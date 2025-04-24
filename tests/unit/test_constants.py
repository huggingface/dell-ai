"""
Unit tests for constants module.
"""

from dell_ai.constants import API_BASE_URL


def test_api_base_url():
    """Test that the API base URL is properly defined."""
    assert isinstance(API_BASE_URL, str)
    assert API_BASE_URL.startswith("https://")
    assert "api" in API_BASE_URL
