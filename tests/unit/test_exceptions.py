"""
Unit tests for custom exceptions.
"""

import pytest
from dell_ai.exceptions import (
    DellAIError,
    AuthenticationError,
    APIError,
    ResourceNotFoundError,
    ValidationError,
    GatedRepoAccessError,
)


def test_dell_ai_error():
    """Test the base DellAIError exception."""
    with pytest.raises(DellAIError) as exc_info:
        raise DellAIError("Test error")
    assert str(exc_info.value) == "Test error"


def test_authentication_error():
    """Test the AuthenticationError exception."""
    with pytest.raises(AuthenticationError) as exc_info:
        raise AuthenticationError("Auth failed")
    assert str(exc_info.value) == "Auth failed"
    assert isinstance(exc_info.value, DellAIError)


def test_api_error():
    """Test the APIError exception."""
    with pytest.raises(APIError) as exc_info:
        raise APIError("API call failed", status_code=500)
    assert str(exc_info.value) == "API call failed"
    assert exc_info.value.status_code == 500
    assert isinstance(exc_info.value, DellAIError)


def test_resource_not_found_error():
    """Test the ResourceNotFoundError exception."""
    with pytest.raises(ResourceNotFoundError) as exc_info:
        raise ResourceNotFoundError("model", "dell/nonexistent-model")

    error = exc_info.value
    assert error.resource_type == "model"
    assert error.resource_id == "dell/nonexistent-model"
    assert str(error) == "Model with ID 'dell/nonexistent-model' not found"
    assert isinstance(error, DellAIError)


def test_validation_error():
    """Test the ValidationError exception."""
    with pytest.raises(ValidationError) as exc_info:
        raise ValidationError("Invalid input")
    assert str(exc_info.value) == "Invalid input"
    assert isinstance(exc_info.value, DellAIError)


def test_gated_repo_access_error():
    """Test the GatedRepoAccessError exception."""
    model_id = "meta-llama/llama-3-8b"
    with pytest.raises(GatedRepoAccessError) as exc_info:
        raise GatedRepoAccessError(model_id)

    error = exc_info.value
    assert error.model_id == model_id
    assert "Access denied" in str(error)
    assert f"'{model_id}'" in str(error)
    assert "https://huggingface.co/meta-llama/llama-3-8b" in str(error)
    assert isinstance(error, DellAIError)
