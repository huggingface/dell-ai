"""Utility functions for the Dell AI CLI."""

import json
import sys
from typing import Any, Dict, List

import typer


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
