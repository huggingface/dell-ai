"""Utility functions for the Dell AI CLI."""

import json
import sys
from typing import Any, Dict, List, Optional

import typer
from dell_ai import DellAIClient
from dell_ai.exceptions import AuthenticationError


def print_json(data: Any) -> None:
    """
    Print data as JSON to stdout.

    Args:
        data: Data to print as JSON
    """
    print(json.dumps(data, indent=2))


def print_error(message: str) -> None:
    """
    Print an error message to stderr and exit with status code 1.

    Args:
        message: Error message to print
    """
    typer.echo(f"Error: {message}", err=True)
    sys.exit(1)


def validate_container_type(container_type: str) -> str:
    """
    Validate the container type.

    Args:
        container_type: Container type to validate

    Returns:
        The validated container type

    Raises:
        ValueError: If the container type is invalid
    """
    valid_types = ["docker", "kubernetes"]
    if container_type.lower() not in valid_types:
        raise ValueError(
            f"Invalid container type: {container_type}. "
            f"Valid types are: {', '.join(valid_types)}"
        )
    return container_type.lower()


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
        return DellAIClient(token=token)
    except AuthenticationError as e:
        print_error(str(e))


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
