"""Command-line interface for Dell AI."""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

import requests
import rich
import typer
from rich.table import Table

from dell_ai import __version__, auth, env
from dell_ai.cli.utils import (
    GLOBAL_AGENT_SKILLS_DIRS,
    LOCAL_AGENT_SKILLS_DIRS,
    get_client,
    get_skills,
    print_apps_table,
    print_compatible_platforms_table,
    print_container_tags_table,
    print_error,
    print_goodput_scenarios_table,
    print_json,
    print_models_table,
    print_platforms_table,
    print_search_results_table,
    print_skills_table,
    print_slos_table,
    print_warning,
    stdout_console,
)
from dell_ai.exceptions import (
    AuthenticationError,
    GatedRepoAccessError,
    ResourceNotFoundError,
    ValidationError,
)
from dell_ai.mcp.cli import mcp_app
from dell_ai.system_utils.system_info import SystemInfo, get_system_info

app = typer.Typer(
    name="dell-ai",
    help="CLI for interacting with the Dell Enterprise Hub (DEH)",
    add_completion=False,
)

models_app = typer.Typer(help="Model commands")
platforms_app = typer.Typer(help="Platform commands")
apps_app = typer.Typer(help="Application commands")
utils_app = typer.Typer(help="Utilities commands")
skills_app = typer.Typer(help="Skills commands")
env_app = typer.Typer(help="Environment variable commands")

app.add_typer(models_app, name="models")
app.add_typer(platforms_app, name="platforms")
app.add_typer(apps_app, name="apps")
app.add_typer(utils_app, name="utils")
app.add_typer(skills_app, name="skills")
app.add_typer(env_app, name="env")
app.add_typer(mcp_app, name="mcp")


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        typer.echo(f"dell-ai version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        help="Show the application version and exit.",
    ),
):
    """
    Dell AI CLI - Interact with the Dell Enterprise Hub (DEH)
    """
    env.load_all_env_to_os()


@app.command("login")
def auth_login(
    token: Optional[str] = typer.Option(
        None,
        "--token",
        help="Hugging Face API token. If not provided, you will be prompted to enter it.",
    ),
) -> None:
    """
    Log in to Dell AI using a Hugging Face token.

    If no token is provided, you will be prompted to enter it. You can get a token from:
    https://huggingface.co/settings/tokens
    """
    if not token:
        typer.echo(
            "You can get a token from https://huggingface.co/settings/tokens\n"
            "The token will be stored securely in your Hugging Face token cache."
        )
        token = typer.prompt("Enter your Hugging Face token", hide_input=True)

    try:
        auth.login(token)
        user_info = auth.get_user_info(token)
        typer.echo(f"Successfully logged in as {user_info.get('name', 'Unknown')}")
    except AuthenticationError as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command("logout")
def auth_logout() -> None:
    """
    Log out from Dell AI and remove the stored token.
    """
    if not auth.is_logged_in():
        typer.echo("You are not currently logged in.")
        return

    if typer.confirm("Are you sure you want to log out?"):
        try:
            auth.logout()
            typer.echo("Successfully logged out")
        except Exception as e:
            typer.echo(f"Error during logout: {str(e)}", err=True)
            raise typer.Exit(code=1)
    else:
        typer.echo("Logout cancelled")


@app.command("whoami")
def auth_status() -> None:
    """
    Show the current authentication status and user information.
    """
    if not auth.is_logged_in():
        typer.echo("Status: Not logged in")
        typer.echo("To log in, run: dell-ai login")
        return

    try:
        user_info = auth.get_user_info()
        typer.echo("Status: Logged in")
        typer.echo(f"User: {user_info.get('name', 'Unknown')}")
        typer.echo(f"Email: {user_info.get('email', 'Not available')}")
        typer.echo(
            f"Organizations: {', '.join([org.get('name', 'Unknown') for org in user_info.get('orgs', [])])}"
        )
    except AuthenticationError as e:
        typer.echo(f"Status: Error ({str(e)})")
        typer.echo("Please try logging in again: dell-ai login")
        raise typer.Exit(code=1)


@app.command("status")
def dellai_status(
    clean: bool = typer.Option(
        False,
        "--clean",
        help="Remove exited Docker containers and stopped K8s deployments.",
    ),
) -> None:
    """
    Check the status of deployed model endpoints, checkpoints, and active deployments.
    """

    # Initialize Table for Deployed Models/Apps
    deployments_table = Table(title="Active Deployments")
    deployments_table.add_column("Deployment ID", style="cyan")
    deployments_table.add_column("Endpoint", style="blue")
    deployments_table.add_column("Status", style="bold")
    deployments_table.add_column("Response Time", style="green")
    deployments_table.add_column("Engine", style="magenta")

    deployments_found = False

    # 1. Scan deployments registry
    from dell_ai import deployments as deployments_module

    all_deployments = deployments_module.list_deployments()
    for deployment_id, deployment_meta in sorted(all_deployments.items()):
        deployments_found = True
        endpoint = deployment_meta.get("endpoint", "N/A")
        engine = deployment_meta.get("engine", "unknown")

        if endpoint and endpoint.startswith("http"):
            start_time = time.time()
            try:
                # Try getting health or main url
                url = endpoint.rstrip("/")
                response = None
                for health_path in ["/health", "/v1/models", ""]:
                    try:
                        response = requests.get(f"{url}{health_path}", timeout=2.0)
                        if response.status_code == 200:
                            break
                    except requests.RequestException:
                        pass

                if response is not None and response.status_code == 200:
                    latency = f"{(time.time() - start_time) * 1000:.0f}ms"
                    deployments_table.add_row(
                        deployment_id,
                        endpoint,
                        "[green]Online[/green]",
                        latency,
                        engine,
                    )
                else:
                    status_code = (
                        response.status_code if response is not None else "No Response"
                    )
                    deployments_table.add_row(
                        deployment_id,
                        endpoint,
                        f"[red]Offline ({status_code})[/red]",
                        "N/A",
                        engine,
                    )
            except Exception as e:
                deployments_table.add_row(
                    deployment_id,
                    endpoint,
                    f"[red]Error ({str(e)})[/red]",
                    "N/A",
                    engine,
                )
        else:
            deployments_table.add_row(
                deployment_id, endpoint, "[yellow]No Endpoint[/yellow]", "N/A", engine
            )

    if deployments_found:
        stdout_console.print("\n")
        stdout_console.print(deployments_table)
        typer.echo("")
    else:
        typer.echo("ℹ️ No active deployments found.")

    # 2. Check for checkpoints
    checkpoint_table = Table(title="Model Checkpoints")
    checkpoint_table.add_column("Environment Variable", style="cyan")
    checkpoint_table.add_column("Path", style="blue")
    checkpoint_table.add_column("Exists", style="bold")
    checkpoint_table.add_column("Type", style="magenta")
    checkpoint_table.add_column("Size", style="green")

    checkpoints_found = False
    for k, v in sorted(os.environ.items()):
        if k.startswith("DELL_AI_") and k.endswith("_CHECKPOINT"):
            checkpoints_found = True
            path = Path(v)
            if path.exists():
                is_dir = "Directory" if path.is_dir() else "File"
                # Compute size — use du for directories to avoid blocking on large checkpoints
                try:
                    if path.is_file():
                        size_bytes = path.stat().st_size
                        for unit in ["B", "KB", "MB", "GB", "TB"]:
                            if size_bytes < 1024.0:
                                size_str = f"{size_bytes:.1f} {unit}"
                                break
                            size_bytes /= 1024.0
                        else:
                            size_str = f"{size_bytes:.1f} PB"
                    elif shutil.which("du"):
                        du_proc = subprocess.run(
                            ["du", "-sh", str(path)],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        size_str = (
                            du_proc.stdout.split("\t")[0].strip()
                            if du_proc.returncode == 0
                            else "Unknown"
                        )
                    else:
                        size_str = "Unknown"
                except Exception:
                    size_str = "Unknown"

                checkpoint_table.add_row(k, v, "[green]Yes[/green]", is_dir, size_str)
            else:
                checkpoint_table.add_row(k, v, "[red]No[/red]", "N/A", "N/A")

    if checkpoints_found:
        stdout_console.print(checkpoint_table)
        typer.echo("")
    else:
        typer.echo("ℹ️ No active checkpoints found in environment variables.")

    # 3. Check for running container/kubernetes deployments
    deployments_table = Table(title="Active Docker/K8s")
    deployments_table.add_column("Engine", style="magenta")
    deployments_table.add_column("ID / Name", style="cyan")
    deployments_table.add_column("Image / Reference", style="blue")
    deployments_table.add_column("Status", style="bold")
    deployments_table.add_column("Port Mapping", style="green")

    deployments_found = False

    # A. Check Docker
    if shutil.which("docker"):
        try:
            # List all containers (running or stopped) for huggingface/dell
            proc = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--format",
                    "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in proc.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 4:
                    c_id, c_name, c_image, c_status = (
                        parts[0],
                        parts[1],
                        parts[2],
                        parts[3],
                    )
                    c_ports = parts[4] if len(parts) > 4 else "N/A"

                    # Filter for huggingface / dell images or last deployed container
                    is_last_deployed = c_id == os.environ.get(
                        "DELL_AI_LAST_DEPLOYED_CONTAINER"
                    ) or c_name == os.environ.get("DELL_AI_LAST_DEPLOYED_CONTAINER")
                    is_matching_image = (
                        "huggingface.co" in c_image
                        or "dell.huggingface" in c_image
                        or "enterprise-dell" in c_image
                    )

                    if is_last_deployed or is_matching_image:
                        deployments_found = True
                        is_running = "Up" in c_status
                        if clean and not is_running:
                            try:
                                subprocess.run(
                                    ["docker", "rm", c_id],
                                    capture_output=True,
                                    timeout=10,
                                    check=True,
                                )
                                c_status = "Removed"
                            except Exception:
                                pass
                        status_color = (
                            "green"
                            if is_running
                            else ("yellow" if c_status == "Removed" else "red")
                        )
                        deployments_table.add_row(
                            "Docker",
                            c_name,
                            c_image,
                            f"[{status_color}]{c_status}[/{status_color}]",
                            c_ports,
                        )
        except Exception:
            pass

    # B. Check Kubernetes (kubectl)
    if shutil.which("kubectl"):
        try:
            # Check for deployments
            proc = subprocess.run(
                ["kubectl", "get", "deployments", "-o", "json"],
                capture_output=True,
                text=True,
                check=True,
            )
            if proc.stdout:
                data = json.loads(proc.stdout)
                for item in data.get("items", []):
                    name = item.get("metadata", {}).get("name")
                    namespace = item.get("metadata", {}).get("namespace", "default")

                    # Check replicas / status
                    status = item.get("status", {})
                    ready = status.get("readyReplicas", 0)
                    desired = item.get("spec", {}).get("replicas", 1)

                    # Check containers
                    containers = (
                        item.get("spec", {})
                        .get("template", {})
                        .get("spec", {})
                        .get("containers", [])
                    )
                    images = [c.get("image", "") for c in containers]

                    is_last_deployed = name == os.environ.get(
                        "DELL_AI_LAST_DEPLOYED_K8S_DEPLOYMENT"
                    )
                    is_matching_image = any(
                        "huggingface.co" in img
                        or "dell.huggingface" in img
                        or "enterprise-dell" in img
                        for img in images
                    )

                    if is_last_deployed or is_matching_image:
                        deployments_found = True
                        status_str = f"{ready}/{desired} Ready"
                        status_color = (
                            "green"
                            if ready == desired
                            else "yellow"
                            if ready > 0
                            else "red"
                        )

                        if clean and ready == 0:
                            try:
                                subprocess.run(
                                    [
                                        "kubectl",
                                        "delete",
                                        "deployment",
                                        name,
                                        "-n",
                                        namespace,
                                    ],
                                    capture_output=True,
                                    timeout=30,
                                    check=True,
                                )
                                deployments_module.delete_deployment(
                                    name, is_global=False
                                )
                                deployments_module.delete_deployment(
                                    name, is_global=True
                                )
                                status_str = "Removed"
                                status_color = "yellow"
                            except Exception:
                                pass

                        deployments_table.add_row(
                            "Kubernetes",
                            f"{namespace}/{name}",
                            ", ".join(images),
                            f"[{status_color}]{status_str}[/{status_color}]",
                            "N/A",
                        )
        except Exception:
            pass

    if deployments_found:
        stdout_console.print(deployments_table)
    else:
        typer.echo("ℹ️ No active Docker/K8s found.")


@models_app.command("list")
def models_list(
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: 'json' for raw JSON, 'table' for a formatted table",
    ),
) -> None:
    """
    List all available models from the Dell Enterprise Hub.

    Returns model IDs in the format "organization/model_name".
    Use --format table for a human-readable table view.
    """
    try:
        client = get_client()
        results = client.search_models()
        if output_format == "table":
            print_models_table(results)
        else:
            model_ids = [
                f"{m.repo_name} (deprecated)"
                if m.status == "deprecated"
                else m.repo_name
                for m in results
            ]
            print_json(model_ids)
    except Exception as e:
        print_error(f"Failed to list models: {str(e)}")


@models_app.command("show")
def models_show(model_id: str) -> None:
    """
    Show detailed information about a specific model.

    Args:
        model_id: The model ID in the format "organization/model_name"
    """
    try:
        client = get_client()
        model_info = client.get_model(model_id)
        print_json(model_info)
    except ResourceNotFoundError:
        print_error(f"Model not found: {model_id}")
    except Exception as e:
        print_error(f"Failed to get model information: {str(e)}")


@models_app.command("search")
def models_search(
    query: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="Search query to match against model name or description",
    ),
    multimodal: Optional[bool] = typer.Option(
        None,
        "--multimodal",
        help="Filter for multimodal (True) or text-only (False) models",
    ),
    min_size: Optional[float] = typer.Option(
        None,
        "--min-size",
        help="Minimum model size in millions of parameters",
    ),
    max_size: Optional[float] = typer.Option(
        None,
        "--max-size",
        help="Maximum model size in millions of parameters",
    ),
    license_filter: Optional[str] = typer.Option(
        None,
        "--license",
        "-l",
        help="Filter by license type (case-insensitive substring match)",
    ),
    platform_id: Optional[str] = typer.Option(
        None,
        "--platform-id",
        "-p",
        help="Filter models that support a specific platform SKU",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: 'json' for raw JSON, 'table' for a formatted table",
    ),
    detail: bool = typer.Option(
        False,
        "--detail",
        "-d",
        help="Show full model details instead of only model IDs",
    ),
) -> None:
    """
    Search and filter available models from the Dell Enterprise Hub.

    Filters can be combined. For example, to find multimodal models larger than 10B params:
        dell-ai models search --multimodal --min-size 10000

    To find models compatible with a specific platform:
        dell-ai models search --platform-id xe9680-nvidia-h100
    """
    try:
        client = get_client()
        filters = {
            "query": query,
            "multimodal": multimodal,
            "min_size": min_size,
            "max_size": max_size,
            "license_filter": license_filter,
            "platform_id": platform_id,
        }
        results = client.search_models(**filters)
        if detail:
            if output_format == "table":
                print_search_results_table(results)
            else:
                print_json([model.model_dump() for model in results])
        else:
            if output_format == "table":
                print_models_table(results)
            else:
                model_ids = [
                    f"{m.repo_name} (deprecated)"
                    if m.status == "deprecated"
                    else m.repo_name
                    for m in results
                ]
                print_json(model_ids)
    except Exception as e:
        print_error(f"Failed to search models: {str(e)}")


@models_app.command("compatible-platforms")
def models_compatible_platforms(
    model_id: str = typer.Argument(
        ..., help="Model ID in the format 'organization/model_name'"
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: 'json' for raw JSON, 'table' for a formatted table",
    ),
) -> None:
    """
    Find all platforms compatible with a given model.

    Shows each compatible platform along with its supported GPU configurations,
    making it easy to plan deployments without manually checking each platform.

    Example:
        dell-ai models compatible-platforms google/gemma-3-27b-it
    """
    try:
        client = get_client()
        results = client.get_compatible_platforms(model_id)
        if output_format == "table":
            print_compatible_platforms_table(results)
        else:
            print_json([r.model_dump() for r in results])
    except (ValidationError, ResourceNotFoundError) as e:
        print_error(str(e))
    except Exception as e:
        print_error(f"Failed to get compatible platforms: {str(e)}")


@models_app.command("list-tags")
def models_list_tags(
    model_id: str = typer.Option(
        ...,
        "--model-id",
        "-m",
        help="Model ID in the format 'organization/model_name'",
    ),
    platform_id: str = typer.Option(
        ...,
        "--platform-id",
        "-p",
        help="Platform SKU ID",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: 'json' for raw JSON, 'table' for a formatted table",
    ),
) -> None:
    """
    List the container image tags available for a model on a given platform.

    These are the values accepted by the '--image-tag' option of
    'models get-snippet' and 'models deploy'. Tags are published per accelerator
    vendor, so the list is resolved from the platform's vendor.

    Example:
        dell-ai models list-tags -m google/gemma-3-27b-it -p xe9680-nvidia-h100
    """
    try:
        client = get_client()
        tags = client.get_container_tags(model_id, platform_id)
        if not tags:
            print_warning(
                f"No container tags are published for {model_id} "
                f"on platform {platform_id}."
            )
            return
        if output_format == "table":
            print_container_tags_table(tags)
        else:
            print_json([tag.model_dump() for tag in tags])
    except (ValidationError, ResourceNotFoundError) as e:
        print_error(str(e))
    except Exception as e:
        print_error(f"Failed to list container tags: {str(e)}")


@models_app.command("check-access")
def models_check_access(model_id: str) -> None:
    """
    Check if you have access to a specific model repository.

    This is particularly useful for gated repositories that require specific permissions.
    If you don't have access to a gated repository, you'll need to request access on the
    Hugging Face Hub before you can use it.

    Args:
        model_id: The model ID in the format "organization/model_name"
    """
    try:
        client = get_client()
        # If check_model_access completes without raising an exception, we have access
        client.check_model_access(model_id)
        typer.echo(f"✅ You have access to model: {model_id}")
    except (GatedRepoAccessError, ResourceNotFoundError, AuthenticationError) as e:
        # Handle expected errors with proper error messages
        print_error(str(e))
    except Exception as e:
        # Unexpected errors get a generic message
        print_error(f"Failed to check model access: {str(e)}")


@models_app.command("get-snippet")
def models_get_snippet(
    model_id: str = typer.Option(
        ...,
        "--model-id",
        "-m",
        help="Model ID in the format 'organization/model_name'",
    ),
    platform_id: str = typer.Option(
        ...,
        "--platform-id",
        "-p",
        help="Platform SKU ID",
    ),
    engine: str = typer.Option(
        "docker",
        "--engine",
        "-e",
        help="Deployment engine (docker or kubernetes)",
    ),
    gpus: Optional[int] = typer.Option(
        None,
        "--gpus",
        "-g",
        help="Number of GPUs to use. Required unless --goodput is set; cannot be combined with it.",
        min=1,
    ),
    replicas: int = typer.Option(
        1,
        "--replicas",
        "-r",
        help="Number of replicas to deploy",
        min=1,
    ),
    goodput: Optional[str] = typer.Option(
        None,
        "--goodput",
        help=(
            "Generate a snippet optimized for a goodput scenario "
            "(e.g. balanced, long-context, high-concurrency, performance). "
            "Cannot be combined with --gpus."
        ),
    ),
    image_tag: Optional[str] = typer.Option(
        None,
        "--image-tag",
        help=(
            "Pin a specific container image tag in the snippet (e.g. vllm-v0.11.2). "
            "Must be one of the tags available for the model/platform "
            "(see 'dell-ai models list-tags'). Defaults to the untagged image."
        ),
    ),
    local_dir: Optional[str] = typer.Option(
        None,
        "--local-dir",
        help=(
            "Path to a local directory containing model weights. "
            "Mounts the folder into the container and sets MODEL_ID to the mount path. "
            "Only supported with --engine docker. Mutually exclusive with --hf-cache-dir."
        ),
    ),
    hf_cache_dir: Optional[str] = typer.Option(
        None,
        "--hf-cache-dir",
        help=(
            "Path to a HuggingFace cache directory (same layout as "
            "'huggingface-cli download --cache-dir'). "
            "Mounts the folder as the container's HF cache and injects HF_HUB_CACHE. "
            "Only supported with --engine docker. Mutually exclusive with --local-dir."
        ),
    ),
) -> None:
    """
    Get a deployment snippet for running a model on a specific platform.

    This command generates a deployment snippet (Docker command or Kubernetes manifest)
    for running the specified model on the given platform with the provided configuration.

    Provide either --gpus for manual sizing or --goodput <scenario> to let the
    server size the deployment for you. Exactly one of the two is required.

    Use --local-dir or --hf-cache-dir to serve weights from a local folder instead
    of downloading them at container startup (Docker only).

    Args:
        model_id: Model ID in the format 'organization/model_name'
        platform_id: Platform SKU ID
        engine: Deployment engine (docker or kubernetes)
        gpus: Number of GPUs to use (manual sizing; required unless --goodput)
        replicas: Number of replicas to deploy
        goodput: Goodput scenario to optimize the snippet for
        image_tag: Container image tag to pin in the snippet
        local_dir: Local directory with model weights (Docker only)
        hf_cache_dir: HuggingFace cache directory (Docker only)

    Examples:
        dell-ai models get-snippet -m google/gemma-3-27b-it -p xe9680-nvidia-h100 -e docker --gpus 8 --replicas 1
        dell-ai models get-snippet -m google/gemma-3-27b-it -p xe9680-nvidia-h100 --goodput balanced
        dell-ai models get-snippet -m google/gemma-3-27b-it -p xe9680-nvidia-h100 --gpus 8 --image-tag vllm-v0.11.2
        dell-ai models get-snippet -m google/gemma-3-27b-it -p xe9680-nvidia-h100 --gpus 8 --local-dir /data/weights
        dell-ai models get-snippet -m google/gemma-3-27b-it -p xe9680-nvidia-h100 --gpus 8 --hf-cache-dir ~/.cache/huggingface
    """
    if goodput is not None and gpus is not None:
        print_error("--gpus cannot be combined with --goodput")

    # One sizing mode is required: manual (--gpus) or server-chosen (--goodput).
    if goodput is None and gpus is None:
        print_error("Either --gpus or --goodput must be provided")

    if local_dir is not None and hf_cache_dir is not None:
        print_error("--local-dir and --hf-cache-dir are mutually exclusive")
        raise typer.Exit(code=1)

    if local_dir is not None or hf_cache_dir is not None:
        if engine != "docker":
            print_error(
                "--local-dir and --hf-cache-dir are only supported with --engine docker"
            )
            raise typer.Exit(code=1)

    if local_dir is not None and not Path(local_dir).is_dir():
        print_error(
            f"--local-dir path does not exist or is not a directory: {local_dir}"
        )
        raise typer.Exit(code=1)

    if hf_cache_dir is not None and not Path(hf_cache_dir).is_dir():
        print_error(
            f"--hf-cache-dir path does not exist or is not a directory: {hf_cache_dir}"
        )
        raise typer.Exit(code=1)

    try:
        from dell_ai import resources

        # Create client and get deployment snippet
        client = get_client()
        snippet = client.get_deployment_snippet(
            model_id=model_id,
            platform_id=platform_id,
            engine=engine,
            num_gpus=gpus,
            num_replicas=replicas,
            goodput=goodput,
            image_tag=image_tag,
        )
        if local_dir is not None:
            snippet = resources.inject_local_dir(snippet, local_dir)
        elif hf_cache_dir is not None:
            snippet = resources.inject_hf_cache_dir(snippet, hf_cache_dir)
        typer.echo(snippet)
    except (ValidationError, ResourceNotFoundError) as e:
        print_error(
            f"{str(e)}\n\nUse 'dell-ai models get-snippet' with a supported DEH configuration "
            f"to retrieve a validated snippet. However, you can still modify the deployment snippet manually to fit your needs."
        )
        raise typer.Exit(code=1)
    except GatedRepoAccessError as e:
        print_error(str(e))
        raise typer.Exit(code=1)
    except Exception as e:
        print_error(f"Failed to get deployment snippet: {str(e)}")
        raise typer.Exit(code=1)


@models_app.command("deploy")
def models_deploy(
    model_id: str = typer.Option(
        ...,
        "--model-id",
        "-m",
        help="Model ID in the format 'organization/model_name'",
    ),
    platform_id: str = typer.Option(
        ...,
        "--platform-id",
        "-p",
        help="Platform SKU ID",
    ),
    engine: str = typer.Option(
        "docker",
        "--engine",
        "-e",
        help="Deployment engine (docker or kubernetes)",
    ),
    gpus: Optional[int] = typer.Option(
        None,
        "--gpus",
        "-g",
        help="Number of GPUs to use. Required unless --goodput is set.",
        min=1,
    ),
    replicas: int = typer.Option(
        1,
        "--replicas",
        "-r",
        help="Number of replicas to deploy",
        min=1,
    ),
    goodput: Optional[str] = typer.Option(
        None,
        "--goodput",
        help=(
            "Deploy optimized for a goodput scenario "
            "(e.g. balanced, long-context, high-concurrency, performance). "
            "Cannot be combined with --gpus."
        ),
    ),
    detach: bool = typer.Option(
        True,
        "--detach/--no-detach",
        help="Whether to run the model in background (detached) mode",
    ),
    image_tag: Optional[str] = typer.Option(
        None,
        "--image-tag",
        help=(
            "Pin a specific container image tag before deploying (e.g. vllm-v0.11.2). "
            "Must be one of the tags available for the model/platform "
            "(see 'dell-ai models list-tags'). Defaults to the untagged image."
        ),
    ),
    local_dir: Optional[str] = typer.Option(
        None,
        "--local-dir",
        help=(
            "Path to a local directory containing model weights. "
            "Mounts the folder into the container and sets MODEL_ID to the mount path. "
            "Only supported with --engine docker. Mutually exclusive with --hf-cache-dir."
        ),
    ),
    hf_cache_dir: Optional[str] = typer.Option(
        None,
        "--hf-cache-dir",
        help=(
            "Path to a HuggingFace cache directory (same layout as "
            "'huggingface-cli download --cache-dir'). "
            "Mounts the folder as the container's HF cache and injects HF_HUB_CACHE. "
            "Only supported with --engine docker. Mutually exclusive with --local-dir."
        ),
    ),
) -> None:
    """
    Deploy a model directly on the local node.

    Provide either --gpus for manual GPU sizing or --goodput <scenario> to let
    the server size the deployment for you. Exactly one of the two is required.

    Use --local-dir or --hf-cache-dir to serve weights from a local folder instead
    of downloading them at container startup (Docker only).

    Examples:
        dell-ai models deploy -m google/gemma-3-27b-it -p xe9680-nvidia-h100 --gpus 8
        dell-ai models deploy -m google/gemma-3-27b-it -p xe9680-nvidia-h100 --goodput balanced
        dell-ai models deploy -m google/gemma-3-27b-it -p xe9680-nvidia-h100 --gpus 8 --image-tag vllm-v0.11.2
        dell-ai models deploy -m google/gemma-3-27b-it -p xe9680-nvidia-h100 --gpus 8 --local-dir /data/weights
        dell-ai models deploy -m google/gemma-3-27b-it -p xe9680-nvidia-h100 --gpus 8 --hf-cache-dir ~/.cache/huggingface
    """
    if goodput is not None and gpus is not None:
        print_error("--gpus cannot be combined with --goodput")
        raise typer.Exit(code=1)
    if goodput is None and gpus is None:
        print_error("Either --gpus or --goodput must be provided")
        raise typer.Exit(code=1)
    if local_dir is not None and hf_cache_dir is not None:
        print_error("--local-dir and --hf-cache-dir are mutually exclusive")
        raise typer.Exit(code=1)
    if local_dir is not None or hf_cache_dir is not None:
        if engine != "docker":
            print_error(
                "--local-dir and --hf-cache-dir are only supported with --engine docker"
            )
            raise typer.Exit(code=1)
    if local_dir is not None and not Path(local_dir).is_dir():
        print_error(
            f"--local-dir path does not exist or is not a directory: {local_dir}"
        )
        raise typer.Exit(code=1)
    if hf_cache_dir is not None and not Path(hf_cache_dir).is_dir():
        print_error(
            f"--hf-cache-dir path does not exist or is not a directory: {hf_cache_dir}"
        )
        raise typer.Exit(code=1)
    try:
        client = get_client()
        typer.echo(f"Deploying model {model_id} on {platform_id} using {engine}...")
        result = client.deploy_model(
            model_id=model_id,
            platform_id=platform_id,
            engine=engine,
            num_gpus=gpus,
            num_replicas=replicas,
            detach=detach,
            goodput=goodput,
            local_dir=local_dir,
            hf_cache_dir=hf_cache_dir,
            image_tag=image_tag,
        )
        if result.get("success"):
            typer.echo("🎉 Deployment initiated successfully!")
            if "container_id" in result:
                typer.echo(f"Docker Container ID: {result['container_id']}")
            if "k8s_deployment" in result:
                typer.echo(f"K8s Deployment: {result['k8s_deployment']}")
            if "endpoint" in result and result["endpoint"]:
                typer.echo(f"Endpoint URL: {result['endpoint']}")
        else:
            print_error(f"Deployment failed: {result.get('error')}")
    except (ValidationError, ResourceNotFoundError) as e:
        # TODO: This can pop up when users request a GPU count config that is not in DEH as a snippet, but that still would work.
        # Consider bypassing the validation by fetching the closes matching snippet and modifying it with the requested GPU count.
        print_error(
            f"{str(e)}\n\nYou can deploy manually using 'dell-ai models get-snippet' with a supported DEH configuration "
            f"to retrieve a validated snippet, and then modify it as needed."
        )
        raise typer.Exit(code=1)
    except GatedRepoAccessError as e:
        print_error(str(e))
        raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to deploy model: {str(e)}")
        raise typer.Exit(code=1)


@models_app.command("undeploy")
def models_undeploy(
    deployment_id: str = typer.Option(
        ...,
        "--deployment-id",
        "-d",
        help=(
            "Deployment ID to undeploy, as shown in the 'Deployment ID' column "
            "of 'dell-ai status'. For a model deployed once this is the model ID; "
            "additional instances of the same model are suffixed (e.g. 'org/model_1')."
        ),
    ),
) -> None:
    """
    Stop and remove a deployed model.

    Stops the running Docker container or Kubernetes deployment and removes
    the deployment entry from the registry.

    Each deployment is torn down individually. If the same model is deployed
    more than once, run 'dell-ai status' to see the suffixed deployment IDs and
    undeploy each one separately.
    """
    try:
        from dell_ai import deployments

        deployment = deployments.get_deployment(deployment_id)
        if not deployment:
            print_error(f"No active deployment found: {deployment_id}")
            raise typer.Exit(code=1)

        engine = deployment.get("engine")
        if engine == "docker":
            import subprocess

            container_id = deployment.get("container_id")
            if container_id:
                try:
                    subprocess.run(
                        ["docker", "stop", container_id],
                        capture_output=True,
                        check=True,
                    )
                    typer.echo(f"✓ Stopped Docker container: {container_id}")
                except subprocess.CalledProcessError as e:
                    print_warning(
                        f"Failed to stop Docker container: {e.stderr.decode()}"
                    )
            else:
                print_warning("No container ID found in deployment record")

        elif engine == "kubernetes":
            import subprocess

            k8s_deployment = deployment.get("k8s_deployment")
            if k8s_deployment:
                try:
                    subprocess.run(
                        ["kubectl", "delete", "deployment", k8s_deployment],
                        capture_output=True,
                        check=True,
                    )
                    typer.echo(f"✓ Deleted Kubernetes deployment: {k8s_deployment}")
                except subprocess.CalledProcessError as e:
                    print_warning(
                        f"Failed to delete Kubernetes deployment: {e.stderr.decode()}"
                    )
            else:
                print_warning("No deployment name found in deployment record")

        # Remove from registry
        deployments.delete_deployment(deployment_id)
        typer.echo(f"✓ Removed deployment entry for: {deployment_id}")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to undeploy model: {str(e)}")
        raise typer.Exit(code=1)


@models_app.command("goodput-scenarios")
def models_goodput_scenarios(
    platform_id: Optional[str] = typer.Option(
        None,
        "--platform-id",
        "-p",
        help="Show the SLO targets for a single SKU (scenario x SLO-field view)",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: 'json' for raw JSON, 'table' for a formatted table",
    ),
) -> None:
    """
    Show the global goodput reference data.

    Returns the scenario definitions, SLO field descriptions, and SLO targets
    per SKU. This data is static and shared across all models.

    Pass --platform-id to drill into the SLO targets for a single SKU, broken down by
    scenario. In table view this renders a scenario x SLO-field grid.

    Examples:
        dell-ai models goodput-scenarios --format table
        dell-ai models goodput-scenarios --platform-id xe9680-nvidia-h100 -f table
    """
    try:
        client = get_client()
        reference = client.get_goodput_scenarios()

        if platform_id is not None:
            slos = reference.slos_by_platform_id.get(platform_id)
            if not slos:
                documented = sorted(reference.slos_by_platform_id.keys())
                sku_list = ", ".join(documented) if documented else "none"
                print_error(
                    f"No SLO targets documented for SKU '{platform_id}'. "
                    f"SKUs with documented SLOs: {sku_list}"
                )
            if output_format == "table":
                print_slos_table(platform_id, slos)
            else:
                print_json({s: slo.model_dump() for s, slo in slos.items()})
            return

        if output_format == "table":
            print_goodput_scenarios_table(reference)
        else:
            print_json(reference.model_dump())
    except Exception as e:
        print_error(f"Failed to get goodput scenarios: {str(e)}")


@platforms_app.command("list")
def platforms_list(
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: 'json' for raw JSON, 'table' for a formatted table",
    ),
) -> None:
    """
    List all available platforms from the Dell Enterprise Hub.

    Returns platform SKU IDs. Use --format table for a human-readable table view.
    """
    try:
        client = get_client()
        platforms = client.list_platforms()
        if output_format == "table":
            print_platforms_table(platforms)
        else:
            print_json(platforms)
    except Exception as e:
        print_error(f"Failed to list platforms: {str(e)}")


@platforms_app.command("show")
def platforms_show(platform_id: str) -> None:
    """
    Show detailed information about a specific platform.

    Args:
        platform_id: The platform SKU ID
    """
    try:
        client = get_client()
        platform_info = client.get_platform(platform_id)
        print_json(platform_info)
    except ResourceNotFoundError:
        print_error(f"Platform not found: {platform_id}")
    except Exception as e:
        print_error(f"Failed to get platform information: {str(e)}")


@apps_app.command("list")
def apps_list(
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: 'json' for raw JSON, 'table' for a formatted table",
    ),
) -> None:
    """
    List all available applications from the Dell Enterprise Hub.

    Returns application names. Use --format table for a human-readable table view.
    """
    try:
        client = get_client()
        apps = client.list_apps()
        if output_format == "table":
            print_apps_table(apps)
        else:
            print_json(apps)
    except Exception as e:
        print_error(f"Failed to list applications: {str(e)}")


@apps_app.command("show")
def apps_show(app_id: str) -> None:
    """
    Show detailed information about a specific application.

    Args:
        app_id: The application ID
    """
    try:
        client = get_client()
        app_info = client.get_app(app_id)
        print_json(app_info.model_dump())
    except ResourceNotFoundError:
        print_error(f"Application not found: {app_id}")
    except Exception as e:
        print_error(f"Failed to get application information: {str(e)}")


@apps_app.command("get-snippet")
def apps_get_snippet(
    app_id: str = typer.Argument(..., help="Application ID"),
    config_json: str = typer.Option(
        "{}",
        "--config",
        "-c",
        help="JSON configuration string for the application",
    ),
) -> None:
    """
    Get a deployment snippet for an application with the provided configuration.

    This command generates a Helm installation command for deploying the specified
    application with the provided configuration parameters.

    Example configuration format:
    {
      "config": [
        {
          "helmPath": "main.config.storageClassName",
          "type": "string",
          "value": "custom-storage-class"
        },
        {
          "helmPath": "main.config.enableOpenAI",
          "type": "boolean",
          "value": true
        }
      ]
    }

    Examples:
        dell-ai apps get-snippet openwebui --config '{"config":[{"helmPath":"main.config.storageClassName","type":"string","value":"custom-storage-class"}]}'
    """
    try:
        # Parse the JSON configuration
        config_data = json.loads(config_json)
        config = config_data.get("config", [])

        # Create client and get deployment snippet
        client = get_client()
        snippet = client.get_app_snippet(app_id=app_id, config=config)
        typer.echo(snippet)
    except json.JSONDecodeError:
        print_error("Invalid JSON configuration format")
    except (ValidationError, ResourceNotFoundError) as e:
        # Handle expected errors with proper error messages
        print_error(str(e))
    except Exception as e:
        # Unexpected errors get a generic message
        print_error(f"Failed to get application deployment snippet: {str(e)}")


@apps_app.command("deploy")
def apps_deploy(
    app_id: str = typer.Argument(..., help="Application ID"),
    config_json: str = typer.Option(
        "{}",
        "--config",
        "-c",
        help="JSON configuration string for the application",
    ),
    detach: bool = typer.Option(
        True,
        "--detach/--no-detach",
        help="Whether to run the application in background (detached) mode",
    ),
) -> None:
    """
    Deploy an application directly on the local node.
    """
    try:
        # Parse the JSON configuration
        config_data = json.loads(config_json)
        config = config_data.get("config", [])

        client = get_client()
        typer.echo(f"Deploying application {app_id}...")
        result = client.deploy_app(app_id=app_id, config=config, detach=detach)
        if result.get("success"):
            typer.echo("🎉 Application deployment initiated successfully!")
            if "endpoint" in result and result["endpoint"]:
                typer.echo(f"Endpoint URL: {result['endpoint']}")
        else:
            print_error(f"Deployment failed: {result.get('error')}")
    except json.JSONDecodeError:
        print_error("Invalid JSON configuration format")
    except (ValidationError, ResourceNotFoundError) as e:
        print_error(str(e))
    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to deploy application: {str(e)}")


@utils_app.command("describe-system")
def utils_describe_system(
    out: str | None = typer.Option(
        None,
        "--out",
        "-o",
        help="Output to file path. Should be path to a writable file",
    ),
):
    """
    Get the representation for the current system in JSON format
    """
    try:
        sys_info = get_system_info()
        if sys_info is not None:
            if out is not None:
                path = Path(out)
                path.touch(exist_ok=True)
                path.write_text(sys_info.model_dump_json(indent=2))
            print_json(sys_info.model_dump())
        else:
            print_error("Only linux systems are supported. Failed to get system report")
    except Exception as e:
        # generic error
        print_error(f"Failed to get system description {str(e)}")


@utils_app.command("check-system")
def utils_check_system():
    """
    Validate system components against recommended configurations
    """
    try:
        sys_info: SystemInfo | None = get_system_info()
        if sys_info is not None:
            # get text representation of the system
            product = sys_info.os.product_prefix
            if product is None:
                print_error("Product name not found. Cannot list platforms")
            if len(sys_info.gpus):
                model = sys_info.gpus[0].model
                if model is None:
                    print_error("Model info not found, cannot find vendor model")
            else:
                print_error(
                    "No GPUs found in the system info. Cannot find vendor model"
                )
            platform_rep = f"{product.lower()}-{'-'.join(model.lower().split())}"

            client = get_client()
            available_platforms = client.list_platforms()

            configurations = []
            for platform in available_platforms:
                if platform == platform_rep:
                    platform_details = client.get_platform_system_info(platform)
                    configurations.extend(
                        [
                            SystemInfo.model_validate(platform_detail)
                            for platform_detail in platform_details
                        ]
                    )

            rich.print(
                f":watch: [magenta]Performing a comparison for {platform_rep} against available information [/]"
            )
            sys_info.compare(configurations)
    except (ValidationError, ResourceNotFoundError) as e:
        # Handle expected errors with proper error messages
        print_error(str(e))
    except Exception as e:
        # generic error
        print_error(f"Failed to check system: {str(e)}")


@skills_app.command("list")
def skills_list(
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: 'json' for raw JSON, 'table' for a formatted table",
    ),
) -> None:
    """
    List all available skills to interact with the Dell Enterprise Hub.

    Returns skill names. Use --format table for a human-readable table view.
    """

    try:
        skills = get_skills()
        if output_format == "table":
            print_skills_table(skills)
        else:
            print_json(skills)
    except Exception as e:
        print_error(f"Failed to list skills: {str(e)}")


@skills_app.command("show")
def skills_show(name: str) -> None:
    """
    Show detailed information about a specific skill.

    Args:
        name: The skill name
    """
    try:
        skills = get_skills()
        skill = next((s for s in skills if s["name"] == name), None)
        if skill is None:
            raise Exception(f"{name} skill not found")

        skill_md_path = Path(skill["path"])
        content = skill_md_path.read_text()
        typer.echo(content)
    except Exception as e:
        print_error(f"Failed to get skill information: {str(e)}")


@skills_app.command("add")
def add_skill(
    name: str = typer.Argument(..., help="Name of the skill to add"),
    codex: bool = typer.Option(
        False,
        "--codex",
        help="Symlink skill into Codex skills directory.",
    ),
    claude: bool = typer.Option(
        False,
        "--claude",
        help="Symlink skill into Claude skills directory.",
    ),
    cursor: bool = typer.Option(
        False,
        "--cursor",
        help="Symlink skill into Cursor skills directory.",
    ),
    opencode: bool = typer.Option(
        False,
        "--opencode",
        help="Symlink skill into OpenCode skills directory.",
    ),
    global_: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="Install in user-level directory instead of current project.",
    ),
    dest: Optional[Path] = typer.Option(
        None,
        "--dest",
        help="Custom destination directory (path to a skills directory).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing skill files if present.",
    ),
) -> None:
    """
    Symlinks the specified skill's SKILL.md into assistant directories.
    """
    if dest and (codex or claude or cursor or opencode or global_):
        typer.echo("--dest cannot be combined with assistant flags or --global.")
        raise typer.Exit(code=1)

    skills = get_skills()
    skill = next((s for s in skills if s["name"] == name), None)
    if skill is None:
        print_error(f"{name} skill not found")

    source = Path(skill["path"]).resolve()

    if dest:
        targets = [dest]
    else:
        agent_dirs = GLOBAL_AGENT_SKILLS_DIRS if global_ else LOCAL_AGENT_SKILLS_DIRS
        targets = []
        if codex:
            targets.append(agent_dirs["codex"])
        if claude:
            targets.append(agent_dirs["claude"])
        if cursor:
            targets.append(agent_dirs["cursor"])
        if opencode:
            targets.append(agent_dirs["opencode"])
        if not targets:
            typer.echo(
                "Select at least one assistant (--codex/--claude/--cursor/--opencode) or use --dest."
            )
            raise typer.Exit(code=1)

    for target in targets:
        skill_dir = Path(target).expanduser() / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        link = skill_dir / source.name
        if link.exists() or link.is_symlink():
            if not force:
                typer.echo(f"Skipped (already exists, use --force): {link}")
                continue
            link.unlink()
        link.symlink_to(source)
        typer.echo(f"Linked skill at: {link}")


def _mask_secret_value(key: str, value: str) -> str:
    sensitive_patterns = {"TOKEN", "SECRET", "KEY", "PASSWORD"}
    key_upper = key.upper()
    if any(pat in key_upper for pat in sensitive_patterns):
        if len(value) > 8:
            return value[:4] + "****"
        return "****"
    return value


@env_app.command("set")
def env_set(
    key: str = typer.Argument(
        ..., help="The environment variable name (e.g. DELL_AI_ENDPOINT)"
    ),
    value: str = typer.Argument(..., help="The environment variable value"),
    is_global: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="Set globally (user-wide). Defaults to local (directory-specific).",
    ),
) -> None:
    """
    Set a local or global environment variable.
    """
    try:
        env.set_env_var(key, value, is_global=is_global)
        scope = "globally" if is_global else "locally"
        typer.echo(f"Successfully set environment variable '{key}' {scope}.")
    except Exception as e:
        print_error(f"Failed to set environment variable: {str(e)}")
        raise typer.Exit(code=1)


@env_app.command("get")
def env_get(
    key: str = typer.Argument(..., help="The environment variable name"),
) -> None:
    """
    Get the value of an environment variable.
    """
    value = env.get_env_var(key)
    if value is not None:
        masked = _mask_secret_value(key, value)
        if masked != value:
            typer.echo(f"{masked} (masked)")
        else:
            typer.echo(value)
    else:
        print_error(f"Environment variable '{key}' not found.")
        raise typer.Exit(code=1)


@env_app.command("list")
def env_list(
    is_global: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="List global variables only.",
    ),
    is_local: bool = typer.Option(
        False,
        "--local",
        "-l",
        help="List local variables only.",
    ),
) -> None:
    """
    List environment variables.
    """
    try:
        if is_global and is_local:
            print_error("Cannot specify both --global and --local.")
            raise typer.Exit(code=1)

        scope = None
        if is_global:
            scope = True
        elif is_local:
            scope = False

        variables = env.list_env_vars(is_global=scope)
        if not variables:
            typer.echo("No environment variables found.")
            return

        for k, v in sorted(variables.items()):
            typer.echo(f"{k}={_mask_secret_value(k, v)}")
    except Exception as e:
        print_error(f"Failed to list environment variables: {str(e)}")
        raise typer.Exit(code=1)


@env_app.command("delete")
def env_delete(
    key: str = typer.Argument(..., help="The environment variable name"),
    is_global: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="Delete the variable from global scope instead of local scope.",
    ),
) -> None:
    """
    Delete a local or global environment variable.
    """
    try:
        deleted = env.delete_env_var(key, is_global=is_global)
        scope = "global" if is_global else "local"
        if deleted:
            typer.echo(f"Successfully deleted {scope} environment variable '{key}'.")
        else:
            print_error(f"Environment variable '{key}' not found in {scope} scope.")
            raise typer.Exit(code=1)
    except Exception as e:
        print_error(f"Failed to delete environment variable: {str(e)}")
        raise typer.Exit(code=1)


if __name__ == "__main__":  # pragma: no cover
    app()
