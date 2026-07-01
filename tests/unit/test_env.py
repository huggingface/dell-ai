"""Unit tests for environment variable management functionality."""

import json
import os
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from dell_ai import env
from dell_ai.cli.main import app

runner = CliRunner()


@pytest.fixture
def temp_env_files(tmp_path, monkeypatch):
    """Fixture to mock local and global env file paths."""
    local_file = tmp_path / "local.json"
    global_file = tmp_path / "global.json"

    monkeypatch.setattr(env, "get_local_env_path", lambda: local_file)
    monkeypatch.setattr(env, "get_global_env_path", lambda: global_file)

    # Save original os.environ
    original_environ = dict(os.environ)

    yield local_file, global_file

    # Restore os.environ
    os.environ.clear()
    os.environ.update(original_environ)


def test_set_and_get_env_var_local(temp_env_files):
    """Test setting and getting local environment variables."""
    local_file, _ = temp_env_files

    env.set_env_var("TEST_LOCAL", "local_val", is_global=False)

    # Verify file content
    assert local_file.exists()
    with open(local_file, "r") as f:
        data = json.load(f)
        assert data["TEST_LOCAL"] == "local_val"

    # Verify getter
    assert env.get_env_var("TEST_LOCAL") == "local_val"


def test_set_and_get_env_var_global(temp_env_files):
    """Test setting and getting global environment variables."""
    _, global_file = temp_env_files

    env.set_env_var("TEST_GLOBAL", "global_val", is_global=True)

    # Verify file content
    assert global_file.exists()
    with open(global_file, "r") as f:
        data = json.load(f)
        assert data["TEST_GLOBAL"] == "global_val"

    # Verify getter
    assert env.get_env_var("TEST_GLOBAL") == "global_val"


def test_get_env_var_overrides(temp_env_files):
    """Test that local variables override global ones, and os.environ overrides both."""
    local_file, global_file = temp_env_files

    # 1. Set in both files
    env.set_env_var("OVERRIDE_VAR", "global_val", is_global=True)
    env.set_env_var("OVERRIDE_VAR", "local_val", is_global=False)

    # Get should return local val
    if "OVERRIDE_VAR" in os.environ:
        del os.environ["OVERRIDE_VAR"]
    assert env.get_env_var("OVERRIDE_VAR") == "local_val"

    # 2. Set in os.environ
    os.environ["OVERRIDE_VAR"] = "os_val"
    assert env.get_env_var("OVERRIDE_VAR") == "os_val"


def test_delete_env_var(temp_env_files):
    """Test deleting environment variables."""
    local_file, global_file = temp_env_files

    # Set and delete local
    env.set_env_var("DEL_LOCAL", "val", is_global=False)
    assert env.get_env_var("DEL_LOCAL") == "val"
    assert env.delete_env_var("DEL_LOCAL", is_global=False) is True
    assert env.get_env_var("DEL_LOCAL") is None

    # Try deleting non-existent
    assert env.delete_env_var("NON_EXISTENT", is_global=False) is False


def test_list_env_vars(temp_env_files):
    """Test listing environment variables with scopes."""
    env.set_env_var("VAR1", "val1", is_global=True)
    env.set_env_var("VAR2", "val2", is_global=False)
    env.set_env_var("VAR1", "val1_local", is_global=False)  # local override

    # Global only
    global_vars = env.list_env_vars(is_global=True)
    assert global_vars == {"VAR1": "val1"}

    # Local only
    local_vars = env.list_env_vars(is_global=False)
    assert local_vars == {"VAR2": "val2", "VAR1": "val1_local"}

    # Combined
    combined = env.list_env_vars(is_global=None)
    assert combined == {"VAR1": "val1_local", "VAR2": "val2"}


def test_load_all_env_to_os(temp_env_files):
    """Test loading env files into active process os.environ."""
    env.set_env_var("LOAD_VAR", "loaded", is_global=False)
    if "LOAD_VAR" in os.environ:
        del os.environ["LOAD_VAR"]

    env.load_all_env_to_os()
    assert os.environ["LOAD_VAR"] == "loaded"


# CLI env command tests


@patch("dell_ai.cli.main.get_client")
def test_cli_env_set_and_get(mock_get_client, temp_env_files):
    """Test 'dell-ai env set' and 'dell-ai env get' CLI commands."""
    # Set local (use a non-sensitive name to avoid masking)
    result = runner.invoke(app, ["env", "set", "MY_VAR", "my_value"])
    assert result.exit_code == 0
    assert "Successfully set environment variable 'MY_VAR' locally." in result.stdout

    # Get
    result = runner.invoke(app, ["env", "get", "MY_VAR"])
    assert result.exit_code == 0
    assert "my_value" in result.stdout

    # Set global
    result = runner.invoke(app, ["env", "set", "MY_GLOBAL", "global_value", "--global"])
    assert result.exit_code == 0
    assert (
        "Successfully set environment variable 'MY_GLOBAL' globally." in result.stdout
    )


@patch("dell_ai.cli.main.get_client")
def test_cli_env_list_and_delete(mock_get_client, temp_env_files):
    """Test 'dell-ai env list' and 'dell-ai env delete' CLI commands."""
    runner.invoke(app, ["env", "set", "VAR1", "val1"])
    runner.invoke(app, ["env", "set", "VAR2", "val2", "--global"])

    # List combined
    result = runner.invoke(app, ["env", "list"])
    assert result.exit_code == 0
    assert "VAR1=val1" in result.stdout
    assert "VAR2=val2" in result.stdout

    # List local only
    result = runner.invoke(app, ["env", "list", "--local"])
    assert result.exit_code == 0
    assert "VAR1=val1" in result.stdout
    assert "VAR2=val2" not in result.stdout

    # Delete local
    result = runner.invoke(app, ["env", "delete", "VAR1"])
    assert result.exit_code == 0
    assert "Successfully deleted local environment variable 'VAR1'." in result.stdout

    # Delete non-existent
    result = runner.invoke(app, ["env", "delete", "NON_EXISTENT"])
    assert result.exit_code == 1
    assert "Error" in result.stdout
