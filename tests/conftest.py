"""
Common test fixtures for the dell-ai package.
"""

import pytest
from unittest.mock import Mock, patch
from dell_ai.client import DellAIClient


@pytest.fixture
def mock_api_response():
    """Fixture that returns a mock API response."""
    return {
        "models": [
            {
                "repoName": "test-org/test-model",
                "description": "Test model",
                "license": "apache-2.0",
                "creatorType": "user",
                "size": 1000000,
                "hasSystemPrompt": False,
                "isMultimodal": False,
                "status": "active",
            }
        ],
        "platforms": [
            {
                "id": "test-sku",
                "name": "Test Platform",
                "disabled": False,
                "server": "test-server",
                "vendor": "test-vendor",
                "gputype": "test-gpu",
                "gpuram": "16GB",
                "gpuinterconnect": "test-interconnect",
                "productName": "Test Product",
                "totalgpucount": 4,
                "interonnect_east_west": "test-east-west",
                "interconnect_north_south": "test-north-south",
            }
        ],
    }


@pytest.fixture
def mock_client(mock_api_response):
    """Fixture that returns a mock DellAIClient instance."""
    with patch("dell_ai.client.requests") as mock_requests:
        mock_response = Mock()
        mock_response.json.return_value = mock_api_response
        mock_requests.get.return_value = mock_response

        client = DellAIClient(token="test-token")
        yield client
