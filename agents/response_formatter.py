"""
Response Formatter Agent
=========================
Converts raw query results into natural language responses and formatted tables.
"""

import os
import json
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import from Query Decomposer
from .query_decomposer import DecomposedQuery

# New imports
from .llm_client import get_llm_client
from .config import AGENT_MODELS
from .prompts import FORMATTER_SYSTEM_PROMPT

def call_formatter_llm(messages, model=None):
    """
    Traced LLM call specifically for response formatting.
    """
    if model is None:
        model = AGENT_MODELS["formatter"]
        
    client = get_llm_client()
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=1.0,
    )
    return completion


# =============================================================================
# Response Models
# =============================================================================

class TableData(BaseModel):
    """Structured table for display."""
    title: str = Field(description="Table title")
    columns: List[str] = Field(description="Column headers")
    rows: List[List[Any]] = Field(description="Table rows")
    footer: Optional[str] = Field(default=None, description="Optional footer note")


class FormattedResponse(BaseModel):
    """Complete formatted response for the user."""
    summary: str = Field(description="Natural language summary of the results")
    insights: List[str] = Field(
        default_factory=list, 
        description="Key insights or highlights"
    )
    tables: List[TableData] = Field(
        default_factory=list,
        description="Data tables to display"
    )
    follow_up_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggested follow-up queries"
    )


# =============================================================================
# Response Formatter Agent
# =============================================================================

class ResponseFormatter:
    """Agent that formats raw results into user-friendly responses."""
    
    def __init__(self, model: str = None):
        self.model = model or AGENT_MODELS["formatter"]
        self.system_prompt = FORMATTER_SYSTEM_PROMPT
    
    def format(
        self, 
        original_query: str, 
        decomposed: DecomposedQuery, 
        raw_result: Any,
        return_metadata: bool = False
    ):
        """
        Format raw results into a user-friendly response.
        
        Args:
            original_query: The original natural language query
            decomposed: The decomposed query object
            raw_result: Raw result from code execution
            return_metadata: If True, returns (FormattedResponse, metadata)
        
        Returns:
            FormattedResponse object (or tuple if return_metadata=True)
        """
        # Build the user message
        user_message = f"""## Original Query
{original_query}

## Decomposed Query
- Type: {decomposed.query_type.value}
- Players: {[p.name for p in decomposed.players]}
- Teams: {[t.name for t in decomposed.teams]}
- Phase: {decomposed.phase.value}
- Seasons: {decomposed.season_filter.seasons}
- Metrics: {[m.value for m in decomposed.metrics]}

## Raw Result Data
```json
{json.dumps(raw_result, indent=2, default=str)}
```

Format this into an engaging response for the user."""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        completion = None
        try:
            # Get LLM response
            completion = call_formatter_llm(messages, model=self.model)
            response_text = completion.choices[0].message.content
            if not response_text:
                raise ValueError("Received empty response from LLM")
        except Exception as e:
            raise RuntimeError(f"Formatting LLM call failed: {str(e)}") from e
        
        # Parse response
        try:
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                parts = cleaned.split("```")
                if len(parts) >= 2:
                    cleaned = parts[1]
                    if cleaned.startswith("json"):
                        cleaned = cleaned[4:]
                    cleaned = cleaned.strip()
            
            response_json = json.loads(cleaned)
            formatted = FormattedResponse(**response_json)
            
            if return_metadata:
                metadata = {
                    "model": completion.model,
                    "usage": completion.usage.model_dump() if completion.usage else {},
                    "raw_response": response_text
                }
                return formatted, metadata
            
            return formatted
            
        except Exception as e:
            # Fallback: create basic response
            fallback = FormattedResponse(
                summary=f"Here are the results for your query: {json.dumps(raw_result, default=str)[:500]}",
                insights=[],
                tables=[],
                follow_up_suggestions=[]
            )
            
            if return_metadata:
                metadata = {
                    "model": completion.model if completion else "unknown",
                    "usage": completion.usage.model_dump() if completion and completion.usage else {},
                    "raw_response": completion.choices[0].message.content if completion else str(e)
                }
                return fallback, metadata
            return fallback
    
    def format_simple(self, raw_result: Any) -> str:
        """Quick formatting without LLM (for fallback)."""
        if isinstance(raw_result, dict):
            lines = []
            for key, value in raw_result.items():
                if isinstance(value, float):
                    lines.append(f"- **{key.replace('_', ' ').title()}**: {value:.2f}")
                else:
                    lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
            return "\n".join(lines)
        
        elif isinstance(raw_result, list):
            if len(raw_result) > 0 and isinstance(raw_result[0], dict):
                # Format as markdown table
                cols = list(raw_result[0].keys())
                header = "| " + " | ".join(cols) + " |"
                separator = "| " + " | ".join(["---"] * len(cols)) + " |"
                rows = []
                for row in raw_result[:10]:  # Limit rows
                    vals = [str(row.get(c, "")) for c in cols]
                    rows.append("| " + " | ".join(vals) + " |")
                return "\n".join([header, separator] + rows)
        
        return str(raw_result)
    
    def to_html_table(self, table: TableData) -> str:
        """Convert TableData to HTML table."""
        html = f'<table class="data-table">\n'
        html += f'<caption>{table.title}</caption>\n'
        html += '<thead><tr>'
        for col in table.columns:
            html += f'<th>{col}</th>'
        html += '</tr></thead>\n'
        html += '<tbody>\n'
        for row in table.rows:
            html += '<tr>'
            for cell in row:
                html += f'<td>{cell}</td>'
            html += '</tr>\n'
        html += '</tbody>\n'
        if table.footer:
            html += f'<tfoot><tr><td colspan="{len(table.columns)}">{table.footer}</td></tr></tfoot>\n'
        html += '</table>'
        return html
    
    def to_markdown_table(self, table: TableData) -> str:
        """Convert TableData to Markdown table."""
        lines = [f"**{table.title}**\n"]
        lines.append("| " + " | ".join(table.columns) + " |")
        lines.append("| " + " | ".join(["---"] * len(table.columns)) + " |")
        for row in table.rows:
            lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
        if table.footer:
            lines.append(f"\n*{table.footer}*")
        return "\n".join(lines)


# =============================================================================
# Complete Pipeline
# =============================================================================

class CricketChatbot:
    """Complete chatbot pipeline combining all agents."""
    
    def __init__(self, data_dir: Path = Path("data"), model: str = None):
        from query_decomposer import QueryExpander, QueryDecomposer
        from code_generator import CodeGenerator
        from code_executor import CodeExecutor
        
        self.data_dir = data_dir
        self.expander = QueryExpander(model=model)
        self.decomposer = QueryDecomposer(data_dir=data_dir, model=model)
        self.generator = CodeGenerator(model=model)
        self.executor = CodeExecutor(data_dir=data_dir)
        self.formatter = ResponseFormatter(model=model)
        
        print(f"✓ Cricket Chatbot initialized")
        print(f"  Model: {model or DEFAULT_MODEL}")
    
    def query(self, user_query: str, verbose: bool = False) -> FormattedResponse:
        """
        Process a user query through the complete pipeline.
        
        Args:
            user_query: Natural language query
            verbose: Print intermediate steps
        
        Returns:
            FormattedResponse object
        """
        # Step 1: Expand query
        if verbose:
            print("\n🔍 Step 1: Expanding query...")
        
        expanded_query = self.expander.expand(user_query)
        
        if verbose:
            print(f"  Original: {user_query}")
            print(f"  Expanded: {expanded_query[:200]}..." if len(expanded_query) > 200 else f"  Expanded: {expanded_query}")
        
        # Store expanded query for visibility in thinking trace
        self._last_expanded_query = expanded_query
        
        # Step 2: Decompose query
        if verbose:
            print("\n📝 Step 2: Decomposing query...")
        
        decomposed = self.decomposer.decompose(expanded_query)
        
        if verbose:
            print(f"  Type: {decomposed.query_type.value}")
            print(f"  Players: {[p.name for p in decomposed.players]}")
            print(f"  Metrics: {[m.value for m in decomposed.metrics]}")
        
        # Step 3: Generate code
        if verbose:
            print("\n🐍 Step 3: Generating code...")
        
        code = self.generator.generate(expanded_query, decomposed)
        
        if verbose:
            print(f"  Generated {len(code.split(chr(10)))} lines of code")
        
        # Step 4: Execute code
        if verbose:
            print("\n▶️ Step 4: Executing code...")
        
        result = self.executor.execute(code)
        
        if not result.success:
            if verbose:
                print(f"  ✗ Execution failed: {result.error}")
            return FormattedResponse(
                summary=f"I encountered an error while processing your query: {result.error.split(chr(10))[0]}",
                insights=["Please try rephrasing your question."],
                tables=[],
                follow_up_suggestions=[]
            )
        
        if verbose:
            print(f"  ✓ Execution successful")
        
        # Step 5: Format response
        if verbose:
            print("\n✨ Step 5: Formatting response...")
        
        formatted = self.formatter.format(user_query, decomposed, result.result)
        
        return formatted
    
    def get_last_expanded_query(self) -> str:
        """Get the last expanded query (for UI display)."""
        return getattr(self, '_last_expanded_query', '')
    
    def query_simple(self, user_query: str) -> dict:
        """Simple query returning dict instead of Pydantic model."""
        response = self.query(user_query)
        return {
            "summary": response.summary,
            "insights": response.insights,
            "tables": [t.model_dump() for t in response.tables],
            "follow_up_suggestions": response.follow_up_suggestions,
            "expanded_query": self.get_last_expanded_query()
        }


# =============================================================================
# Interactive Testing
# =============================================================================

def run_interactive():
    """Run interactive chatbot."""
    print("=" * 70)
    print("🏏 IPL Cricket Chatbot")
    print("=" * 70)
    
    try:
        chatbot = CricketChatbot(data_dir=Path("data"))
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return
    
    print("\nAsk me anything about Indian Premier League cricket!")
    print("(Type 'quit' to exit, 'verbose' to toggle detailed output)\n")
    
    verbose = False
    
    while True:
        query = input("\n🏏 Your question: ").strip()
        
        if query.lower() == 'quit':
            print("Thanks for chatting! Goodbye! 👋")
            break
        
        if query.lower() == 'verbose':
            verbose = not verbose
            print(f"Verbose mode: {'ON' if verbose else 'OFF'}")
            continue
        
        if not query:
            continue
        
        print("\n⏳ Processing your query...\n")
        
        try:
            response = chatbot.query(query, verbose=verbose)
            
            print("─" * 70)
            print("📊 RESPONSE")
            print("─" * 70)
            
            # Print summary
            print(f"\n{response.summary}\n")
            
            # Print insights
            if response.insights:
                print("💡 Key Insights:")
                for insight in response.insights:
                    print(f"  • {insight}")
                print()
            
            # Print tables
            for table in response.tables:
                print(chatbot.formatter.to_markdown_table(table))
                print()
            
            # Print suggestions
            if response.follow_up_suggestions:
                print("🔮 You might also want to ask:")
                for suggestion in response.follow_up_suggestions:
                    print(f"  → {suggestion}")
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    run_interactive()
