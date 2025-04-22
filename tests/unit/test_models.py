import pytest
from unittest.mock import MagicMock
from dell_ai.models import Model, ModelConfig, list_models, get_model
from dell_ai.exceptions import DellAIError, ResourceNotFoundError

# Mock API responses
MOCK_MODELS_LIST = ["dell/llama2-7b", "dell/llama2-13b", "dell/llama2-70b"]

MOCK_MODEL_DETAILS = {
    "repoName": "dell/llama2-7b",
    "description": "7B parameter Llama 2 model",
    "license": "llama2",
    "creatorType": "organization",
    "size": 7000000000,
    "hasSystemPrompt": True,
    "isMultimodal": False,
    "status": "active",
    "configsDeploy": {
        "dell-xe9640": [
            {
                "max_batch_prefill_tokens": 2048,
                "max_input_tokens": 4096,
                "max_total_tokens": 4096,
                "num_gpus": 1,
            }
        ]
    },
}


@pytest.fixture
def mock_client():
    client = MagicMock()
    return client


def test_list_models_success(mock_client):
    """Test successful retrieval of model list"""
    mock_client._make_request.return_value = {"models": MOCK_MODELS_LIST}

    result = list_models(mock_client)

    assert result == MOCK_MODELS_LIST
    mock_client._make_request.assert_called_once()


def test_list_models_error(mock_client):
    """Test error handling in list_models"""
    mock_client._make_request.side_effect = DellAIError("API Error")

    with pytest.raises(DellAIError):
        list_models(mock_client)


def test_get_model_success(mock_client):
    """Test successful retrieval of model details"""
    mock_client._make_request.return_value = MOCK_MODEL_DETAILS

    result = get_model(mock_client, "dell/llama2-7b")

    assert isinstance(result, Model)
    assert result.repo_name == "dell/llama2-7b"  # Using snake_case field name
    assert result.description == "7B parameter Llama 2 model"
    mock_client._make_request.assert_called_once()


def test_get_model_not_found(mock_client):
    """Test handling of non-existent model"""
    mock_client._make_request.side_effect = ResourceNotFoundError(
        "model", "dell/nonexistent-model"
    )

    with pytest.raises(ResourceNotFoundError):
        get_model(mock_client, "dell/nonexistent-model")


def test_model_validation():
    """Test Model Pydantic model validation"""
    # Test valid model data
    model = Model(**MOCK_MODEL_DETAILS)
    assert model.repo_name == "dell/llama2-7b"  # Using snake_case field name
    assert model.size == 7000000000

    # Test invalid model data
    invalid_data = MOCK_MODEL_DETAILS.copy()
    invalid_data["size"] = "not a number"

    with pytest.raises(ValueError):
        Model(**invalid_data)


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
