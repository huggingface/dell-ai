import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from dell_ai.cli.main import app


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
