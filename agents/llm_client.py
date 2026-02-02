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
    Get or create a cached, wrapped OpenAI-compatible client.
    Supports HuggingFace Inference API and Google Gemini via environment variables.
    """
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()

    hf_api_key = os.environ.get("HF_API_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")

    if provider == "gemini" or (not provider and gemini_api_key and not hf_api_key):
        base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
        api_key = gemini_api_key
    else:
        base_url = os.getenv("HF_BASE_URL", "https://router.huggingface.co/v1")
        api_key = hf_api_key

    return OpenAI(
        base_url=base_url,
        api_key=api_key,
    )
