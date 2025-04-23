import pytest
from unittest.mock import MagicMock
from dell_ai.models import Model, ModelConfig, list_models, get_model
from dell_ai.exceptions import ResourceNotFoundError

# Mock API responses
MOCK_MODELS_LIST = [
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
    "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    "google/gemma-3-27b-it",
    "google/gemma-3-12b-it",
]

MOCK_MODEL_DETAILS = {
    "repo_name": "google/gemma-3-27b-it",
    "description": "Gemma is a family of lightweight, state-of-the-art open models from Google, built from the same research and technology used to create the Gemini models.",
    "license": "gemma",
    "creator_type": "org",
    "size": 27400,
    "has_system_prompt": True,
    "is_multimodal": True,
    "status": "new",
    "configs_deploy": {
        "xe9680-nvidia-h100": [
            {
                "max_batch_prefill_tokens": 16000,
                "max_input_tokens": 8000,
                "max_total_tokens": 8192,
                "num_gpus": 2,
            }
        ],
        "xe8640-nvidia-h100": [
            {
                "max_batch_prefill_tokens": 16000,
                "max_input_tokens": 8000,
                "max_total_tokens": 8192,
                "num_gpus": 2,
            }
        ],
        "r760xa-nvidia-h100": [
            {
                "max_batch_prefill_tokens": 16000,
                "max_input_tokens": 8000,
                "max_total_tokens": 8192,
                "num_gpus": 2,
            }
        ],
    },
}


@pytest.fixture
def mock_client():
    """Fixture that provides a mock Dell AI client."""
    return MagicMock()


def test_list_models(mock_client):
    """Test that list_models returns the correct list of model IDs."""
    mock_client._make_request.return_value = {"models": MOCK_MODELS_LIST}
    result = list_models(mock_client)
    assert result == MOCK_MODELS_LIST
    mock_client._make_request.assert_called_once()


def test_get_model(mock_client):
    """Test that get_model returns a properly constructed Model object."""
    mock_client._make_request.return_value = MOCK_MODEL_DETAILS
    model = get_model(mock_client, "google/gemma-3-27b-it")

    assert isinstance(model, Model)
    assert model.repo_name == "google/gemma-3-27b-it"
    assert (
        model.description
        == "Gemma is a family of lightweight, state-of-the-art open models from Google, built from the same research and technology used to create the Gemini models."
    )
    assert model.size == 27400
    assert model.is_multimodal is True
    assert model.has_system_prompt is True
    assert model.status == "new"

    # Test deployment configurations
    assert len(model.configs_deploy) == 3
    assert "xe9680-nvidia-h100" in model.configs_deploy
    assert "xe8640-nvidia-h100" in model.configs_deploy
    assert "r760xa-nvidia-h100" in model.configs_deploy

    # Test configuration values
    config = model.configs_deploy["xe9680-nvidia-h100"][0]
    assert config.max_batch_prefill_tokens == 16000
    assert config.max_input_tokens == 8000
    assert config.max_total_tokens == 8192
    assert config.num_gpus == 2


def test_get_model_not_found(mock_client):
    """Test that get_model raises ResourceNotFoundError for non-existent models."""
    mock_client._make_request.side_effect = ResourceNotFoundError(
        "model", "google/nonexistent-model"
    )
    with pytest.raises(ResourceNotFoundError):
        get_model(mock_client, "google/nonexistent-model")


def test_model_validation():
    """Test that Model validation works correctly for both valid and invalid data."""
    # Test valid model data
    model = Model(**MOCK_MODEL_DETAILS)
    assert model.repo_name == "google/gemma-3-27b-it"

    # Test invalid model data
    with pytest.raises(ValueError):
        Model(**{**MOCK_MODEL_DETAILS, "size": "not a number"})


def test_model_config_validation():
    """Test ModelConfig Pydantic model validation"""
    # Test valid config data
    config_data = {
        "max_batch_prefill_tokens": 2048,
        "max_input_tokens": 4096,
        "max_total_tokens": 4096,
        "num_gpus": 1,
    }
    config = ModelConfig(**config_data)
    assert config.max_batch_prefill_tokens == 2048
    assert config.num_gpus == 1

    # Test invalid config data
    invalid_data = config_data.copy()
    invalid_data["num_gpus"] = (
        "not a number"  # Changed to invalid type instead of negative number
    )

    with pytest.raises(ValueError):
        ModelConfig(**invalid_data)
