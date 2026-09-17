import asyncio
from typing import Optional

from dell_ai import deployments as deployments_module
from dell_ai.mcp.client import create_client
from dell_ai.mcp.config import MCPConfig
from dell_ai.mcp.tools import format_result
from dell_ai.system_utils.system_info import get_system_info


def register_resources(mcp, config: MCPConfig) -> None:
    if not config.capabilities.resources:
        return

    @mcp.resource(
        "deh://models/{+model_id}",
        name="model",
        mime_type="application/json",
    )
    async def model_resource(model_id: str) -> str:
        """Detailed information about a model."""
        result = await _call(config, lambda client: client.get_model(model_id))
        return format_result(result)

    @mcp.resource(
        "deh://platforms/{platform_id}",
        name="platform",
        mime_type="application/json",
    )
    async def platform_resource(platform_id: str) -> str:
        """Detailed information about a platform."""
        result = await _call(config, lambda client: client.get_platform(platform_id))
        return format_result(result)

    @mcp.resource(
        "deh://apps/{app_id}",
        name="app",
        mime_type="application/json",
    )
    async def app_resource(app_id: str) -> str:
        """Detailed information about an application."""
        result = await _call(config, lambda client: client.get_app(app_id))
        return format_result(result)

    @mcp.resource(
        "deh://deployments",
        name="deployments",
        mime_type="application/json",
    )
    async def deployments_resource() -> str:
        """Active deployments from the local registry."""
        result = await asyncio.to_thread(deployments_module.list_deployments)
        return format_result(result)

    @mcp.resource(
        "deh://system",
        name="system",
        mime_type="application/json",
    )
    async def system_resource() -> str:
        """Local CPU, memory, GPU, and OS information."""
        result = await asyncio.to_thread(get_system_info)
        if result is None:
            return "{}"
        return format_result(result)


async def _call(config: MCPConfig, fn) -> Optional[object]:
    return await asyncio.to_thread(_sync_call, config, fn)


def _sync_call(config: MCPConfig, fn) -> object:
    client = create_client(config)
    return fn(client)
