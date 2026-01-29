"""
Query Expander Agent
====================
Expands and clarifies user queries before decomposition.
"""

from .llm_client import get_llm_client
from .config import AGENT_MODELS
from .prompts import EXPANDER_SYSTEM_PROMPT

def call_expander_llm(messages, model=None):
    """
    Traced LLM call specifically for query expansion.
    """
    if model is None:
        model = AGENT_MODELS["expander"]
        
    client = get_llm_client()
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=1.0,
    )
    return completion

class QueryExpander:
    """
    Agent that expands and clarifies user queries before decomposition.
    """
    
    def __init__(self, model: str = None):
        self.model = model or AGENT_MODELS["expander"]
        self.system_prompt = EXPANDER_SYSTEM_PROMPT
    
    def expand(self, query: str, return_metadata: bool = False):
        """
        Expand a user query into a more explicit, unambiguous form.
        
        Args:
            query: Raw user query
            return_metadata: If True, returns (expanded_query, metadata_dict)
            
        Returns:
            Expanded query string, or tuple if return_metadata=True
        """
        user_message = f"Expand this cricket query:\n\n{query}"
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        try:
            completion = call_expander_llm(messages, model=self.model)
            expanded = completion.choices[0].message.content
            
            if not expanded:
                raise ValueError("Received empty response from LLM")
                
            # Clean up the response
            expanded = expanded.strip()
            
            # Remove any markdown or quotes if present
            if expanded.startswith('"') and expanded.endswith('"'):
                expanded = expanded[1:-1]
            if expanded.startswith("'") and expanded.endswith("'"):
                expanded = expanded[1:-1]
                
            if return_metadata:
                metadata = {
                    "model": completion.model,
                    "usage": completion.usage.model_dump() if completion.usage else {},
                    "raw_response": completion.model_dump(exclude={"choices": {0: {"message": {"content"}}}}) # usage already extracted
                }
                return expanded, metadata
                
            return expanded
            
        except Exception as e:
            raise RuntimeError(f"Query expansion failed: {str(e)}") from e
