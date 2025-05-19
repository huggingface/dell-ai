"""Unit tests for the DellAIClient class."""

import pytest
from unittest.mock import patch, MagicMock, call
from requests.exceptions import HTTPError

from dell_ai.client import DellAIClient
from dell_ai.exceptions import (
    AuthenticationError,
    APIError,
    GatedRepoAccessError,
)


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
