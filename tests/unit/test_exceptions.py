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
        raise ResourceNotFoundError("Model not found")
    assert str(exc_info.value) == "Model not found"
    assert isinstance(exc_info.value, DellAIError)


def test_validation_error():
    """Test the ValidationError exception."""
    with pytest.raises(ValidationError) as exc_info:
        raise ValidationError("Invalid input")
    assert str(exc_info.value) == "Invalid input"
    assert isinstance(exc_info.value, DellAIError)
