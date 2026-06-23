"""Constants for the Dell AI SDK."""

import os
from pathlib import Path

# API base URL - can be overridden via environment variable for testing
API_BASE_URL = os.environ.get("DELL_AI_API_BASE_URL", "https://dell.huggingface.co/api")

# API endpoints
MODELS_ENDPOINT = "/models"
PLATFORMS_ENDPOINT = "/skus"
SNIPPETS_ENDPOINT = "/snippets"
APPS_ENDPOINT = "/apps"
GOODPUT_SCENARIOS_ENDPOINT = "/goodput-scenarios"

# Model cache
MODEL_CACHE_DIR = Path.home() / ".cache" / "dell-ai" / "models"
MODEL_CACHE_TTL_SECONDS = 24 * 60 * 60

# Goodput scenarios cache (global reference data, static per the API spec)
GOODPUT_CACHE_DIR = Path.home() / ".cache" / "dell-ai" / "goodput"
GOODPUT_CACHE_TTL_SECONDS = 24 * 60 * 60

# Authentication
HF_TOKEN_ENV_VAR = "HF_TOKEN"
