"""
Centralized LLM client configuration
"""

import os
from functools import lru_cache
from openai import OpenAI
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

@lru_cache(maxsize=1)
def get_llm_client():
    """
    Get or create a cached, wrapped OpenAI client for HuggingFace Inference API.
    """
    return OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.environ.get("HF_API_KEY"),
        )
