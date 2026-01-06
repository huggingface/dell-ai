"""Unit tests for the DellAIClient class."""

import json

import pytest
from unittest.mock import patch, MagicMock, call
from requests.exceptions import HTTPError

from dell_ai.client import DellAIClient, _sanitize_response
from dell_ai.exceptions import (
    AuthenticationError,
    APIError,
    GatedRepoAccessError,
)


class TestSanitizeResponse:
    """Tests for the _sanitize_response function.

    Fixes: https://github.com/huggingface/dell-ai/issues/30
    """

    def test_sanitize_empty_input(self):
        """Test sanitization of empty and None inputs."""
        assert _sanitize_response(None) == ""
        assert _sanitize_response("") == ""

    def test_sanitize_normal_text(self):
        """Test that normal text without sensitive data is unchanged."""
        text = "This is a normal error message"
        assert _sanitize_response(text) == text

    def test_sanitize_truncates_long_response(self):
        """Test that long responses are truncated."""
        long_text = "x" * 1000
        result = _sanitize_response(long_text)
        assert len(result) < 1000
        assert result.endswith("... (truncated)")
        assert result.startswith("x" * 500)

    def test_sanitize_custom_max_length(self):
        """Test truncation with custom max length."""
        text = "x" * 200
        result = _sanitize_response(text, max_length=100)
        assert len(result) == 100 + len("... (truncated)")
        assert result.endswith("... (truncated)")

    def test_sanitize_redacts_bearer_token(self):
        """Test that bearer tokens are redacted."""
        text = "Error: Bearer abc123xyz789token in header"
        result = _sanitize_response(text)
        assert "abc123xyz789token" not in result
        assert "[REDACTED]" in result
        assert "Bearer " in result

    def test_sanitize_redacts_token_field(self):
        """Test that token fields in JSON-like responses are redacted."""
        text = '{"token": "abcdefghij1234567890secrettoken"}'
        result = _sanitize_response(text)
        assert "abcdefghij1234567890secrettoken" not in result
        assert "[REDACTED]" in result

    def test_sanitize_redacts_api_key(self):
        """Test that API keys are redacted."""
        text = 'api_key: sk_live_abcdefghij1234567890'
        result = _sanitize_response(text)
        assert "sk_live_abcdefghij1234567890" not in result
        assert "[REDACTED]" in result

    def test_sanitize_redacts_secret(self):
        """Test that secrets are redacted."""
        text = '{"secret": "my_super_secret_value_12345"}'
        result = _sanitize_response(text)
        assert "my_super_secret_value_12345" not in result
        assert "[REDACTED]" in result

    def test_sanitize_redacts_password(self):
        """Test that passwords are redacted."""
        text = 'password: mysecretpassword123'
        result = _sanitize_response(text)
        assert "mysecretpassword123" not in result
        assert "[REDACTED]" in result

    def test_sanitize_multiple_sensitive_values(self):
        """Test that multiple sensitive values are all redacted."""
        text = 'Bearer token123abc, api_key: key456def789012345678'
        result = _sanitize_response(text)
        assert "token123abc" not in result
        assert "key456def789012345678" not in result
        assert result.count("[REDACTED]") == 2

    def test_sanitize_case_insensitive(self):
        """Test that pattern matching is case-insensitive."""
        text = "BEARER MySecretToken123"
        result = _sanitize_response(text)
        assert "MySecretToken123" not in result
        assert "[REDACTED]" in result


class TestDellAIClient:
    """Tests for the DellAIClient class."""

    def test_initialization_with_token(self):
        """Test client initialization with an explicit token."""
        with (
            patch("dell_ai.client.requests.Session") as mock_session_class,
            patch(
                "dell_ai.client.auth.validate_token", return_value=True
            ) as mock_validate,
        ):
            mock_session = MagicMock()
            mock_session.headers = {}
            mock_session_class.return_value = mock_session

            client = DellAIClient(token="test-token")

            assert client.token == "test-token"
            assert mock_session.headers["Authorization"] == "Bearer test-token"
            mock_validate.assert_called_once_with("test-token")

    def test_initialization_without_token(self):
        """Test client initialization without a token."""
        with (
            patch("dell_ai.client.requests.Session") as mock_session_class,
            patch("dell_ai.client.auth.get_token", return_value=None) as mock_get_token,
        ):
            mock_session = MagicMock()
            mock_session.headers = {}
            mock_session_class.return_value = mock_session

            client = DellAIClient()

            assert client.token is None
            assert "Authorization" not in mock_session.headers
            mock_get_token.assert_called_once()

    def test_initialization_with_invalid_token(self):
        """Test client initialization with an invalid token."""
        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token", return_value=False),
        ):
            with pytest.raises(AuthenticationError):
                DellAIClient(token="invalid-token")

    def test_make_request_success(self):
        """Test successful API request."""
        with (
            patch("dell_ai.client.requests.Session") as mock_session_class,
            patch("dell_ai.client.auth.validate_token", return_value=True),
        ):
            # Setup mock session
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Setup mock response
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": "test"}
            mock_response.status_code = 200
            mock_session.request.return_value = mock_response

            # Create client and make request
            client = DellAIClient(token="test-token")
            result = client._make_request("GET", "/test-endpoint")

            # Verify results
            assert result == {"data": "test"}
            mock_session.request.assert_called_once()
            call_kwargs = mock_session.request.call_args.kwargs
            assert call_kwargs["method"] == "GET"
            assert call_kwargs["url"] == "https://dell.huggingface.co/api/test-endpoint"

    def test_make_request_error(self):
        """Test error handling in API requests."""
        with (
            patch("dell_ai.client.requests.Session") as mock_session_class,
            patch("dell_ai.client.auth.validate_token", return_value=True),
        ):
            # Setup mock session
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Setup mock error response
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_response.json.return_value = {"message": "Internal Server Error"}

            # Setup HTTP error
            http_error = HTTPError(response=mock_response)
            mock_response.raise_for_status.side_effect = http_error
            mock_session.request.return_value = mock_response

            # Create client and test error handling
            client = DellAIClient(token="test-token")
            with pytest.raises(APIError) as exc_info:
                client._make_request("GET", "/test-endpoint")

            # Verify error message
            assert "Internal Server Error" in str(exc_info.value)

    def test_make_request_error_sanitizes_sensitive_data(self):
        """Test that sensitive data in error responses is sanitized.

        Fixes: https://github.com/huggingface/dell-ai/issues/30
        """
        with (
            patch("dell_ai.client.requests.Session") as mock_session_class,
            patch("dell_ai.client.auth.validate_token", return_value=True),
        ):
            # Setup mock session
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Setup mock error response with sensitive data
            mock_response = MagicMock()
            mock_response.status_code = 500
            # Include sensitive data that should be redacted
            mock_response.text = 'Error: Bearer secret_token_12345 was invalid'
            mock_response.json.side_effect = json.JSONDecodeError("Not JSON", "", 0)

            # Setup HTTP error
            http_error = HTTPError(response=mock_response)
            mock_response.raise_for_status.side_effect = http_error
            mock_session.request.return_value = mock_response

            # Create client and test error handling
            client = DellAIClient(token="test-token")
            with pytest.raises(APIError) as exc_info:
                client._make_request("GET", "/test-endpoint")

            # Verify sensitive data is redacted
            error_str = str(exc_info.value)
            assert "secret_token_12345" not in error_str
            assert "[REDACTED]" in error_str

    def test_make_request_error_truncates_long_response(self):
        """Test that long error responses are truncated.

        Fixes: https://github.com/huggingface/dell-ai/issues/30
        """
        with (
            patch("dell_ai.client.requests.Session") as mock_session_class,
            patch("dell_ai.client.auth.validate_token", return_value=True),
        ):
            # Setup mock session
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Setup mock error response with very long text
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "x" * 2000  # Very long response
            mock_response.json.side_effect = json.JSONDecodeError("Not JSON", "", 0)

            # Setup HTTP error
            http_error = HTTPError(response=mock_response)
            mock_response.raise_for_status.side_effect = http_error
            mock_session.request.return_value = mock_response

            # Create client and test error handling
            client = DellAIClient(token="test-token")
            with pytest.raises(APIError) as exc_info:
                client._make_request("GET", "/test-endpoint")

            # Verify response is truncated
            error_str = str(exc_info.value)
            assert len(error_str) < 2000
            assert "truncated" in error_str

    def test_is_authenticated_with_token(self):
        """Test is_authenticated when a token is available."""
        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token") as mock_validate,
            patch("dell_ai.client.auth.get_token", return_value="test-token"),
        ):
            # First call during initialization should return True
            # Second call during is_authenticated should return True
            mock_validate.side_effect = [True, True]

            client = DellAIClient(token="test-token")
            result = client.is_authenticated()

            assert result is True
            assert mock_validate.call_count == 2
            assert mock_validate.call_args_list[1] == call("test-token")

    def test_is_authenticated_without_token(self):
        """Test is_authenticated when no token is available."""
        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.get_token", return_value=None),
        ):
            client = DellAIClient()
            assert client.is_authenticated() is False

    def test_is_authenticated_with_invalid_token(self):
        """Test is_authenticated when the token is invalid."""
        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token") as mock_validate,
            patch("dell_ai.client.auth.get_token", return_value="test-token"),
        ):
            # First call during initialization should return True
            # Second call during is_authenticated should return False
            mock_validate.side_effect = [True, False]

            client = DellAIClient(token="test-token")
            result = client.is_authenticated()

            assert result is False
            assert mock_validate.call_count == 2

    def test_is_authenticated_exception(self):
        """Test is_authenticated when validation raises an exception."""
        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token") as mock_validate,
            patch("dell_ai.client.auth.get_token", return_value="test-token"),
        ):
            # First call during initialization should return True
            # Second call during is_authenticated should raise Exception
            mock_validate.side_effect = [True, Exception("Test error")]

            client = DellAIClient(token="test-token")
            result = client.is_authenticated()

            assert result is False
            assert mock_validate.call_count == 2

    def test_get_user_info(self):
        """Test the get_user_info method."""
        expected_info = {"name": "Test User", "email": "test@example.com"}

        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token", return_value=True),
            patch("dell_ai.client.auth.get_user_info") as mock_get_info,
        ):
            mock_get_info.return_value = expected_info

            client = DellAIClient(token="test-token")
            result = client.get_user_info()

            assert result == expected_info
            mock_get_info.assert_called_once_with("test-token")

    def test_get_user_info_no_token(self):
        """Test get_user_info when no token is available."""
        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.get_token", return_value=None),
        ):
            client = DellAIClient()
            with pytest.raises(AuthenticationError):
                client.get_user_info()

    def test_check_model_access_success(self):
        """Test successful model access check."""
        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token", return_value=True),
            patch("dell_ai.client.auth.check_model_access") as mock_check_access,
        ):
            mock_check_access.return_value = True

            client = DellAIClient(token="test-token")
            result = client.check_model_access("org/model")

            assert result is True
            mock_check_access.assert_called_once_with("org/model", "test-token")

    def test_check_model_access_gated_repo(self):
        """Test model access check for a gated repository."""
        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token", return_value=True),
            patch("dell_ai.client.auth.check_model_access") as mock_check_access,
        ):
            mock_check_access.side_effect = GatedRepoAccessError("org/gated-model")

            client = DellAIClient(token="test-token")
            with pytest.raises(GatedRepoAccessError) as exc_info:
                client.check_model_access("org/gated-model")

            assert exc_info.value.model_id == "org/gated-model"
            assert "Access denied" in str(exc_info.value)

    def test_list_models(self):
        """Test list_models method."""
        expected_models = ["org/model1", "org/model2"]

        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token", return_value=True),
            patch("dell_ai.models.list_models") as mock_list_models,
        ):
            mock_list_models.return_value = expected_models

            client = DellAIClient(token="test-token")
            result = client.list_models()

            assert result == expected_models
            mock_list_models.assert_called_once_with(client)

    def test_get_model(self):
        """Test get_model method."""
        mock_model = MagicMock()

        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token", return_value=True),
            patch("dell_ai.models.get_model") as mock_get_model,
        ):
            mock_get_model.return_value = mock_model

            client = DellAIClient(token="test-token")
            result = client.get_model("org/model1")

            assert result == mock_model
            mock_get_model.assert_called_once_with(client, "org/model1")

    def test_list_platforms(self):
        """Test list_platforms method."""
        expected_platforms = ["platform1", "platform2"]

        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token", return_value=True),
            patch("dell_ai.platforms.list_platforms") as mock_list_platforms,
        ):
            mock_list_platforms.return_value = expected_platforms

            client = DellAIClient(token="test-token")
            result = client.list_platforms()

            assert result == expected_platforms
            mock_list_platforms.assert_called_once_with(client)

    def test_get_platform(self):
        """Test get_platform method."""
        mock_platform = MagicMock()

        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token", return_value=True),
            patch("dell_ai.platforms.get_platform") as mock_get_platform,
        ):
            mock_get_platform.return_value = mock_platform

            client = DellAIClient(token="test-token")
            result = client.get_platform("platform1")

            assert result == mock_platform
            mock_get_platform.assert_called_once_with(client, "platform1")

    def test_get_deployment_snippet(self):
        """Test get_deployment_snippet method."""
        expected_snippet = "docker run --gpus all registry.huggingface.co/model:latest"
        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token", return_value=True),
            patch("dell_ai.models.get_deployment_snippet") as mock_get_snippet,
        ):
            mock_get_snippet.return_value = expected_snippet

            client = DellAIClient(token="test-token")
            result = client.get_deployment_snippet(
                model_id="org/model",
                platform_id="platform1",
                engine="docker",
                num_gpus=1,
                num_replicas=1,
            )

            assert result == expected_snippet
            mock_get_snippet.assert_called_once_with(
                client,
                model_id="org/model",
                platform_id="platform1",
                engine="docker",
                num_gpus=1,
                num_replicas=1,
            )

    def test_list_apps(self):
        """Test list_apps method."""
        expected_apps = ["app1", "app2"]

        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token", return_value=True),
            patch("dell_ai.apps.list_apps") as mock_list_apps,
        ):
            mock_list_apps.return_value = expected_apps

            client = DellAIClient(token="test-token")
            result = client.list_apps()

            assert result == expected_apps
            mock_list_apps.assert_called_once_with(client)

    def test_get_app(self):
        """Test get_app method."""
        mock_app = MagicMock()

        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token", return_value=True),
            patch("dell_ai.apps.get_app") as mock_get_app,
        ):
            mock_get_app.return_value = mock_app

            client = DellAIClient(token="test-token")
            result = client.get_app("app1")

            assert result == mock_app
            mock_get_app.assert_called_once_with(client, "app1")

    def test_get_app_snippet(self):
        """Test get_app_snippet method."""
        expected_snippet = "helm install app1 --set storage.class=standard"
        config = [{"helmPath": "storage.class", "type": "string", "value": "standard"}]

        with (
            patch("dell_ai.client.requests.Session"),
            patch("dell_ai.client.auth.validate_token", return_value=True),
            patch("dell_ai.apps.get_app_snippet") as mock_get_app_snippet,
        ):
            mock_get_app_snippet.return_value = expected_snippet

            client = DellAIClient(token="test-token")
            result = client.get_app_snippet("app1", config)

            assert result == expected_snippet
            mock_get_app_snippet.assert_called_once_with(client, "app1", config)
