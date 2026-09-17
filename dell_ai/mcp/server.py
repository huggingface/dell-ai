from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server import MCPServer

from dell_ai import __version__
from dell_ai.mcp import deploy, prompts, resources, skills, tools
from dell_ai.mcp.config import MCPConfig, load_config
from dell_ai.mcp.types import AppContext

INSTRUCTIONS = (
    "This server provides tools to discover Dell Enterprise Hub "
    "models, platforms, applications, deployment snippets, and local "
    "deployment status. Use the 'Get deployment snippet' tool to generate a "
    "command or manifest, then review it before running any deployment. "
    "Deployment tools are only registered when allow_destructive is true."
)


def create_server(config: MCPConfig | None = None) -> MCPServer:
    config = config or load_config()
    mcp = MCPServer(
        name="dell-ai-mcp",
        title="Dell AI MCP Server",
        description="MCP server exposing Dell Enterprise Hub capabilities.",
        instructions=INSTRUCTIONS,
        version=__version__,
        lifespan=_make_lifespan(config),
        log_level=config.log_level,
    )
    if config.capabilities.tools:
        tools.register_catalog_tools(mcp, config)
        deploy.register_deployment_tools(mcp, config)
        skills.register_skills_tools(mcp, config)
    if config.capabilities.resources:
        resources.register_resources(mcp, config)
        skills.register_skills_resources(mcp, config)
    if config.capabilities.prompts:
        prompts.register_prompts(mcp, config)
    return mcp


def _make_lifespan(config: MCPConfig):
    @asynccontextmanager
    async def _lifespan(server: MCPServer) -> AsyncIterator[AppContext]:
        yield AppContext(config=config)

    return _lifespan
