"""Tests for the Dell AI CLI commands."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner

from dell_ai.cli.main import app
from dell_ai.exceptions import (
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
)


@pytest.fixture
def runner():
    """Fixture that returns a CliRunner instance."""
    return CliRunner()


@pytest.fixture
def mock_auth():
    """Fixture that mocks the authentication module."""
    with patch("dell_ai.cli.main.auth") as mock:
        yield mock


@pytest.fixture
def mock_client():
    """Fixture that mocks the DellAIClient."""
    with patch("dell_ai.cli.main.get_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


def test_auth_login_with_token(runner, mock_auth):
    """Test login command with token provided."""
    # Setup
    mock_auth.login.return_value = None
    mock_auth.get_user_info.return_value = {"name": "Test User"}

    # Execute
    result = runner.invoke(app, ["login", "--token", "test-token"])

    # Verify
    assert result.exit_code == 0
    assert "Successfully logged in as Test User" in result.output
    mock_auth.login.assert_called_once_with("test-token")
    mock_auth.get_user_info.assert_called_once_with("test-token")


def test_auth_login_interactive(runner, mock_auth):
    """Test login command with interactive token input."""
    # Setup
    mock_auth.login.return_value = None
    mock_auth.get_user_info.return_value = {"name": "Test User"}

    # Execute with mocked input
    with patch("typer.prompt", return_value="test-token"):
        result = runner.invoke(app, ["login"])

    # Verify
    assert result.exit_code == 0
    assert "Successfully logged in as Test User" in result.output
    mock_auth.login.assert_called_once_with("test-token")
    mock_auth.get_user_info.assert_called_once_with("test-token")


def test_auth_login_error(runner, mock_auth):
    """Test login command with authentication error."""
    # Setup
    mock_auth.login.side_effect = AuthenticationError("Invalid token")

    # Execute
    result = runner.invoke(app, ["login", "--token", "invalid-token"])

    # Verify
    assert result.exit_code == 1
    assert "Error: Invalid token" in result.output
    mock_auth.login.assert_called_once_with("invalid-token")


def test_auth_logout_confirmed(runner, mock_auth):
    """Test logout command with confirmation."""
    # Setup
    mock_auth.is_logged_in.return_value = True
    mock_auth.logout.return_value = None

    # Execute with mocked confirmation
    with patch("typer.confirm", return_value=True):
        result = runner.invoke(app, ["logout"])

    # Verify
    assert result.exit_code == 0
    assert "Successfully logged out" in result.output
    mock_auth.logout.assert_called_once()


def test_auth_logout_not_confirmed(runner, mock_auth):
    """Test logout command without confirmation."""
    # Setup
    mock_auth.is_logged_in.return_value = True

    # Execute with mocked confirmation
    with patch("typer.confirm", return_value=False):
        result = runner.invoke(app, ["logout"])

    # Verify
    assert result.exit_code == 0
    assert "Logout cancelled" in result.output
    mock_auth.logout.assert_not_called()


def test_auth_logout_not_logged_in(runner, mock_auth):
    """Test logout command when not logged in."""
    # Setup
    mock_auth.is_logged_in.return_value = False

    # Execute
    result = runner.invoke(app, ["logout"])

    # Verify
    assert result.exit_code == 0
    assert "You are not currently logged in" in result.output
    mock_auth.logout.assert_not_called()


def test_auth_status_logged_in(runner, mock_auth):
    """Test whoami command when logged in."""
    # Setup
    mock_auth.is_logged_in.return_value = True
    mock_auth.get_user_info.return_value = {
        "name": "Test User",
        "email": "test@example.com",
        "orgs": [{"name": "Test Org"}],
    }

    # Execute
    result = runner.invoke(app, ["whoami"])

    # Verify
    assert result.exit_code == 0
    assert "Status: Logged in" in result.output
    assert "User: Test User" in result.output
    assert "Email: test@example.com" in result.output
    assert "Organizations: Test Org" in result.output


def test_auth_status_not_logged_in(runner, mock_auth):
    """Test whoami command when not logged in."""
    # Setup
    mock_auth.is_logged_in.return_value = False

    # Execute
    result = runner.invoke(app, ["whoami"])

    # Verify
    assert result.exit_code == 0
    assert "Status: Not logged in" in result.output
    assert "To log in, run: dell-ai login" in result.output


def test_auth_status_error(runner, mock_auth):
    """Test whoami command with authentication error."""
    # Setup
    mock_auth.is_logged_in.return_value = True
    mock_auth.get_user_info.side_effect = AuthenticationError("Token expired")

    # Execute
    result = runner.invoke(app, ["whoami"])

    # Verify
    assert result.exit_code == 1
    assert "Status: Error (Token expired)" in result.output
    assert "Please try logging in again: dell-ai login" in result.output


def test_models_list_success(runner, mock_client):
    """Test models list command with successful response."""
    # Setup
    mock_client.list_models.return_value = ["org1/model1", "org2/model2"]

    # Execute
    result = runner.invoke(app, ["models", "list"])

    # Verify
    assert result.exit_code == 0
    assert '"org1/model1"' in result.output
    assert '"org2/model2"' in result.output
    mock_client.list_models.assert_called_once()


def test_models_list_error(runner, mock_client):
    """Test models list command with error."""
    # Setup
    mock_client.list_models.side_effect = Exception("API error")

    # Execute
    result = runner.invoke(app, ["models", "list"])

    # Verify
    assert result.exit_code == 1
    assert "Error: Failed to list models: API error" in result.output
    mock_client.list_models.assert_called_once()


def test_models_show_success(runner, mock_client):
    """Test models show command with successful response."""
    # Setup
    mock_client.get_model.return_value = {
        "id": "org1/model1",
        "name": "Test Model",
        "description": "A test model",
        "license": "apache-2.0",
    }

    # Execute
    result = runner.invoke(app, ["models", "show", "org1/model1"])

    # Verify
    assert result.exit_code == 0
    assert '"id": "org1/model1"' in result.output
    assert '"name": "Test Model"' in result.output
    assert '"description": "A test model"' in result.output
    assert '"license": "apache-2.0"' in result.output
    mock_client.get_model.assert_called_once_with("org1/model1")


def test_models_show_not_found(runner, mock_client):
    """Test models show command with model not found."""
    # Setup
    mock_client.get_model.side_effect = ResourceNotFoundError(
        resource_type="model", resource_id="org1/nonexistent"
    )

    # Execute
    result = runner.invoke(app, ["models", "show", "org1/nonexistent"])

    # Verify
    assert result.exit_code == 1
    assert "Error: Model not found: org1/nonexistent" in result.output
    mock_client.get_model.assert_called_once_with("org1/nonexistent")


def test_models_show_error(runner, mock_client):
    """Test models show command with error."""
    # Setup
    mock_client.get_model.side_effect = Exception("API error")

    # Execute
    result = runner.invoke(app, ["models", "show", "org1/model1"])

    # Verify
    assert result.exit_code == 1
    assert "Error: Failed to get model information: API error" in result.output
    mock_client.get_model.assert_called_once_with("org1/model1")


def test_platforms_list_success(runner, mock_client):
    """Test platforms list command with successful response."""
    # Setup
    mock_client.list_platforms.return_value = [
        "xe9680-nvidia-h100",
        "xe9640-nvidia-a100",
    ]

    # Execute
    result = runner.invoke(app, ["platforms", "list"])

    # Verify
    assert result.exit_code == 0
    assert '"xe9680-nvidia-h100"' in result.output
    assert '"xe9640-nvidia-a100"' in result.output
    mock_client.list_platforms.assert_called_once()


def test_platforms_list_error(runner, mock_client):
    """Test platforms list command with error."""
    # Setup
    mock_client.list_platforms.side_effect = Exception("API error")

    # Execute
    result = runner.invoke(app, ["platforms", "list"])

    # Verify
    assert result.exit_code == 1
    assert "Error: Failed to list platforms: API error" in result.output
    mock_client.list_platforms.assert_called_once()


def test_platforms_show_success(runner, mock_client):
    """Test platforms show command with successful response."""
    # Setup
    mock_client.get_platform.return_value = {
        "id": "xe9680-nvidia-h100",
        "name": "PowerEdge XE9680",
        "description": "High-performance AI server with NVIDIA H100 GPUs",
        "gpu_type": "NVIDIA H100",
        "gpu_count": 8,
    }

    # Execute
    result = runner.invoke(app, ["platforms", "show", "xe9680-nvidia-h100"])

    # Verify
    assert result.exit_code == 0
    assert '"id": "xe9680-nvidia-h100"' in result.output
    assert '"name": "PowerEdge XE9680"' in result.output
    assert (
        '"description": "High-performance AI server with NVIDIA H100 GPUs"'
        in result.output
    )
    assert '"gpu_type": "NVIDIA H100"' in result.output
    assert '"gpu_count": 8' in result.output
    mock_client.get_platform.assert_called_once_with("xe9680-nvidia-h100")


def test_platforms_show_not_found(runner, mock_client):
    """Test platforms show command with platform not found."""
    # Setup
    mock_client.get_platform.side_effect = ResourceNotFoundError(
        resource_type="platform", resource_id="nonexistent-sku"
    )

    # Execute
    result = runner.invoke(app, ["platforms", "show", "nonexistent-sku"])

    # Verify
    assert result.exit_code == 1
    assert "Error: Platform not found: nonexistent-sku" in result.output
    mock_client.get_platform.assert_called_once_with("nonexistent-sku")


def test_platforms_show_error(runner, mock_client):
    """Test platforms show command with error."""
    # Setup
    mock_client.get_platform.side_effect = Exception("API error")

    # Execute
    result = runner.invoke(app, ["platforms", "show", "xe9680-nvidia-h100"])

    # Verify
    assert result.exit_code == 1
    assert "Error: Failed to get platform information: API error" in result.output
    mock_client.get_platform.assert_called_once_with("xe9680-nvidia-h100")


# Add tests for app CLI commands
@patch("dell_ai.cli.main.get_client")
def test_apps_list(mock_get_client, runner):
    """Test the apps list command."""
    # Mock the client and its list_apps method
    mock_client = Mock()
    mock_client.list_apps.return_value = ["OpenWebUI", "AnythingLLM"]
    mock_get_client.return_value = mock_client

    # Run the command
    result = runner.invoke(app, ["apps", "list"])

    # Check result
    assert result.exit_code == 0
    assert '"OpenWebUI"' in result.output
    assert '"AnythingLLM"' in result.output
    mock_client.list_apps.assert_called_once()


@patch("dell_ai.cli.main.get_client")
def test_apps_show_success(mock_get_client, runner):
    """Test the apps show command when successful."""
    # Mock the client and its get_app method
    mock_client = Mock()
    mock_app = Mock()
    mock_app.model_dump.return_value = {
        "id": "openwebui",
        "name": "OpenWebUI",
        "version": "1.0.0",
        "license": "BSD-3-Clause",
        "tags": ["chat", "llm"],
    }
    mock_client.get_app.return_value = mock_app
    mock_get_client.return_value = mock_client

    # Run the command
    result = runner.invoke(app, ["apps", "show", "openwebui"])

    # Check result
    assert result.exit_code == 0
    assert '"id": "openwebui"' in result.output
    assert '"name": "OpenWebUI"' in result.output
    mock_client.get_app.assert_called_once_with("openwebui")


@patch("dell_ai.cli.main.get_client")
def test_apps_show_not_found(mock_get_client, runner):
    """Test the apps show command when the app isn't found."""
    # Mock the client and its get_app method to raise ResourceNotFoundError
    mock_client = Mock()
    mock_client.get_app.side_effect = ResourceNotFoundError("app", "nonexistent-app")
    mock_get_client.return_value = mock_client

    # Run the command
    result = runner.invoke(app, ["apps", "show", "nonexistent-app"])

    # Check result - The CLI command exits with an error code, but still outputs the error message
    assert "Error:" in result.output
    assert "Application not found: nonexistent-app" in result.output
    mock_client.get_app.assert_called_once_with("nonexistent-app")


@patch("dell_ai.cli.main.get_client")
def test_apps_get_snippet_success(mock_get_client, runner):
    """Test the apps get-snippet command when successful."""
    # Mock the client and its get_app_snippet method
    mock_client = Mock()
    mock_client.get_app_snippet.return_value = (
        "helm install my-app deh/app --set config.value=test"
    )
    mock_get_client.return_value = mock_client

    # Run the command with explicit config JSON
    config = {
        "config": [{"helmPath": "config.value", "type": "string", "value": "test"}]
    }
    config_json = json.dumps(config)
    result = runner.invoke(
        app, ["apps", "get-snippet", "test-app", "--config", config_json]
    )

    # Check result
    assert result.exit_code == 0
    assert "helm install my-app deh/app --set config.value=test" in result.output
    mock_client.get_app_snippet.assert_called_once_with(
        app_id="test-app", config=config["config"]
    )


@patch("dell_ai.cli.main.get_client")
def test_apps_get_snippet_invalid_json(mock_get_client, runner):
    """Test the apps get-snippet command with invalid JSON."""
    # Mock the client
    mock_client = Mock()
    mock_get_client.return_value = mock_client

    # Run the command with invalid JSON
    result = runner.invoke(
        app, ["apps", "get-snippet", "test-app", "--config", "{invalid:json}"]
    )

    # Check result - The CLI command exits with an error code, but still outputs the error message
    assert "Error:" in result.output
    assert "Invalid JSON configuration format" in result.output
    # Ensure the client method wasn't called
    mock_client.get_app_snippet.assert_not_called()


@patch("dell_ai.cli.main.get_client")
def test_models_get_snippet_success(mock_get_client, runner):
    """Test the models get-snippet command when successful."""
    # Mock the client and its get_deployment_snippet method
    mock_client = Mock()
    mock_client.get_deployment_snippet.return_value = (
        "docker run -it --gpus 1 gemma:latest"
    )
    mock_get_client.return_value = mock_client

    # Run the command
    result = runner.invoke(
        app,
        [
            "models",
            "get-snippet",
            "--model-id",
            "google/gemma-3-27b-it",
            "--platform-id",
            "xe9680-nvidia-h100",
        ],
    )

    # Check result
    assert result.exit_code == 0
    assert "docker run -it --gpus 1 gemma:latest" in result.output
    mock_client.get_deployment_snippet.assert_called_once_with(
        model_id="google/gemma-3-27b-it",
        platform_id="xe9680-nvidia-h100",
        engine="docker",
        num_gpus=1,
        num_replicas=1,
    )


@pytest.mark.skip(
    reason="`rich` messes up the output in the CI, whilst this runs locally just fine"
)
@patch("dell_ai.cli.main.get_client")
def test_models_get_snippet_validation_error(mock_get_client, runner):
    """Test the models get-snippet command with validation error."""
    # Mock the client and its get_deployment_snippet method to raise ValidationError
    mock_client = Mock()
    mock_client.get_deployment_snippet.side_effect = ValidationError(
        "Invalid number of GPUs (0) for model google/gemma-3-27b-it. Valid GPU counts: 1, 2"
    )
    mock_get_client.return_value = mock_client

    # Run the command with invalid parameters
    result = runner.invoke(
        app,
        [
            "models",
            "get-snippet",
            "--model-id",
            "google/gemma-3-27b-it",
            "--platform-id",
            "xe9680-nvidia-h100",
            "--gpus",
            "0",  # Invalid value
        ],
    )

    # Check result - Typer performs its own validation for this case
    assert "Invalid value for '--gpus'" in result.output
    assert "0 is not in the range" in result.output
