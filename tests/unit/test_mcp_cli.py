import json
from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from dell_ai.cli.main import app
from dell_ai.mcp.cli import _read_config


@pytest.fixture
def runner():
    return CliRunner()


def test_mcp_validate_config(runner, tmp_path):
    config_file = tmp_path / "mcp.json"
    config_file.write_text(json.dumps({"transport": "streamable-http", "port": 3000}))
    result = runner.invoke(
        app, ["mcp", "validate-config", "--config", str(config_file)]
    )
    assert result.exit_code == 0
    assert "streamable-http" in result.output
    assert "3000" in result.output


def test_mcp_start_without_mcp_extra(runner):
    with patch("dell_ai.mcp.cli.importlib.util.find_spec") as mock_find_spec:
        mock_find_spec.return_value = None
        result = runner.invoke(app, ["mcp", "start"])
    assert result.exit_code == 1
    assert "mcp" in result.output.lower()


@pytest.mark.parametrize("command", ["start", "validate-config"])
@pytest.mark.parametrize(
    "case, message",
    [
        ("missing", "not found"),
        ("malformed", "line 1, column 2"),
        ("array", "must contain a JSON object"),
        ("null", "must contain a JSON object"),
        ("unreadable", "Permission denied"),
        ("encoding", "Cannot read MCP configuration"),
        ("invalid_value", "port:"),
    ],
)
def test_mcp_commands_reject_invalid_config(
    runner, tmp_path, monkeypatch, command, case, message
):
    pytest.importorskip("mcp")
    config_file = tmp_path / "mcp.json"
    contents = {
        "malformed": b"{",
        "array": b"[]",
        "null": b"null",
        "encoding": b"\xff",
        "invalid_value": b'{"port": "not-a-port"}',
        "unreadable": b"{}",
    }
    if case != "missing":
        config_file.write_bytes(contents[case])
    if case == "unreadable":
        monkeypatch.setattr(
            "dell_ai.mcp.config.open",
            Mock(side_effect=PermissionError("Permission denied")),
            raising=False,
        )

    with patch("dell_ai.mcp.server.create_server") as mock_create_server:
        result = runner.invoke(app, ["mcp", command, "--config", str(config_file)])

    assert result.exit_code == 1
    assert str(config_file) in result.output
    assert message in result.output
    mock_create_server.assert_not_called()


def test_config_error_is_written_to_stderr(tmp_path, capsys):
    config_file = tmp_path / "missing.json"

    with pytest.raises(typer.Exit) as exc:
        _read_config(config_file)

    assert exc.value.exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(config_file) in captured.err
    assert "not found" in captured.err


@pytest.mark.parametrize(
    "cli_args, expected_host, expected_port",
    [
        ([], "0.0.0.0", 3000),
        (["--host", "127.0.0.1", "--port", "3456"], "127.0.0.1", 3456),
    ],
)
def test_mcp_sse_uses_configured_address(
    runner, tmp_path, cli_args, expected_host, expected_port
):
    pytest.importorskip("mcp")
    config_file = tmp_path / "mcp.json"
    config_file.write_text(
        json.dumps({"transport": "sse", "host": "0.0.0.0", "port": 3000})
    )

    with patch("dell_ai.mcp.server.MCPServer.run") as mock_run:
        result = runner.invoke(
            app, ["mcp", "start", "--config", str(config_file), *cli_args]
        )

    assert result.exit_code == 0, result.output
    mock_run.assert_called_once_with(
        transport="sse", host=expected_host, port=expected_port
    )
