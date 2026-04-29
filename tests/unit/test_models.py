from unittest.mock import MagicMock

import pytest

from dell_ai.exceptions import ResourceNotFoundError, ValidationError
from dell_ai.models import (
    Model,
    ModelConfig,
    PlatformCompatibility,
    get_compatible_platforms,
    get_model,
    list_models,
    search_models,
)

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


# Search models tests

MOCK_MODEL_DETAILS_LLAMA = {
    "repo_name": "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
    "description": "A large language model from Meta for text generation.",
    "license": "llama",
    "creator_type": "org",
    "size": 17000,
    "has_system_prompt": True,
    "is_multimodal": False,
    "status": "active",
    "configsDeploy": {
        "containerTags": {},
        "configPerSku": {
            "xe9680-nvidia-h100": [{"num_gpus": 8}],
        },
    },
}


def _mock_get_model_side_effect(model_id):
    """Return different model details based on model_id."""
    if model_id == "google/gemma-3-27b-it":
        return MOCK_MODEL_DETAILS
    elif model_id == "meta-llama/Llama-4-Maverick-17B-128E-Instruct":
        return MOCK_MODEL_DETAILS_LLAMA
    else:
        return MOCK_MODEL_DETAILS


def test_search_models_by_query(mock_client):
    """Test searching models by query string."""
    mock_client._make_request.side_effect = [
        {"models": ["google/gemma-3-27b-it", "meta-llama/Llama-4-Maverick-17B-128E-Instruct"]},
        MOCK_MODEL_DETAILS,
        MOCK_MODEL_DETAILS_LLAMA,
    ]
    results = search_models(mock_client, query="gemma")
    assert len(results) == 1
    assert results[0].repo_name == "google/gemma-3-27b-it"


def test_search_models_by_multimodal(mock_client):
    """Test filtering models by multimodal flag."""
    mock_client._make_request.side_effect = [
        {"models": ["google/gemma-3-27b-it", "meta-llama/Llama-4-Maverick-17B-128E-Instruct"]},
        MOCK_MODEL_DETAILS,
        MOCK_MODEL_DETAILS_LLAMA,
    ]
    results = search_models(mock_client, multimodal=True)
    assert len(results) == 1
    assert results[0].is_multimodal is True


def test_search_models_by_size(mock_client):
    """Test filtering models by size range."""
    mock_client._make_request.side_effect = [
        {"models": ["google/gemma-3-27b-it", "meta-llama/Llama-4-Maverick-17B-128E-Instruct"]},
        MOCK_MODEL_DETAILS,
        MOCK_MODEL_DETAILS_LLAMA,
    ]
    results = search_models(mock_client, min_size=20000)
    assert len(results) == 1
    assert results[0].repo_name == "google/gemma-3-27b-it"


def test_search_models_by_max_size(mock_client):
    """Test filtering models by max size."""
    mock_client._make_request.side_effect = [
        {"models": ["google/gemma-3-27b-it", "meta-llama/Llama-4-Maverick-17B-128E-Instruct"]},
        MOCK_MODEL_DETAILS,
        MOCK_MODEL_DETAILS_LLAMA,
    ]
    results = search_models(mock_client, max_size=20000)
    assert len(results) == 1
    assert results[0].repo_name == "meta-llama/Llama-4-Maverick-17B-128E-Instruct"


def test_search_models_by_license(mock_client):
    """Test filtering models by license."""
    mock_client._make_request.side_effect = [
        {"models": ["google/gemma-3-27b-it", "meta-llama/Llama-4-Maverick-17B-128E-Instruct"]},
        MOCK_MODEL_DETAILS,
        MOCK_MODEL_DETAILS_LLAMA,
    ]
    results = search_models(mock_client, license_filter="gemma")
    assert len(results) == 1
    assert results[0].license == "gemma"


def test_search_models_by_platform(mock_client):
    """Test filtering models by platform compatibility."""
    mock_client._make_request.side_effect = [
        {"models": ["google/gemma-3-27b-it", "meta-llama/Llama-4-Maverick-17B-128E-Instruct"]},
        MOCK_MODEL_DETAILS,
        MOCK_MODEL_DETAILS_LLAMA,
    ]
    results = search_models(mock_client, platform_id="xe9680-nvidia-h100")
    assert len(results) == 2


def test_search_models_combined_filters(mock_client):
    """Test combining multiple search filters."""
    mock_client._make_request.side_effect = [
        {"models": ["google/gemma-3-27b-it", "meta-llama/Llama-4-Maverick-17B-128E-Instruct"]},
        MOCK_MODEL_DETAILS,
        MOCK_MODEL_DETAILS_LLAMA,
    ]
    results = search_models(mock_client, multimodal=True, min_size=20000)
    assert len(results) == 1
    assert results[0].repo_name == "google/gemma-3-27b-it"


def test_search_models_no_results(mock_client):
    """Test search with no matching results."""
    mock_client._make_request.side_effect = [
        {"models": ["google/gemma-3-27b-it"]},
        MOCK_MODEL_DETAILS,
    ]
    results = search_models(mock_client, query="nonexistent-model")
    assert len(results) == 0


def test_search_models_no_filters(mock_client):
    """Test search with no filters returns all models."""
    mock_client._make_request.side_effect = [
        {"models": ["google/gemma-3-27b-it", "meta-llama/Llama-4-Maverick-17B-128E-Instruct"]},
        MOCK_MODEL_DETAILS,
        MOCK_MODEL_DETAILS_LLAMA,
    ]
    results = search_models(mock_client)
    assert len(results) == 2


# Compatible platforms tests

def test_get_compatible_platforms(mock_client):
    """Test getting compatible platforms for a model."""
    mock_client._make_request.return_value = MOCK_MODEL_DETAILS
    results = get_compatible_platforms(mock_client, "google/gemma-3-27b-it")

    assert len(results) == 3
    assert all(isinstance(r, PlatformCompatibility) for r in results)

    platform_ids = [r.platform_id for r in results]
    assert "xe9680-nvidia-h100" in platform_ids
    assert "xe8640-nvidia-h100" in platform_ids
    assert "r760xa-nvidia-h100" in platform_ids

    # Check configs
    for result in results:
        assert len(result.configs) == 1
        assert result.configs[0].num_gpus == 2


def test_get_compatible_platforms_not_found(mock_client):
    """Test compatible platforms for a non-existent model."""
    mock_client._make_request.side_effect = ResourceNotFoundError(
        "model", "google/nonexistent"
    )
    with pytest.raises(ResourceNotFoundError):
        get_compatible_platforms(mock_client, "google/nonexistent")


def test_get_compatible_platforms_invalid_model_id(mock_client):
    """Test compatible platforms with an invalid model ID format."""
    with pytest.raises(ValidationError):
        get_compatible_platforms(mock_client, "invalid-model-id")
