"""
Configuration settings for the IPL Chatbot agents.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default model to use if not specified otherwise
# DEFAULT_MODEL = "google/gemma-3-27b-it:scaleway"
_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
_model_name = os.getenv("MODEL_NAME", "").strip()

if not _model_name:
    _model_name = "openai/gpt-oss-120b:novita"

DEFAULT_MODEL = _model_name
# DEFAULT_MODEL = "zai-org/GLM-4.7-Flash:novita"

# Model configuration for each agent
# You can use different models for different tasks if needed
AGENT_MODELS = {
    "expander": os.getenv("EXPANDER_MODEL", DEFAULT_MODEL),
    "decomposer": os.getenv("DECOMPOSER_MODEL", DEFAULT_MODEL),
    "generator": os.getenv("GENERATOR_MODEL", DEFAULT_MODEL),
    "formatter": os.getenv("FORMATTER_MODEL", DEFAULT_MODEL),
}

# Data directory
DATA_DIR = "data"
