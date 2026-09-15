import asyncio
import json
from typing import Annotated, Any, Dict, List, Literal, Optional

from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from dell_ai import deployments as deployments_module
from dell_ai.mcp.client import create_client
from dell_ai.mcp.config import MCPConfig
from dell_ai.mcp.types import AppContext
from dell_ai.system_utils.system_info import get_system_info

READ_ONLY_ANNOTATIONS = ToolAnnotations(read_only_hint=True, open_world_hint=False)


def register_catalog_tools(mcp, config: MCPConfig) -> None:
    if not config.capabilities.tools:
        return

    @mcp.tool(title="List models", annotations=READ_ONLY_ANNOTATIONS)
    async def list_models(
        ctx: Context[AppContext],
        query: Annotated[
            Optional[str],
            Field(description="Search query matching model name or description"),
        ] = None,
        multimodal: Annotated[
            Optional[bool],
            Field(
                description="Filter for multimodal (True) or text-only (False) models"
            ),
        ] = None,
        min_size: Annotated[
            Optional[float],
            Field(description="Minimum model size in millions of parameters"),
        ] = None,
        max_size: Annotated[
            Optional[float],
            Field(description="Maximum model size in millions of parameters"),
        ] = None,
        license_filter: Annotated[
            Optional[str], Field(description="License substring filter")
        ] = None,
        platform_id: Annotated[
            Optional[str], Field(description="Only models compatible with this SKU")
        ] = None,
    ) -> str:
        """List available model IDs from the Dell Enterprise Hub."""
        result = await call_client(
            ctx,
            lambda client: client.list_models(
                query=query,
                multimodal=multimodal,
                min_size=min_size,
                max_size=max_size,
                license_filter=license_filter,
                platform_id=platform_id,
            ),
        )
        return format_result(result)

    @mcp.tool(title="Search models", annotations=READ_ONLY_ANNOTATIONS)
    async def search_models(
        ctx: Context[AppContext],
        query: Annotated[
            Optional[str],
            Field(description="Search query matching model name or description"),
        ] = None,
        multimodal: Annotated[
            Optional[bool],
            Field(
                description="Filter for multimodal (True) or text-only (False) models"
            ),
        ] = None,
        min_size: Annotated[
            Optional[float],
            Field(description="Minimum model size in millions of parameters"),
        ] = None,
        max_size: Annotated[
            Optional[float],
            Field(description="Maximum model size in millions of parameters"),
        ] = None,
        license_filter: Annotated[
            Optional[str], Field(description="License substring filter")
        ] = None,
        platform_id: Annotated[
            Optional[str], Field(description="Only models compatible with this SKU")
        ] = None,
    ) -> str:
        """Search and return full model objects from the Dell Enterprise Hub."""
        result = await call_client(
            ctx,
            lambda client: client.search_models(
                query=query,
                multimodal=multimodal,
                min_size=min_size,
                max_size=max_size,
                license_filter=license_filter,
                platform_id=platform_id,
            ),
        )
        return format_result(result)

    @mcp.tool(title="Get model", annotations=READ_ONLY_ANNOTATIONS)
    async def get_model(
        ctx: Context[AppContext],
        model_id: Annotated[
            str,
            Field(description="Model ID in the format 'organization/model_name'"),
        ],
    ) -> str:
        """Get detailed information about a specific model."""
        result = await call_client(ctx, lambda client: client.get_model(model_id))
        return format_result(result)

    @mcp.tool(title="Get compatible platforms", annotations=READ_ONLY_ANNOTATIONS)
    async def get_compatible_platforms(
        ctx: Context[AppContext],
        model_id: Annotated[
            str, Field(description="Model ID in 'organization/model_name' format")
        ],
    ) -> str:
        """List platforms and GPU configurations compatible with a model."""
        result = await call_client(
            ctx, lambda client: client.get_compatible_platforms(model_id)
        )
        return format_result(result)

    @mcp.tool(title="List platforms", annotations=READ_ONLY_ANNOTATIONS)
    async def list_platforms(ctx: Context[AppContext]) -> str:
        """List available Dell platform SKU IDs."""
        result = await call_client(ctx, lambda client: client.list_platforms())
        return format_result(result)

    @mcp.tool(title="Get platform", annotations=READ_ONLY_ANNOTATIONS)
    async def get_platform(
        ctx: Context[AppContext],
        platform_id: Annotated[str, Field(description="Platform SKU ID")],
    ) -> str:
        """Get detailed information about a specific platform."""
        result = await call_client(ctx, lambda client: client.get_platform(platform_id))
        return format_result(result)

    @mcp.tool(title="Get platform system info", annotations=READ_ONLY_ANNOTATIONS)
    async def get_platform_system_info(
        ctx: Context[AppContext],
        platform_id: Annotated[str, Field(description="Platform SKU ID")],
    ) -> str:
        """Get tested system information for a platform."""
        result = await call_client(
            ctx, lambda client: client.get_platform_system_info(platform_id)
        )
        return format_result(result)

    @mcp.tool(title="Check model access", annotations=READ_ONLY_ANNOTATIONS)
    async def check_model_access(
        ctx: Context[AppContext],
        model_id: Annotated[
            str, Field(description="Model ID in 'organization/model_name' format")
        ],
    ) -> str:
        """Check whether the authenticated user can access a gated model."""
        result = await call_client(
            ctx, lambda client: client.check_model_access(model_id)
        )
        return format_result(result)

    @mcp.tool(title="Get deployment snippet", annotations=READ_ONLY_ANNOTATIONS)
    async def get_deployment_snippet(
        ctx: Context[AppContext],
        model_id: Annotated[
            str, Field(description="Model ID in 'organization/model_name' format")
        ],
        platform_id: Annotated[str, Field(description="Platform SKU ID")],
        engine: Annotated[
            Literal["docker", "kubernetes"],
            Field(description="Deployment engine"),
        ],
        num_gpus: Annotated[
            Optional[int],
            Field(description="Number of GPUs to use (omit when using goodput)"),
        ] = None,
        num_replicas: Annotated[int, Field(description="Number of replicas")] = 1,
        goodput: Annotated[
            Optional[str],
            Field(
                description="Goodput scenario, e.g. 'balanced' (omit when using num_gpus)"
            ),
        ] = None,
        image_tag: Annotated[
            Optional[str], Field(description="Container image tag to pin")
        ] = None,
    ) -> str:
        """Generate a Docker or Kubernetes deployment snippet for a model.

        Replace $$_TOKEN_$$ with your Hugging Face token before manual execution,
        or use deploy_model when enabled to handle token substitution automatically.
        """
        result = await call_client(
            ctx,
            lambda client: client.get_deployment_snippet(
                model_id=model_id,
                platform_id=platform_id,
                engine=engine,
                num_gpus=num_gpus,
                num_replicas=num_replicas,
                goodput=goodput,
                image_tag=image_tag,
            ),
        )
        return format_result(result)

    @mcp.tool(title="Get container tags", annotations=READ_ONLY_ANNOTATIONS)
    async def get_container_tags(
        ctx: Context[AppContext],
        model_id: Annotated[
            str, Field(description="Model ID in 'organization/model_name' format")
        ],
        platform_id: Annotated[str, Field(description="Platform SKU ID")],
    ) -> str:
        """List container image tags available for a model and platform."""
        result = await call_client(
            ctx, lambda client: client.get_container_tags(model_id, platform_id)
        )
        return format_result(result)

    @mcp.tool(title="Get goodput scenarios", annotations=READ_ONLY_ANNOTATIONS)
    async def get_goodput_scenarios(ctx: Context[AppContext]) -> str:
        """Get goodput scenario definitions and SLO targets per platform."""
        result = await call_client(ctx, lambda client: client.get_goodput_scenarios())
        return format_result(result)

    @mcp.tool(title="List apps", annotations=READ_ONLY_ANNOTATIONS)
    async def list_apps(ctx: Context[AppContext]) -> str:
        """List available applications in the Dell app catalog."""
        result = await call_client(ctx, lambda client: client.list_apps())
        return format_result(result)

    @mcp.tool(title="Get app", annotations=READ_ONLY_ANNOTATIONS)
    async def get_app(
        ctx: Context[AppContext],
        app_id: Annotated[str, Field(description="Application ID")],
    ) -> str:
        """Get detailed information about an application."""
        result = await call_client(ctx, lambda client: client.get_app(app_id))
        return format_result(result)

    @mcp.tool(title="Get app snippet", annotations=READ_ONLY_ANNOTATIONS)
    async def get_app_snippet(
        ctx: Context[AppContext],
        app_id: Annotated[str, Field(description="Application ID")],
        config: Annotated[
            Optional[List[Dict[str, Any]]],
            Field(
                description="Application configuration as a list of objects with helmPath, type, and value"
            ),
        ] = None,
    ) -> str:
        """Generate a Helm deployment snippet for an application."""
        result = await call_client(
            ctx, lambda client: client.get_app_snippet(app_id, config or [])
        )
        return format_result(result)

    @mcp.tool(title="List deployments", annotations=READ_ONLY_ANNOTATIONS)
    async def list_deployments(ctx: Context[AppContext]) -> str:
        """List active deployments from the local deployment registry."""
        result = await asyncio.to_thread(deployments_module.list_deployments)
        return format_result(result)

    @mcp.tool(title="Describe system", annotations=READ_ONLY_ANNOTATIONS)
    async def describe_system(ctx: Context[AppContext]) -> str:
        """Describe the local system's CPU, memory, GPU, and OS information."""
        result = await asyncio.to_thread(get_system_info)
        if result is None:
            return "Unable to retrieve system information."
        return format_result(result)


async def call_client(ctx: Context[AppContext], fn) -> Any:
    config = ctx.request_context.lifespan_context.config
    return await asyncio.to_thread(sync_call, config, fn)


def sync_call(config: MCPConfig, fn) -> Any:
    client = create_client(config)
    return fn(client)


def format_result(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, BaseModel):
        data = value.model_dump()
    elif isinstance(value, list):
        data = [item_data(item) for item in value]
    else:
        data = value
    return json.dumps(data, indent=2, default=str)


def item_data(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    return value
