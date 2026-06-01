"""Utility functions for the Dell AI CLI."""

import json
from typing import Any, List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dell_ai import DellAIClient
from dell_ai.exceptions import AuthenticationError

# Create console for rich output
console = Console(stderr=True)
# Console for stdout (for table output)
stdout_console = Console()


def print_json(data: Any) -> None:
    """
    Print data as JSON to stdout.

    Args:
        data: Data to print as JSON
    """
    if hasattr(data, "dict"):
        data = data.dict()
    print(json.dumps(data, indent=2, default=str))


def print_error(message: str) -> None:
    """
    Print an error message to stderr and exit with status code 1.
    Uses Rich formatting for better readability.

    Args:
        message: Error message to print
    """
    console.print(
        Panel.fit(
            f"[bold red]Error:[/bold red] {message}",
            border_style="red",
            title="Dell AI CLI",
        )
    )
    raise typer.Exit(code=1)


def get_client(token: Optional[str] = None) -> DellAIClient:
    """
    Create and return a DellAIClient instance.

    Args:
        token: Optional Hugging Face API token. If not provided, will attempt to load
              from the Hugging Face token cache.

    Returns:
        A configured DellAIClient instance

    Raises:
        SystemExit: If authentication fails
    """
    try:
        client = DellAIClient(token=token)
    except AuthenticationError as e:
        print_error(str(e))
    return client


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask for user confirmation before proceeding with an action.

    Args:
        message: The confirmation message to display
        default: The default value if the user just presses Enter

    Returns:
        True if the user confirms, False otherwise
    """
    return typer.confirm(message, default=default)


def print_models_table(models: List[str]) -> None:
    """
    Print a list of model IDs as a Rich table.

    Args:
        models: List of model ID strings
    """
    table = Table(title="Available Models")
    table.add_column("#", style="dim", width=4)
    table.add_column("Model ID", style="cyan")

    for i, model_id in enumerate(models, 1):
        table.add_row(str(i), model_id)

    stdout_console.print(table)


def print_platforms_table(platforms: List[str]) -> None:
    """
    Print a list of platform IDs as a Rich table.

    Args:
        platforms: List of platform SKU ID strings
    """
    table = Table(title="Available Platforms")
    table.add_column("#", style="dim", width=4)
    table.add_column("Platform SKU ID", style="green")

    for i, platform_id in enumerate(platforms, 1):
        table.add_row(str(i), platform_id)

    stdout_console.print(table)


def print_apps_table(apps: List[str]) -> None:
    """
    Print a list of app names as a Rich table.

    Args:
        apps: List of application name strings
    """
    table = Table(title="Available Applications")
    table.add_column("#", style="dim", width=4)
    table.add_column("Application", style="magenta")

    for i, app_name in enumerate(apps, 1):
        table.add_row(str(i), app_name)

    stdout_console.print(table)


def print_search_results_table(models: List[Any]) -> None:
    """
    Print model search results as a Rich table with details.

    Args:
        models: List of Model objects (or dicts with model_dump())
    """
    table = Table(title="Search Results")
    table.add_column("#", style="dim", width=4)
    table.add_column("Model ID", style="cyan")
    table.add_column("Size (M)", justify="right", style="yellow")
    table.add_column("Multimodal", style="green")
    table.add_column("License", style="blue")
    table.add_column("Platforms", style="magenta")

    for i, model in enumerate(models, 1):
        if hasattr(model, "model_dump"):
            data = model.model_dump()
        else:
            data = model
        platforms = list(data.get("configs_deploy", {}).get("config_per_sku", {}).keys())
        table.add_row(
            str(i),
            data.get("repo_name", ""),
            str(data.get("size", "")),
            "Yes" if data.get("is_multimodal") else "No",
            data.get("license", ""),
            ", ".join(platforms) if platforms else "-",
        )

    stdout_console.print(table)


def print_compatible_platforms_table(results: List[Any]) -> None:
    """
    Print compatible platforms and their GPU configurations as a Rich table.

    Args:
        results: List of PlatformCompatibility objects (or dicts)
    """
    table = Table(title="Compatible Platforms")
    table.add_column("#", style="dim", width=4)
    table.add_column("Platform SKU", style="green")
    table.add_column("GPU Counts", justify="right", style="yellow")
    table.add_column("Max Input Tokens", justify="right", style="cyan")
    table.add_column("Max Total Tokens", justify="right", style="blue")

    for i, result in enumerate(results, 1):
        if hasattr(result, "model_dump"):
            data = result.model_dump()
        else:
            data = result
        configs = data.get("configs", [])
        gpu_counts = ", ".join(str(c.get("num_gpus", "-")) for c in configs)
        max_input = ", ".join(
            str(c.get("max_input_tokens", "-")) for c in configs
        )
        max_total = ", ".join(
            str(c.get("max_total_tokens", "-")) for c in configs
        )
        table.add_row(
            str(i),
            data.get("platform_id", ""),
            gpu_counts,
            max_input,
            max_total,
        )

    stdout_console.print(table)
