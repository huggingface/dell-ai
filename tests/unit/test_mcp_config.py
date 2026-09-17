import json
from unittest.mock import Mock

import pytest

from dell_ai.mcp.client import _resolve_token, create_client
from dell_ai.mcp.config import (
    MCPConfig,
    MCPConfigError,
    load_config,
)


def test_mcp_config_defaults():
    cfg = MCPConfig()
    assert cfg.transport == "stdio"
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8000
    assert cfg.allow_destructive is False
    assert cfg.capabilities.tools is True
    assert cfg.capabilities.resources is True
    assert cfg.capabilities.prompts is True


def test_mcp_config_ignores_unknown_fields():
    cfg = MCPConfig(unknown_field="ignored")
    assert not hasattr(cfg, "unknown_field")


def test_load_config_from_path(tmp_path):
    config_file = tmp_path / "mcp.json"
    config_file.write_text(json.dumps({"transport": "streamable-http", "port": 3000}))
    cfg = load_config(config_file)
    assert cfg.transport == "streamable-http"
    assert cfg.port == 3000


def test_load_config_local_overrides_global(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "dell_ai.mcp.config.get_global_mcp_path", lambda: tmp_path / "global.json"
    )
    monkeypatch.setattr(
        "dell_ai.mcp.config.get_local_mcp_path", lambda: tmp_path / "local.json"
    )
    (tmp_path / "global.json").write_text(json.dumps({"host": "0.0.0.0", "port": 1111}))
    (tmp_path / "local.json").write_text(json.dumps({"port": 2222}))
    cfg = load_config()
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 2222


def test_load_config_allows_missing_default_files(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "dell_ai.mcp.config.get_global_mcp_path", lambda: tmp_path / "global.json"
    )
    monkeypatch.setattr(
        "dell_ai.mcp.config.get_local_mcp_path", lambda: tmp_path / "local.json"
    )

    assert load_config() == MCPConfig()


@pytest.mark.parametrize("invalid_file", ["global.json", "local.json"])
def test_load_config_rejects_invalid_discovered_file(
    tmp_path, monkeypatch, invalid_file
):
    monkeypatch.setattr(
        "dell_ai.mcp.config.get_global_mcp_path", lambda: tmp_path / "global.json"
    )
    monkeypatch.setattr(
        "dell_ai.mcp.config.get_local_mcp_path", lambda: tmp_path / "local.json"
    )
    (tmp_path / "global.json").write_text('{"allow_destructive": true}')
    (tmp_path / "local.json").write_text('{"allow_destructive": false}')
    invalid_path = tmp_path / invalid_file
    invalid_path.write_text('{"allow_destructive": false,')

    with pytest.raises(MCPConfigError, match="Invalid JSON") as exc:
        load_config()

    assert str(invalid_path) in str(exc.value)


def test_resolve_token_env(monkeypatch):
    monkeypatch.setenv("TEST_HF_TOKEN", "abc123")
    assert _resolve_token("env:TEST_HF_TOKEN") == "abc123"
    assert _resolve_token("TEST_HF_TOKEN") == "abc123"
    assert _resolve_token("env:MISSING") is None


def test_resolve_token_file(tmp_path):
    token_file = tmp_path / "token.txt"
    token_file.write_text("filetoken\n")
    assert _resolve_token(f"file:{token_file}") == "filetoken"
    assert _resolve_token("file:/nonexistent") is None


@pytest.mark.parametrize("token_source", ["env", "file", "default"])
@pytest.mark.parametrize(
    "snippet",
    [
        "docker run -e HF_TOKEN=$$_TOKEN_$$ test-image",
        "helm install test-app test-chart --set token=$$_TOKEN_$$",
        "apiVersion: v1\nkind: Secret\nstringData:\n  token: $$_TOKEN_$$",
    ],
    ids=["docker", "helm", "kubernetes"],
)
def test_deployment_uses_mcp_client_token(tmp_path, monkeypatch, token_source, snippet):
    monkeypatch.setattr("dell_ai.env.load_all_env_to_os", lambda: None)
    monkeypatch.setattr("dell_ai.auth.validate_token", lambda token: True)
    monkeypatch.setattr("dell_ai.auth.get_token", lambda: "ambient-token")

    source = None
    expected_token = "ambient-token"
    if token_source == "env":
        monkeypatch.setenv("TEST_MCP_HF_TOKEN", "configured-token")
        source = "env:TEST_MCP_HF_TOKEN"
        expected_token = "configured-token"
    elif token_source == "file":
        token_file = tmp_path / "token.txt"
        token_file.write_text("configured-token\n")
        source = f"file:{token_file}"
        expected_token = "configured-token"

    client = create_client(MCPConfig(hf_token_source=source))
    # A later change to the ambient token must not change deployment identity.
    monkeypatch.setattr("dell_ai.auth.get_token", lambda: "different-token")
    mock_run = Mock(return_value=Mock(stdout="container-id\n", stderr=""))
    monkeypatch.setattr("subprocess.run", mock_run)

    result = client._execute_snippet(snippet)

    assert result["success"] is True
    assert client.session.headers["Authorization"] == f"Bearer {expected_token}"
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    executed_snippet = kwargs["input"] if "input" in kwargs else args[0]
    assert expected_token in executed_snippet
    assert "different-token" not in executed_snippet
    assert "$$_TOKEN_$$" not in executed_snippet
