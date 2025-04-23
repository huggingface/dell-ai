"""Unit tests for the DellAIClient class."""

import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import HTTPError

from dell_ai.client import DellAIClient
from dell_ai.exceptions import AuthenticationError, APIError


def test_client_initialization_with_token():
    """
    Test that the client can be initialized with a valid token.
    Verifies token storage and header setup.
    """
    with patch("dell_ai.client.auth.validate_token") as mock_validate:
        mock_validate.return_value = True

        with patch("requests.Session") as mock_session:
            session_instance = MagicMock()
            session_instance.headers = {}
            mock_session.return_value = session_instance

            token = "test-token"
            client = DellAIClient(token=token)

            assert client.token == token
            assert session_instance.headers["Authorization"] == f"Bearer {token}"
            mock_validate.assert_called_once_with(token)


def test_client_initialization_without_token():
    """
    Test that the client can be initialized without a token.
    Verifies fallback behavior when no token is provided.
    """
    with patch("dell_ai.client.auth.get_token") as mock_get_token:
        mock_get_token.return_value = None

        with patch("requests.Session") as mock_session:
            session_instance = MagicMock()
            session_instance.headers = {}
            mock_session.return_value = session_instance

            client = DellAIClient()

            assert client.token is None
            assert "Authorization" not in session_instance.headers


def test_client_initialization_with_invalid_token():
    """
    Test that the client raises an error when initialized with an invalid token.
    """
    with patch("dell_ai.client.auth.validate_token") as mock_validate:
        mock_validate.return_value = False

        with pytest.raises(AuthenticationError) as exc_info:
            DellAIClient(token="invalid-token")

        assert "Invalid authentication token" in str(exc_info.value)


def test_make_request_success():
    """
    Test successful API request.
    Verifies request construction and response handling.
    """
    with patch("requests.Session") as mock_session:
        session_instance = MagicMock()
        session_instance.headers = {}
        mock_session.return_value = session_instance

        # Mock successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.status_code = 200
        session_instance.request.return_value = mock_response

        client = DellAIClient(token="test-token")
        result = client._make_request("GET", "/test")

        assert result == {"data": "test"}
        session_instance.request.assert_called_once_with(
            method="GET", url=f"{client.base_url}/test", params=None, json=None
        )


def test_make_request_error():
    """
    Test error handling in API requests.
    Verifies that API errors are properly converted to exceptions.
    """
    with patch("requests.Session") as mock_session:
        session_instance = MagicMock()
        session_instance.headers = {}
        mock_session.return_value = session_instance

        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.return_value = {"message": "Internal Server Error"}

        # Create a proper HTTPError
        http_error = HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error
        session_instance.request.return_value = mock_response

        client = DellAIClient(token="test-token")

        with pytest.raises(APIError) as exc_info:
            client._make_request("GET", "/test")

        assert "Internal Server Error" in str(exc_info.value)
