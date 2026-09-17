import os
from pathlib import Path
from typing import Optional

from dell_ai import DellAIClient
from dell_ai.mcp.config import MCPConfig


def create_client(config: MCPConfig) -> DellAIClient:
    token = _resolve_token(config.hf_token_source)
    client = DellAIClient(token=token) if token else DellAIClient()
    if config.api_base_url:
        client.base_url = config.api_base_url
    return client


def _resolve_token(source: Optional[str]) -> Optional[str]:
    if not source:
        return None
    source = source.strip()
    if source.startswith("env:"):
        return os.environ.get(source[4:])
    if source.startswith("file:"):
        path = Path(source[5:])
        return path.read_text().strip() if path.exists() else None
    return os.environ.get(source)
