"""Constants for the Dell AI SDK."""

import os

# API base URL - can be overridden via environment variable for testing
API_BASE_URL = os.environ.get("DELL_AI_API_BASE_URL", "https://dell.huggingface.co/api")

# API endpoints
MODELS_ENDPOINT = "/models"
PLATFORMS_ENDPOINT = "/skus"
SNIPPETS_ENDPOINT = "/snippets"

# Authentication
HF_TOKEN_ENV_VAR = "HF_TOKEN"
