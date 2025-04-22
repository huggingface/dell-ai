"""Unit tests for the DellAIClient class."""

import json
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException

from dell_ai.client import DellAIClient
from dell_ai.exceptions import (
    APIError,
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
)


@pytest.fixture
def mock_session():
    """Fixture to mock the requests Session."""
    session = MagicMock()
    session.headers = {}
    return session


@pytest.fixture
def mock_requests(mock_session):
    """Fixture to mock the requests library."""
    with patch("requests.Session", return_value=mock_session) as mock:
        yield mock


@pytest.fixture
def mock_hf_folder():
    """Fixture to mock the HuggingFace folder."""
    with patch("dell_ai.auth.HfFolder") as mock_folder:
        mock_folder_instance = Mock()
        mock_folder_instance.get_token.return_value = None
        mock_folder.return_value = mock_folder_instance
        yield mock_folder


@pytest.fixture
def mock_hf_api():
    """Fixture to mock the HuggingFace API."""
    with patch("dell_ai.auth.HfApi") as mock_api:
        mock_api_instance = Mock()
        mock_api_instance.whoami.return_value = {"username": "test-user"}
        mock_api.return_value = mock_api_instance
        yield mock_api


@pytest.fixture
def mock_auth(mock_hf_api, mock_hf_folder):
    """Fixture to mock the authentication module."""
    with patch("dell_ai.client.auth") as mock_auth:
        mock_auth.get_token.return_value = None
        mock_auth.validate_token.return_value = True
        mock_auth.get_user_info.return_value = {"username": "test-user"}
        yield mock_auth


@pytest.fixture
def client(mock_requests, mock_auth, mock_session):
    """Fixture to create a DellAIClient instance with mocked dependencies."""
    mock_auth.get_token.return_value = "test-token"
    return DellAIClient()


def test_client_initialization_with_token(mock_requests, mock_auth, mock_session):
    """Test client initialization with a token."""
    token = "test-token"
    mock_auth.validate_token.return_value = True
    client = DellAIClient(token=token)

    assert client.token == token
    assert mock_session.headers["Authorization"] == f"Bearer {token}"


def test_client_initialization_without_token(mock_requests, mock_auth, mock_session):
    """Test client initialization without a token."""
    mock_auth.get_token.return_value = "test-token"
    mock_auth.validate_token.return_value = True
    client = DellAIClient()

    assert client.token == "test-token"
    assert mock_session.headers["Authorization"] == "Bearer test-token"


def test_client_initialization_with_invalid_token(
    mock_requests, mock_auth, mock_session
):
    """Test client initialization with an invalid token."""
    mock_auth.validate_token.return_value = False

    with pytest.raises(AuthenticationError) as exc_info:
        DellAIClient(token="invalid-token")

    assert "Invalid authentication token" in str(exc_info.value)


def test_make_request_success(client, mock_session):
    """Test successful API request."""
    mock_response = Mock()
    mock_response.json.return_value = {"data": "test"}
    mock_response.status_code = 200
    mock_session.request.return_value = mock_response

    result = client._make_request("GET", "/test")

    assert result == {"data": "test"}
    mock_session.request.assert_called_once_with(
        method="GET", url=f"{client.base_url}/test", params=None, json=None
    )


def test_make_request_authentication_error(client, mock_session):
    """Test handling of authentication errors."""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.json.return_value = {"message": "Unauthorized"}

    mock_session.request.return_value = mock_response
    mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)

    with pytest.raises(AuthenticationError) as exc_info:
        client._make_request("GET", "/test")

    assert "Authentication failed" in str(exc_info.value)


def test_make_request_resource_not_found(client, mock_session):
    """Test handling of resource not found errors."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_response.json.return_value = {"message": "Not Found"}

    mock_session.request.return_value = mock_response
    mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)

    with pytest.raises(ResourceNotFoundError) as exc_info:
        client._make_request("GET", "/models/test-model")

    assert exc_info.value.resource_type == "models"
    assert exc_info.value.resource_id == "test-model"


def test_make_request_validation_error(client, mock_session):
    """Test handling of validation errors."""
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "Invalid input"
    mock_response.json.return_value = {"message": "Invalid input"}

    mock_session.request.return_value = mock_response
    mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)

    with pytest.raises(ValidationError) as exc_info:
        client._make_request("GET", "/test")

    assert "Invalid request" in str(exc_info.value)


def test_make_request_api_error(client, mock_session):
    """Test handling of general API errors."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.json.return_value = {"message": "Internal Server Error"}

    mock_session.request.return_value = mock_response
    mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)

    with pytest.raises(APIError) as exc_info:
        client._make_request("GET", "/test")

    assert exc_info.value.status_code == 500
    assert "Internal Server Error" in str(exc_info.value)


def test_make_request_connection_error(client, mock_session):
    """Test handling of connection errors."""
    mock_session.request.side_effect = ConnectionError("Connection failed")

    with pytest.raises(APIError) as exc_info:
        client._make_request("GET", "/test")

    assert "Connection error" in str(exc_info.value)


def test_make_request_timeout_error(client, mock_session):
    """Test handling of timeout errors."""
    mock_session.request.side_effect = Timeout("Request timed out")

    with pytest.raises(APIError) as exc_info:
        client._make_request("GET", "/test")

    assert "Request timed out" in str(exc_info.value)


def test_make_request_invalid_json(client, mock_session):
    """Test handling of invalid JSON responses."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
    mock_response.text = "Invalid JSON"
    mock_session.request.return_value = mock_response

    with pytest.raises(APIError) as exc_info:
        client._make_request("GET", "/test")

    assert "Invalid JSON response" in str(exc_info.value)


def test_is_authenticated_with_valid_token(client, mock_auth):
    """Test authentication status check with valid token."""
    mock_auth.validate_token.return_value = True
    assert client.is_authenticated() is True


def test_is_authenticated_with_invalid_token(client, mock_auth):
    """Test authentication status check with invalid token."""
    mock_auth.validate_token.return_value = False
    assert client.is_authenticated() is False


def test_is_authenticated_without_token(mock_requests, mock_auth, mock_session):
    """Test authentication status check without token."""
    mock_auth.get_token.return_value = None
    client = DellAIClient()
    assert client.is_authenticated() is False


def test_get_user_info(client, mock_auth):
    """Test getting user information."""
    mock_auth.get_user_info.return_value = {"username": "test-user"}
    result = client.get_user_info()
    assert result == {"username": "test-user"}
