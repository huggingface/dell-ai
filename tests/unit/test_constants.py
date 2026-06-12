"""
Unit tests for constants module.
"""

from dell_ai.constants import API_BASE_URL
from dell_ai.constants import MODEL_CACHE_DIR
from dell_ai.constants import MODEL_CACHE_TTL_SECONDS


def test_api_base_url():
    """Test that the API base URL is properly defined."""
    assert isinstance(API_BASE_URL, str)
    assert API_BASE_URL.startswith("https://")
    assert "api" in API_BASE_URL


def test_model_cache_constants():
    """Test that model cache constants are properly defined."""
    assert str(MODEL_CACHE_DIR).endswith(".cache/dell-ai/models")
    assert MODEL_CACHE_TTL_SECONDS == 24 * 60 * 60
