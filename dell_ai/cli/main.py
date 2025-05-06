"""Command-line interface for Dell AI."""

import typer
from typing import Optional

from dell_ai import __version__, auth
from dell_ai.exceptions import (
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
    GatedRepoAccessError,
)
from dell_ai.cli.utils import (
    get_client,
    print_json,
    print_error,
)

app = typer.Typer(
    name="dell-ai",
    help="CLI for interacting with the Dell Enterprise Hub (DEH)",
    add_completion=False,
)

models_app = typer.Typer(help="Model commands")
platforms_app = typer.Typer(help="Platform commands")
snippets_app = typer.Typer(help="Snippet commands")

app.add_typer(models_app, name="models")
app.add_typer(platforms_app, name="platforms")
app.add_typer(snippets_app, name="snippets")


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
    )
):
    """
    Dell AI CLI - Interact with the Dell Enterprise Hub (DEH)
    """
    pass


@app.command("login")
def auth_login(
    token: Optional[str] = typer.Option(
        None,
        "--token",
        help="Hugging Face API token. If not provided, you will be prompted to enter it.",
    )
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


@models_app.command("list")
def models_list() -> None:
    """
    List all available models from the Dell Enterprise Hub.

    Returns a JSON array of model IDs in the format "organization/model_name".
    """
    try:
        client = get_client()
        models = client.list_models()
        print_json(models)
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


@platforms_app.command("list")
def platforms_list() -> None:
    """
    List all available platforms from the Dell Enterprise Hub.

    Returns a JSON array of platform SKU IDs.
    """
    try:
        client = get_client()
        platforms = client.list_platforms()
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


@snippets_app.command("get")
def snippets_get(
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
    gpus: int = typer.Option(
        1,
        "--gpus",
        "-g",
        help="Number of GPUs to use",
        min=1,
    ),
    replicas: int = typer.Option(
        1,
        "--replicas",
        "-r",
        help="Number of replicas to deploy",
        min=1,
    ),
) -> None:
    """
    Get a deployment snippet for running a model on a specific platform.

    This command generates a deployment snippet (Docker command or Kubernetes manifest)
    for running the specified model on the given platform with the provided configuration.

    Args:
        model_id: Model ID in the format 'organization/model_name'
        platform_id: Platform SKU ID
        engine: Deployment engine (docker or kubernetes)
        gpus: Number of GPUs to use
        replicas: Number of replicas to deploy

    Examples:
        dell-ai snippets get --model-id google/gemma-3-27b-it --platform-id xe9680-nvidia-h100 --engine docker --gpus 1 --replicas 1
        dell-ai snippets get -m google/gemma-3-27b-it -p xe9680-nvidia-h100 -e kubernetes -g 2 -r 3
    """
    try:
        # Create client and get deployment snippet
        client = get_client()
        snippet = client.get_deployment_snippet(
            model_id=model_id,
            platform_id=platform_id,
            engine=engine,
            num_gpus=gpus,
            num_replicas=replicas,
        )
        typer.echo(snippet)
    except (ValidationError, ResourceNotFoundError, GatedRepoAccessError) as e:
        # Handle expected errors with proper error messages
        print_error(str(e))
    except Exception as e:
        # Unexpected errors get a generic message
        print_error(f"Failed to get deployment snippet: {str(e)}")


if __name__ == "__main__":
    app()
