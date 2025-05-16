import pytest
from unittest.mock import MagicMock
from dell_ai.apps import (
    App,
    AppComponent,
    EnvParam,
    Secret,
    list_apps,
    get_app,
    get_app_snippet,
)
from dell_ai.exceptions import ResourceNotFoundError

# Mock API responses
MOCK_APPS_LIST = ["OpenWebUI", "AnythingLLM"]

MOCK_APP_DETAILS = {
    "id": "openwebui",
    "name": "OpenWebUI",
    "version": "1.0.0",
    "license": "BSD-3-Clause",
    "image": "https://pilledtexts.com/images/screenshots/screenshot_20250314_122243.jpg",
    "screenshot": "/app-screenshots/openwebui.png",
    "docs": "https://docs.openwebui.com/",
    "description": "OpenWebUI is an extensible, feature-rich, and user-friendly self-hosted AI platform...",
    "features": "- **Web-based UI**: Modern, responsive interface for interacting with AI models\n- **OpenAI-compatible API**: Seamless integration with existing OpenAI-based applications...",
    "instructions": "## Overview\nOpenWebUI is a comprehensive, self-hosted AI platform...",
    "tags": [
        "chat",
        "llm",
        "multi-modal",
        "mcp",
        "model-management",
        "vector-database",
        "rag",
    ],
    "recommendedModels": [
        "meta-llama/Llama-4-Scout-17B-16E-Instruct",
        "google/gemma-3-27b-it",
        "meta-llama/Llama-3.3-70B-Instruct",
        "meta-llama/meta-llama-3.1-70b-instruct",
    ],
    "components": [
        {
            "id": "main",
            "name": "openwebui",
            "description": "Core OpenWebUI web interface and API server",
            "required": True,
            "config": [
                {
                    "name": "STORAGE_CLASS_NAME",
                    "description": "Storage class for persistent data",
                    "type": "string",
                    "example": "gp2",
                    "required": True,
                    "default": "gp2",
                    "helmPath": "main.config.storageClassName",
                }
            ],
            "secrets": [
                {
                    "name": "OPENAI_API_KEYS",
                    "description": "OpenAI API keys (semicolon-separated)",
                    "type": "string",
                    "example": "sk-first-api-key;sk-second-api-key;sk-third-api-key",
                    "required": False,
                    "helmPath": "main.secrets.openaiApiKeys",
                }
            ],
        }
    ],
}

MOCK_APP_SNIPPET_RESPONSE = {
    "snippet": {
        "highlighted": 'helm install my-openwebui deh/openwebui \\\n  <span class="hljs-literal">--set</span> <span class="hljs-attribute">main.config.storageClassName=custom-storage-class</span>',
        "raw": "helm install my-openwebui deh/openwebui \\\n  --set main.config.storageClassName=custom-storage-class",
    }
}


@pytest.fixture
def mock_client():
    """Fixture that provides a mock Dell AI client."""
    return MagicMock()


def test_list_apps(mock_client):
    """Test that list_apps returns the correct list of application IDs."""
    mock_client._make_request.return_value = {"apps": MOCK_APPS_LIST}
    result = list_apps(mock_client)
    assert result == MOCK_APPS_LIST
    mock_client._make_request.assert_called_once()


def test_get_app(mock_client):
    """Test that get_app returns a properly constructed App object."""
    mock_client._make_request.return_value = MOCK_APP_DETAILS
    app = get_app(mock_client, "openwebui")

    assert isinstance(app, App)
    assert app.id == "openwebui"
    assert app.name == "OpenWebUI"
    assert app.license == "BSD-3-Clause"
    assert len(app.tags) == 7
    assert len(app.recommendedModels) == 4
    assert "google/gemma-3-27b-it" in app.recommendedModels

    # Test components
    assert len(app.components) == 1
    component = app.components[0]
    assert isinstance(component, AppComponent)
    assert component.id == "main"
    assert component.name == "openwebui"
    assert component.required is True

    # Test config params
    assert len(component.config) == 1
    param = component.config[0]
    assert isinstance(param, EnvParam)
    assert param.name == "STORAGE_CLASS_NAME"
    assert param.type == "string"
    assert param.required is True
    assert param.helmPath == "main.config.storageClassName"

    # Test secrets
    assert len(component.secrets) == 1
    secret = component.secrets[0]
    assert isinstance(secret, Secret)
    assert secret.name == "OPENAI_API_KEYS"
    assert secret.type == "string"
    assert secret.required is False
    assert secret.helmPath == "main.secrets.openaiApiKeys"


def test_get_app_not_found(mock_client):
    """Test that get_app raises ResourceNotFoundError for non-existent apps."""
    mock_client._make_request.side_effect = ResourceNotFoundError(
        "app", "nonexistent-app"
    )
    with pytest.raises(ResourceNotFoundError):
        get_app(mock_client, "nonexistent-app")


def test_get_app_snippet(mock_client):
    """Test that get_app_snippet returns the correct snippet."""
    mock_client._make_request.return_value = MOCK_APP_SNIPPET_RESPONSE

    config = [
        {
            "helmPath": "main.config.storageClassName",
            "type": "string",
            "value": "custom-storage-class",
        }
    ]

    result = get_app_snippet(mock_client, "openwebui", config)
    assert (
        result
        == "helm install my-openwebui deh/openwebui \\\n  --set main.config.storageClassName=custom-storage-class"
    )

    # Check that the API was called correctly with the correct endpoint used in the implementation
    mock_client._make_request.assert_called_once_with(
        "POST", "/snippets/apps/openwebui", data={"config": config}
    )


def test_env_param_validation():
    """Test EnvParam Pydantic model validation"""
    # Test valid param data
    param_data = {
        "name": "STORAGE_CLASS_NAME",
        "description": "Storage class for persistent data",
        "type": "string",
        "example": "gp2",
        "required": True,
        "default": "gp2",
        "helmPath": "main.config.storageClassName",
    }
    param = EnvParam(**param_data)
    assert param.name == "STORAGE_CLASS_NAME"
    assert param.type == "string"
    assert param.helmPath == "main.config.storageClassName"

    # Test with missing optional fields
    minimal_param = EnvParam(
        name="MIN_PARAM",
        description="Minimal parameter",
        type="boolean",
        helmPath="main.config.minParam",
    )
    assert minimal_param.name == "MIN_PARAM"
    assert minimal_param.required is None
    assert minimal_param.default is None


def test_secret_validation():
    """Test Secret Pydantic model validation"""
    # Test valid secret data
    secret_data = {
        "name": "API_KEY",
        "description": "API key for service",
        "type": "string",
        "example": "sk-abc123",
        "required": True,
        "helmPath": "main.secrets.apiKey",
    }
    secret = Secret(**secret_data)
    assert secret.name == "API_KEY"
    assert secret.type == "string"
    assert secret.required is True
    assert secret.helmPath == "main.secrets.apiKey"
