import json
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

LOCAL_MCP_FILENAME = ".dell-ai-mcp.json"


class MCPConfigError(ValueError):
    """An MCP configuration file could not be loaded or validated."""


class CapabilitiesConfig(BaseModel):
    tools: bool = True
    resources: bool = True
    prompts: bool = True


class MCPConfig(BaseModel):
    transport: Literal["stdio", "streamable-http", "sse"] = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    streamable_http_path: str = "/mcp"
    stateless_http: bool = True
    json_response: bool = False
    allow_destructive: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    hf_token_source: Optional[str] = None
    api_base_url: Optional[str] = None
    capabilities: CapabilitiesConfig = Field(default_factory=CapabilitiesConfig)

    model_config = {"extra": "ignore"}


def get_global_mcp_path() -> Path:
    return Path.home() / ".config" / "dell-ai" / "mcp.json"


def get_local_mcp_path() -> Path:
    return Path.cwd() / LOCAL_MCP_FILENAME


def _load_config_file(path: Path, *, missing_ok: bool = False) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as e:
        if missing_ok:
            return {}
        raise MCPConfigError(f"MCP configuration file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise MCPConfigError(
            f"Invalid JSON in MCP configuration {path}: "
            f"{e.msg} (line {e.lineno}, column {e.colno})"
        ) from e
    except (OSError, UnicodeError) as e:
        raise MCPConfigError(f"Cannot read MCP configuration {path}: {e}") from e
    if not isinstance(data, dict):
        raise MCPConfigError(f"MCP configuration {path} must contain a JSON object")
    return data


def load_config(config_path: Optional[Path] = None) -> MCPConfig:
    paths = (
        [config_path]
        if config_path is not None
        else [get_global_mcp_path(), get_local_mcp_path()]
    )
    data = {}
    for path in paths:
        data.update(_load_config_file(path, missing_ok=config_path is None))
    try:
        return MCPConfig(**data)
    except ValidationError as e:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in e.errors(include_input=False, include_url=False)
        )
        sources = ", ".join(str(path) for path in paths)
        raise MCPConfigError(f"Invalid MCP configuration ({sources}): {details}") from e
