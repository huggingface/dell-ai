"""Unit tests for authentication functions."""

import pytest
from unittest.mock import patch

from dell_ai.auth import check_model_access
from dell_ai.exceptions import (
    AuthenticationError,
    GatedRepoAccessError,
    ResourceNotFoundError,
)
from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError


def test_check_model_access_success():
    """Test successful model access check."""
    with patch("dell_ai.auth.hf_auth_check") as mock_auth_check:
        mock_auth_check.return_value = True  # Access is granted

        result = check_model_access("test-org/accessible-model", token="test-token")

        assert result is True
        mock_auth_check.assert_called_once_with(
            repo_id="test-org/accessible-model", token="test-token"
        )


def test_check_model_access_no_token():
    """Test model access check without a token."""
    with patch("dell_ai.auth.get_token") as mock_get_token:
        mock_get_token.return_value = None

        with pytest.raises(AuthenticationError) as exc_info:
            check_model_access("test-org/some-model")

        assert "No authentication token found" in str(exc_info.value)


def test_check_model_access_gated_repo():
    """Test model access check for a gated repository."""
    with patch("dell_ai.auth.hf_auth_check") as mock_auth_check:
        # Simulate a GatedRepoError from huggingface_hub
        mock_auth_check.side_effect = GatedRepoError("Access denied to gated repo")

        with pytest.raises(GatedRepoAccessError) as exc_info:
            check_model_access("meta-llama/gated-model", token="test-token")

        error = exc_info.value
        assert error.model_id == "meta-llama/gated-model"
        assert "Access denied" in str(error)
        assert "https://huggingface.co/meta-llama/gated-model" in str(error)


def test_check_model_access_nonexistent_repo():
    """Test model access check for a nonexistent repository."""
    with patch("dell_ai.auth.hf_auth_check") as mock_auth_check:
        # Simulate a RepositoryNotFoundError from huggingface_hub
        mock_auth_check.side_effect = RepositoryNotFoundError("Repository not found")

        with pytest.raises(ResourceNotFoundError) as exc_info:
            check_model_access("test-org/nonexistent-model", token="test-token")

        error = exc_info.value
        assert error.resource_type == "model"
        assert error.resource_id == "test-org/nonexistent-model"


def test_check_model_access_other_error():
    """Test model access check with an unexpected error."""
    with patch("dell_ai.auth.hf_auth_check") as mock_auth_check:
        # Simulate a generic error
        mock_auth_check.side_effect = Exception("Network error")

        with pytest.raises(AuthenticationError) as exc_info:
            check_model_access("test-org/some-model", token="test-token")

        assert "Failed to check model access" in str(exc_info.value)
