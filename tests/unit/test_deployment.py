"""Unit tests for model and application deployment and status functionalities."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from dell_ai import DellAIClient, env
from dell_ai.cli.main import app

runner = CliRunner()


@pytest.fixture
def mock_subprocess_run():
    """Fixture to mock subprocess.run."""
    with patch("subprocess.run") as mock_run:
        # Mock successful subprocess execution
        mock_proc = MagicMock()
        mock_proc.return_value.returncode = 0
        mock_proc.return_value.stdout = "mock-container-id-abc123xyz\n"
        mock_proc.return_value.stderr = ""
        mock_run.return_value = mock_proc.return_value
        yield mock_run


@pytest.fixture
def temp_env_files(tmp_path, monkeypatch):
    """Fixture to mock env files and reset env vars."""
    local_file = tmp_path / "local.json"
    global_file = tmp_path / "global.json"

    monkeypatch.setattr(env, "get_local_env_path", lambda: local_file)
    monkeypatch.setattr(env, "get_global_env_path", lambda: global_file)

    # Mock validate_token to always succeed for testing
    monkeypatch.setattr("dell_ai.auth.validate_token", lambda token: True)

    # Save original os.environ
    original_environ = dict(os.environ)

    yield local_file, global_file

    # Restore os.environ
    os.environ.clear()
    os.environ.update(original_environ)


def test_deploy_model_docker(mock_subprocess_run, temp_env_files):
    """Test successful Docker deployment of a model."""
    client = DellAIClient(token="mock_token")

    # Mock get_deployment_snippet
    with patch.object(
        client,
        "get_deployment_snippet",
        return_value="docker run -it -p 80:80 tgi-image",
    ):
        result = client.deploy_model(
            model_id="meta-llama/Llama-4",
            platform_id="xe9680",
            engine="docker",
            num_gpus=1,
            num_replicas=1,
            detach=True,
        )

        assert result["success"] is True
        assert result["container_id"] == "mock-container-id-abc123xyz"
        assert result["endpoint"] == "http://localhost:80"

        # Check that environment variables are saved
        assert env.get_env_var("DELL_AI_LAST_DEPLOYED_ENGINE") == "docker"
        assert (
            env.get_env_var("DELL_AI_LAST_DEPLOYED_CONTAINER")
            == "mock-container-id-abc123xyz"
        )
        assert env.get_env_var("DELL_AI_ENDPOINT") == "http://localhost:80"

        # Verify subprocess was called with detached command
        mock_subprocess_run.assert_called_once()
        args, kwargs = mock_subprocess_run.call_args
        assert "-d" in args[0]
        assert "-it" not in args[0]


def test_deploy_model_kubernetes(mock_subprocess_run, temp_env_files):
    """Test successful Kubernetes deployment of a model."""
    client = DellAIClient(token="mock_token")

    # YAML manifest
    k8s_manifest = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: my-tgi"

    with patch.object(client, "get_deployment_snippet", return_value=k8s_manifest):
        result = client.deploy_model(
            model_id="meta-llama/Llama-4",
            platform_id="xe9680",
            engine="kubernetes",
            num_gpus=1,
            num_replicas=1,
            detach=True,
        )

        assert result["success"] is True
        assert result["k8s_deployment"] == "my-tgi"

        # Check that environment variables are saved
        assert env.get_env_var("DELL_AI_LAST_DEPLOYED_ENGINE") == "kubernetes"
        assert env.get_env_var("DELL_AI_LAST_DEPLOYED_K8S_DEPLOYMENT") == "my-tgi"


def test_deploy_app(mock_subprocess_run, temp_env_files):
    """Test successful application deployment."""
    client = DellAIClient(token="mock_token")

    with patch.object(
        client, "get_app_snippet", return_value="helm install my-app chart"
    ):
        result = client.deploy_app(
            app_id="openwebui",
            config=[],
            detach=True,
        )

        assert result["success"] is True
        assert env.get_env_var("DELL_AI_LAST_DEPLOYED_ENGINE") == "helm"


# Realistic DEH multi-line snippet (note the image name contains "-d")
REALISTIC_DOCKER_SNIPPET = """docker run \\
    -it \\
    -p 8080:80 \\
    --shm-size 256g \\
    -e NUM_SHARD=8 \\
    registry.dell.huggingface.co/enterprise-dell-inference-meta-llama"""


def test_deploy_model_docker_realistic_snippet(mock_subprocess_run, temp_env_files):
    """Multi-line DEH snippet: -it must become -d, port parsed, image '-d' ignored."""
    client = DellAIClient(token="mock_token")

    with patch.object(
        client, "get_deployment_snippet", return_value=REALISTIC_DOCKER_SNIPPET
    ):
        result = client.deploy_model(
            model_id="meta-llama/Llama-4",
            platform_id="xe9680",
            engine="docker",
            num_gpus=8,
            num_replicas=1,
            detach=True,
        )

        assert result["success"] is True
        assert result["container_id"] == "mock-container-id-abc123xyz"
        # Port mapping 8080:80 -> host port 8080
        assert result["endpoint"] == "http://localhost:8080"

        args, _ = mock_subprocess_run.call_args
        executed_cmd = args[0]
        assert " -d " in executed_cmd
        assert "-it" not in executed_cmd
        # The image name (which contains a literal "-d") must be preserved
        assert "enterprise-dell-inference-meta-llama" in executed_cmd


def test_deploy_model_persists_to_local_file(mock_subprocess_run, temp_env_files):
    """Deployment metadata must be written to the on-disk local env file."""
    local_file, _ = temp_env_files
    client = DellAIClient(token="mock_token")

    with patch.object(
        client, "get_deployment_snippet", return_value="docker run -it -p 80:80 img"
    ):
        client.deploy_model(
            model_id="meta-llama/Llama-4",
            platform_id="xe9680",
            engine="docker",
            num_gpus=1,
            num_replicas=1,
            detach=True,
        )

    # Verify the values were actually persisted to disk, not just os.environ
    assert local_file.exists()
    with open(local_file, "r") as f:
        data = json.load(f)
    assert data["DELL_AI_ENDPOINT"] == "http://localhost:80"
    assert data["DELL_AI_LAST_DEPLOYED_CONTAINER"] == "mock-container-id-abc123xyz"
    assert data["DELL_AI_LAST_DEPLOYED_ENGINE"] == "docker"


def test_deploy_model_no_detach(temp_env_files):
    """With detach=False, docker should run in foreground (no -d, no container id)."""
    client = DellAIClient(token="mock_token")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        with patch.object(
            client,
            "get_deployment_snippet",
            return_value="docker run -it -p 80:80 img",
        ):
            result = client.deploy_model(
                model_id="meta-llama/Llama-4",
                platform_id="xe9680",
                engine="docker",
                num_gpus=1,
                num_replicas=1,
                detach=False,
            )

        assert result["success"] is True
        assert "container_id" not in result
        args, kwargs = mock_run.call_args
        # Foreground run keeps the original -it and does not capture output
        assert "-it" in args[0]
        assert kwargs.get("capture_output") is not True


def test_deploy_model_failure(temp_env_files):
    """A failing subprocess should be reported and must not persist env vars."""
    client = DellAIClient(token="mock_token")

    with patch("subprocess.run", side_effect=FileNotFoundError("docker not found")):
        with patch.object(
            client,
            "get_deployment_snippet",
            return_value="docker run -it -p 80:80 img",
        ):
            result = client.deploy_model(
                model_id="meta-llama/Llama-4",
                platform_id="xe9680",
                engine="docker",
                num_gpus=1,
                num_replicas=1,
                detach=True,
            )

        assert result["success"] is False
        assert "docker not found" in result["error"]
        # No deployment metadata should be saved on failure
        assert env.get_env_var("DELL_AI_LAST_DEPLOYED_CONTAINER") is None


# CLI Deployment tests


@patch("dell_ai.cli.main.get_client")
def test_cli_models_deploy(mock_get_client, mock_subprocess_run, temp_env_files):
    """Test 'dell-ai models deploy' CLI command."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.deploy_model.return_value = {
        "success": True,
        "container_id": "c-123",
        "endpoint": "http://localhost:80",
    }

    result = runner.invoke(
        app,
        [
            "models",
            "deploy",
            "--model-id",
            "meta-llama/Llama-4",
            "--platform-id",
            "xe9680",
            "--engine",
            "docker",
            "--gpus",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert "🎉 Deployment initiated successfully!" in result.stdout
    assert "Docker Container ID: c-123" in result.stdout
    assert "Endpoint URL: http://localhost:80" in result.stdout


@patch("dell_ai.cli.main.get_client")
def test_cli_apps_deploy(mock_get_client, mock_subprocess_run, temp_env_files):
    """Test 'dell-ai apps deploy' CLI command."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.deploy_app.return_value = {
        "success": True,
    }

    result = runner.invoke(
        app,
        [
            "apps",
            "deploy",
            "openwebui",
            "--config",
            '{"config": []}',
        ],
    )

    assert result.exit_code == 0
    assert "🎉 Application deployment initiated successfully!" in result.stdout


# CLI Status test


@patch("requests.get")
@patch("shutil.which")
def test_cli_status(mock_which, mock_get, mock_subprocess_run, temp_env_files):
    """Test 'dell-ai status' CLI command."""
    # Mock requests.get to return 200 for health check
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    # Mock docker and kubectl binaries as available
    mock_which.side_effect = lambda cmd: f"/usr/bin/{cmd}"

    # Set up mock environment variables
    env.set_env_var("DELL_AI_ENDPOINT", "http://localhost:80")
    env.set_env_var("DELL_AI_CHECKPOINT", "/tmp/mock_checkpoint")
    env.set_env_var("DELL_AI_LAST_DEPLOYED_CONTAINER", "c-123")

    # Create the mock checkpoint directory
    checkpoint_path = Path("/tmp/mock_checkpoint")
    checkpoint_path.mkdir(parents=True, exist_ok=True)

    # Mock docker ps stdout
    mock_subprocess_run.return_value.stdout = (
        "c-123\tmy-container\tenterprise-dell-image\tUp 5 minutes\t0.0.0.0:80->80/tcp"
    )

    result = runner.invoke(app, ["status"])

    # Clean up checkpoint dir
    try:
        checkpoint_path.rmdir()
    except Exception:
        pass

    assert result.exit_code == 0
    assert "Deployed Model Endpoints" in result.stdout
    assert "Online" in result.stdout
    assert "Model Checkpoints" in result.stdout
    assert "Active Local Deployments" in result.stdout
    assert "my-container" in result.stdout
