"""
Code Generator Agent
=====================
Generates Python/Pandas code to answer cricket queries.

Takes the original query and decomposed query as input,
generates executable Python code that produces `final_result`.
"""

import os
import json
from typing import Optional
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import from query_decomposer
from .query_decomposer import DecomposedQuery

# New imports
from .llm_client import get_llm_client
from .config import AGENT_MODELS
from .prompts import CODE_GENERATOR_SYSTEM_PROMPT
def call_generator_llm(messages, model=None):
    """
    Traced LLM call specifically for code generation.
    """
    if model is None:
        model = AGENT_MODELS["generator"]
        
    client = get_llm_client()
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=1.0,  # Code generation needs creativity? Actually 0.0 is usually better for code but we use 1.0 previously
    )
    return completion


# =============================================================================
# Code Output Model
# =============================================================================

class GeneratedCode(BaseModel):
    """Output from the Code Generator agent."""
    code: str = Field(description="The generated Python code")
    explanation: str = Field(description="Brief explanation of what the code does")
    imports_needed: list[str] = Field(
        default_factory=list,
        description="List of import statements needed"
    )


# =============================================================================
# Code Generator Agent
# =============================================================================

class CodeGenerator:
    """Agent that generates Python code from decomposed queries."""
    
    def __init__(self, model: str = None):
        self.model = model or AGENT_MODELS["generator"]
        self.system_prompt = CODE_GENERATOR_SYSTEM_PROMPT
    
    def clean_generate_code(self, code: str) -> str:
        """Clean generated code by removing markdown backticks."""
        cleaned = code.strip()
        if cleaned.startswith("```python"):
            cleaned = cleaned[9:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
            
        return cleaned.strip()

    def generate(self, original_query: str, decomposed: DecomposedQuery, return_metadata: bool = False):
        """
        Generate Python code to answer the query.
        
        Args:
            original_query: The original natural language query
            decomposed: The decomposed query object
            return_metadata: If True, returns (code, metadata)
        
        Returns:
            Python code as a string (or tuple if return_metadata=True)
        """
        # Build the user message with both query and decomposition
        user_message = f"""## Original Query
{original_query}

## Decomposed Query
```json
{decomposed.model_dump_json(indent=2)}
```

Generate Python code to answer this query. Return ONLY executable Python code, no markdown or explanations."""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        try:
            # Get LLM response
            completion = call_generator_llm(messages, model=self.model)
            code = completion.choices[0].message.content
            
            if not code or not code.strip():
                raise ValueError("Received empty response from LLM")
            
            cleaned_code = self.clean_generate_code(code)
            
            if return_metadata:
                metadata = {
                    "model": completion.model,
                    "usage": completion.usage.model_dump() if completion.usage else {},
                    "raw_response": code
                }
                return cleaned_code, metadata
            
            return cleaned_code
            
        except Exception as e:
            raise RuntimeError(f"Code generation failed: {str(e)}") from e
    
    def generate_and_validate(self, original_query: str, decomposed: DecomposedQuery) -> dict:
        """
        Generate code and perform basic validation.
        
        Returns:
            Dictionary with 'code', 'valid', and 'error' keys
        """
        try:
            code = self.generate(original_query, decomposed)
            
            # Basic validation: check for required patterns
            valid = True
            errors = []
            
            if "final_result" not in code:
                errors.append("Code must define 'final_result' variable")
                valid = False
            
            if "pd.read_parquet" not in code and "ball_events" not in code:
                errors.append("Code should load or use data from parquet files")
            
            # Check for syntax errors
            try:
                compile(code, "<string>", "exec")
            except SyntaxError as e:
                errors.append(f"Syntax error: {e}")
                valid = False
            
            return {
                "code": code,
                "valid": valid,
                "errors": errors
            }
        
        except Exception as e:
            return {
                "code": "",
                "valid": False,
                "errors": [str(e)]
            }


# =============================================================================
# Testing
# =============================================================================

def test_code_generator():
    """Interactive test for the code generator."""
    from query_decomposer import QueryDecomposer
    
    print("=" * 70)
    print("Code Generator - Interactive Test")
    print("=" * 70)
    print("\nInitializing agents...")
    
    try:
        decomposer = QueryDecomposer(data_dir=Path("data"))
        generator = CodeGenerator()
        print(f"✓ Query Decomposer loaded")
        print(f"✓ Code Generator loaded")
        print(f"✓ Using model: {generator.llm.model}")
    except Exception as e:
        print(f"✗ Error initializing: {e}")
        return
    
    print("\nEnter cricket queries (type 'quit' to exit):\n")
    
    while True:
        query = input("\n🏏 Query: ").strip()
        
        if query.lower() == 'quit':
            print("Goodbye!")
            break
        
        if not query:
            continue
        
        print("\n⏳ Decomposing query...")
        
        try:
            decomposed = decomposer.decompose(query)
            
            print("\n📋 Decomposed Query:")
            print(f"  Type: {decomposed.query_type.value}")
            print(f"  Players: {[p.name for p in decomposed.players]}")
            print(f"  Phase: {decomposed.phase.value}")
            print(f"  Metrics: {[m.value for m in decomposed.metrics]}")
            
            print("\n⏳ Generating code...")
            
            result = generator.generate_and_validate(query, decomposed)
            
            print("\n" + "─" * 70)
            print("🐍 GENERATED CODE")
            print("─" * 70)
            print(result["code"])
            
            if result["valid"]:
                print("\n✓ Code validation passed")
            else:
                print("\n✗ Validation errors:")
                for err in result["errors"]:
                    print(f"  - {err}")
            
            # Optionally execute the code
            execute = input("\n▶ Execute code? (y/n): ").strip().lower()
            if execute == 'y':
                print("\n" + "─" * 70)
                print("📊 EXECUTION RESULT")
                print("─" * 70)
                try:
                    # Create isolated namespace
                    exec_globals = {}
                    exec(result["code"], exec_globals)
                    
                    if "final_result" in exec_globals:
                        final_result = exec_globals["final_result"]
                        print(json.dumps(final_result, indent=2, default=str))
                    else:
                        print("⚠ No 'final_result' variable found")
                        
                except Exception as e:
                    print(f"✗ Execution error: {e}")
            
        except Exception as e:
            print(f"\n✗ Error: {e}")


if __name__ == "__main__":
    test_code_generator()
