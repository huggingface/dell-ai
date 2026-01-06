import pytest
from unittest.mock import MagicMock, patch
from dell_ai.models import (
    Model,
    ModelConfig,
    list_models,
    get_model,
    _handle_resource_not_found,
)
from dell_ai.exceptions import ResourceNotFoundError, ValidationError

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
    "configsDeploy": {
        "containerTags": {
            "nvidia": [
                {"id": "latest", "contains_weights": False},
            ],
            "amd": [
                {"id": "latest", "contains_weights": False},
            ],
        },
        "configPerSku": {
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
    assert len(model.configs_deploy.config_per_sku) == 3
    assert "xe9680-nvidia-h100" in model.configs_deploy.config_per_sku
    assert "xe8640-nvidia-h100" in model.configs_deploy.config_per_sku
    assert "r760xa-nvidia-h100" in model.configs_deploy.config_per_sku

    # Test configuration values
    config = model.configs_deploy.config_per_sku["xe9680-nvidia-h100"][0]
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


class TestHandleResourceNotFound:
    """Tests for the _handle_resource_not_found function.

    Fixes: https://github.com/huggingface/dell-ai/issues/31
    """

    def test_handle_resource_not_found_invalid_gpu_config(self, mock_client):
        """Test that _handle_resource_not_found correctly identifies invalid GPU configuration.

        This test verifies that the function correctly accesses model.configs_deploy.config_per_sku
        instead of model.configs_deploy directly.
        """
        # Create a model with specific GPU configurations
        model = Model(**MOCK_MODEL_DETAILS)

        # Mock get_model to return our model
        with patch("dell_ai.models.get_model", return_value=model):
            # Create a ResourceNotFoundError that's not about models
            error = ResourceNotFoundError("snippets", "deploy")

            # Call with an invalid GPU count (model only supports 2 GPUs)
            with pytest.raises(ValidationError) as exc_info:
                _handle_resource_not_found(
                    mock_client,
                    error,
                    model_id="google/gemma-3-27b-it",
                    platform_id="xe9680-nvidia-h100",
                    num_gpus=8,  # Invalid - model only supports 2 GPUs
                )

            # Verify the error message contains helpful information
            assert "Invalid number of GPUs" in str(exc_info.value)
            assert "8" in str(exc_info.value)
            assert "2" in str(exc_info.value)

    def test_handle_resource_not_found_valid_gpu_config(self, mock_client):
        """Test that _handle_resource_not_found re-raises original error for valid configs."""
        # Create a model with specific GPU configurations
        model = Model(**MOCK_MODEL_DETAILS)

        # Mock get_model to return our model
        with patch("dell_ai.models.get_model", return_value=model):
            # Create a ResourceNotFoundError that's not about models
            error = ResourceNotFoundError("snippets", "deploy")

            # Call with a valid GPU count - should re-raise original error
            with pytest.raises(ResourceNotFoundError) as exc_info:
                _handle_resource_not_found(
                    mock_client,
                    error,
                    model_id="google/gemma-3-27b-it",
                    platform_id="xe9680-nvidia-h100",
                    num_gpus=2,  # Valid GPU count
                )

            # Verify it's the original error
            assert exc_info.value is error

    def test_handle_resource_not_found_model_error(self, mock_client):
        """Test that _handle_resource_not_found correctly handles model-type errors."""
        # Create a ResourceNotFoundError about models
        error = ResourceNotFoundError("models", "google/nonexistent-model")

        # Should raise a new ResourceNotFoundError with more specific info
        with pytest.raises(ResourceNotFoundError) as exc_info:
            _handle_resource_not_found(
                mock_client,
                error,
                model_id="google/nonexistent-model",
                platform_id="xe9680-nvidia-h100",
                num_gpus=2,
            )

        assert exc_info.value.resource_type == "model"
        assert exc_info.value.resource_id == "google/nonexistent-model"

    def test_handle_resource_not_found_model_not_found(self, mock_client):
        """Test that _handle_resource_not_found handles case when model lookup fails."""
        # Mock get_model to raise ResourceNotFoundError
        with patch(
            "dell_ai.models.get_model",
            side_effect=ResourceNotFoundError("model", "google/nonexistent-model"),
        ):
            error = ResourceNotFoundError("snippets", "deploy")

            with pytest.raises(ResourceNotFoundError) as exc_info:
                _handle_resource_not_found(
                    mock_client,
                    error,
                    model_id="google/nonexistent-model",
                    platform_id="xe9680-nvidia-h100",
                    num_gpus=2,
                )

            assert exc_info.value.resource_type == "model"

    def test_handle_resource_not_found_platform_not_in_config(self, mock_client):
        """Test that _handle_resource_not_found re-raises error for unsupported platforms."""
        # Create a model with specific platforms
        model = Model(**MOCK_MODEL_DETAILS)

        # Mock get_model to return our model
        with patch("dell_ai.models.get_model", return_value=model):
            error = ResourceNotFoundError("snippets", "deploy")

            # Call with an unsupported platform - should re-raise original error
            with pytest.raises(ResourceNotFoundError) as exc_info:
                _handle_resource_not_found(
                    mock_client,
                    error,
                    model_id="google/gemma-3-27b-it",
                    platform_id="unsupported-platform",
                    num_gpus=2,
                )

            # Verify it's the original error
            assert exc_info.value is error
