from dataclasses import dataclass

from dell_ai.mcp.config import MCPConfig


@dataclass
class AppContext:
    config: MCPConfig
