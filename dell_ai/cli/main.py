"""Command-line interface for Dell AI."""

import json
import typer
from typing import Optional

from dell_ai import __version__, auth
from dell_ai.client import DellAIClient
from dell_ai.exceptions import AuthenticationError, ResourceNotFoundError
from dell_ai.cli.utils import get_client, print_json, print_error

app = typer.Typer(
    name="dell-ai",
    help="CLI for interacting with the Dell Enterprise Hub (DEH)",
    add_completion=False,
)

auth_app = typer.Typer(help="Authentication commands")
models_app = typer.Typer(help="Model commands")
platforms_app = typer.Typer(help="Platform commands")
snippets_app = typer.Typer(help="Snippet commands")

app.add_typer(auth_app, name="auth")
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


@auth_app.command("login")
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


@auth_app.command("logout")
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


@auth_app.command("status")
def auth_status() -> None:
    """
    Show the current authentication status and user information.
    """
    if not auth.is_logged_in():
        typer.echo("Status: Not logged in")
        typer.echo("To log in, run: dell-ai auth login")
        return

    try:
        user_info = auth.get_user_info()
        typer.echo("Status: Logged in")
        typer.echo(f"User: {user_info.get('name', 'Unknown')}")
        typer.echo(f"Email: {user_info.get('email', 'Not available')}")
        typer.echo(f"Organization: {user_info.get('orgs', ['None'])[0]}")
    except AuthenticationError as e:
        typer.echo(f"Status: Error ({str(e)})")
        typer.echo("Please try logging in again: dell-ai auth login")
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


@platforms_app.command("list")
def platforms_list():
    """
    List all available platforms.
    """
    typer.echo("Platforms list functionality will be implemented here")


@platforms_app.command("show")
def platforms_show(sku_id: str):
    """
    Show details for a specific platform.
    """
    typer.echo(f"Platform details functionality will be implemented here for {sku_id}")


@snippets_app.command("get")
def snippets_get(
    model_id: str,
    sku_id: str,
    container: str = typer.Option(
        ..., "--container", help="Container type (docker or kubernetes)"
    ),
    gpus: int = typer.Option(..., "--gpus", help="Number of GPUs to use"),
    replicas: int = typer.Option(
        ..., "--replicas", help="Number of replicas to deploy"
    ),
):
    """
    Get a deployment snippet for the specified model and configuration.
    """
    typer.echo(
        f"Snippet generation functionality will be implemented here for {model_id} on {sku_id}"
    )


if __name__ == "__main__":
    app()
