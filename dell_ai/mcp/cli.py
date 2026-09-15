import importlib.util
from pathlib import Path
from typing import Optional

import typer

from dell_ai.mcp.config import MCPConfig, load_config

mcp_app = typer.Typer(help="MCP server commands")

TRANSPORTS = {"stdio", "streamable-http", "sse"}


@mcp_app.command("start")
def mcp_start(
    config: Optional[Path] = typer.Option(
        None, "--config", help="Path to MCP config file"
    ),
    transport: Optional[str] = typer.Option(
        None, "--transport", help="Transport: stdio, streamable-http, or sse"
    ),
    host: Optional[str] = typer.Option(None, "--host", help="HTTP host"),
    port: Optional[int] = typer.Option(None, "--port", help="HTTP port"),
    allow_destructive: bool = typer.Option(
        False, "--allow-destructive", help="Enable destructive tools"
    ),
) -> None:
    """Start the Dell AI MCP server."""
    if importlib.util.find_spec("mcp") is None:
        typer.echo(
            "The MCP server requires the 'mcp' extra. "
            "Install it with: uv pip install 'dell-ai[mcp]'",
            err=True,
        )
        raise typer.Exit(1)

    cfg = _load_cli_config(config, transport, host, port, allow_destructive)

    from dell_ai.mcp.server import create_server

    server = create_server(cfg)
    if cfg.transport == "stdio":
        server.run()
    elif cfg.transport == "streamable-http":
        server.run(
            transport="streamable-http",
            host=cfg.host,
            port=cfg.port,
            streamable_http_path=cfg.streamable_http_path,
            stateless_http=cfg.stateless_http,
            json_response=cfg.json_response,
        )
    elif cfg.transport == "sse":
        server.run(transport="sse", host=cfg.host, port=cfg.port)
    else:
        raise typer.BadParameter(f"Unsupported transport: {cfg.transport}") from None


@mcp_app.command("validate-config")
def mcp_validate_config(
    config: Optional[Path] = typer.Option(
        None, "--config", help="Path to MCP config file"
    ),
) -> None:
    """Validate an MCP configuration file."""
    cfg = load_config(config)
    typer.echo(cfg.model_dump_json(indent=2))


def _load_cli_config(
    config: Optional[Path],
    transport: Optional[str],
    host: Optional[str],
    port: Optional[int],
    allow_destructive: bool,
) -> MCPConfig:
    if transport and transport not in TRANSPORTS:
        raise typer.BadParameter(
            f"Invalid transport: {transport}. Valid: {', '.join(TRANSPORTS)}"
        )

    cfg = load_config(config)
    if transport:
        cfg.transport = transport
    if host:
        cfg.host = host
    if port:
        cfg.port = port
    cfg.allow_destructive = allow_destructive or cfg.allow_destructive
    return cfg
