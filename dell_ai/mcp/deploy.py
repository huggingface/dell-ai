import asyncio
import subprocess
from typing import Annotated, Any, Dict, List, Literal, Optional

from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from dell_ai import deployments as deployments_module
from dell_ai.mcp.config import MCPConfig
from dell_ai.mcp.tools import call_client, format_result
from dell_ai.mcp.types import AppContext

DEPLOY_ANNOTATIONS = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    open_world_hint=True,
    idempotent_hint=False,
)

UNDEPLOY_ANNOTATIONS = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    open_world_hint=True,
    idempotent_hint=True,
)


def register_deployment_tools(mcp, config: MCPConfig) -> None:
    if not config.capabilities.tools or not config.allow_destructive:
        return

    @mcp.tool(title="Deploy model", annotations=DEPLOY_ANNOTATIONS)
    async def deploy_model(
        ctx: Context[AppContext],
        model_id: Annotated[
            str,
            Field(description="Model ID in 'organization/model_name' format"),
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
        detach: Annotated[bool, Field(description="Run in detached mode")] = True,
        goodput: Annotated[
            Optional[str],
            Field(
                description="Goodput scenario, e.g. 'balanced' (omit when using num_gpus)"
            ),
        ] = None,
        local_dir: Annotated[
            Optional[str],
            Field(
                description="Local model weights directory (mutually exclusive with hf_cache_dir)"
            ),
        ] = None,
        hf_cache_dir: Annotated[
            Optional[str],
            Field(
                description="HuggingFace cache directory (mutually exclusive with local_dir)"
            ),
        ] = None,
        image_tag: Annotated[
            Optional[str], Field(description="Container image tag to pin")
        ] = None,
    ) -> str:
        """Deploy a model on the local node."""
        result = await call_client(
            ctx,
            lambda client: client.deploy_model(
                model_id=model_id,
                platform_id=platform_id,
                engine=engine,
                num_gpus=num_gpus,
                num_replicas=num_replicas,
                detach=detach,
                goodput=goodput,
                local_dir=local_dir,
                hf_cache_dir=hf_cache_dir,
                image_tag=image_tag,
            ),
        )
        return format_result(result)

    @mcp.tool(title="Deploy app", annotations=DEPLOY_ANNOTATIONS)
    async def deploy_app(
        ctx: Context[AppContext],
        app_id: Annotated[str, Field(description="Application ID")],
        config: Annotated[
            Optional[List[Dict[str, Any]]],
            Field(
                description="Application configuration as a list of objects with helmPath, type, and value"
            ),
        ] = None,
        detach: Annotated[bool, Field(description="Run in detached mode")] = True,
    ) -> str:
        """Deploy an application on the local node."""
        result = await call_client(
            ctx,
            lambda client: client.deploy_app(app_id, config or [], detach=detach),
        )
        return format_result(result)

    @mcp.tool(title="Undeploy", annotations=UNDEPLOY_ANNOTATIONS)
    async def undeploy(
        ctx: Context[AppContext],
        deployment_id: Annotated[
            str,
            Field(description="Deployment ID as shown in list_deployments"),
        ],
    ) -> str:
        """Stop and remove a deployment by ID."""
        result = await asyncio.to_thread(_undeploy, deployment_id)
        return format_result(result)


def _undeploy(deployment_id: str) -> Dict[str, Any]:
    deployment = deployments_module.get_deployment(deployment_id)
    if not deployment:
        return {
            "success": False,
            "error": f"No active deployment found: {deployment_id}",
        }

    engine = deployment.get("engine")
    messages = []
    success = True

    if engine == "docker":
        container_id = deployment.get("container_id")
        if container_id:
            try:
                subprocess.run(
                    ["docker", "stop", container_id],
                    capture_output=True,
                    check=True,
                    text=True,
                )
                messages.append(f"Stopped Docker container: {container_id}")
            except subprocess.CalledProcessError as e:
                success = False
                messages.append(f"Failed to stop Docker container: {e.stderr}")
    elif engine == "kubernetes":
        k8s_deployment = deployment.get("k8s_deployment")
        if k8s_deployment:
            try:
                subprocess.run(
                    ["kubectl", "delete", "deployment", k8s_deployment],
                    capture_output=True,
                    check=True,
                    text=True,
                )
                messages.append(f"Deleted Kubernetes deployment: {k8s_deployment}")
            except subprocess.CalledProcessError as e:
                success = False
                messages.append(f"Failed to delete Kubernetes deployment: {e.stderr}")
    elif engine == "helm":
        messages.append(
            "Helm releases must be removed manually with `helm uninstall <release>`."
        )
    else:
        messages.append(f"Unknown engine: {engine}")

    deleted = deployments_module.delete_deployment(deployment_id)
    if deleted:
        messages.append(f"Removed deployment entry: {deployment_id}")

    return {"success": success, "messages": messages}
