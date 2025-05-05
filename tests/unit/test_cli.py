"""Tests for the Dell AI CLI commands."""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from dell_ai.cli.main import app
from dell_ai.exceptions import AuthenticationError, ResourceNotFoundError


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
