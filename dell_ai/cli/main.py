"""Command-line interface for Dell AI."""

import json
import typer
from typing import Optional

from dell_ai import __version__, auth
from dell_ai.client import DellAIClient
from dell_ai.exceptions import AuthenticationError

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
    token: Optional[str] = typer.Option(None, "--token", help="Hugging Face API token")
):
    """
    Log in to Dell AI using a Hugging Face token.
    """
    if not token:
        token = typer.prompt("Enter your Hugging Face token", hide_input=True)

    try:
        auth.login(token)
        typer.echo("Successfully logged in")
    except AuthenticationError as e:
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(code=1)


@auth_app.command("logout")
def auth_logout():
    """
    Log out from Dell AI.
    """
    auth.logout()
    typer.echo("Successfully logged out")


@auth_app.command("status")
def auth_status():
    """
    Show the current authentication status.
    """
    if not auth.is_logged_in():
        typer.echo("Not logged in")
        return

    try:
        client = DellAIClient()
        if client.is_authenticated():
            user_info = client.get_user_info()
            typer.echo(f"Logged in as: {user_info.get('name', 'Unknown')}")
            # Optional: Output full user info as JSON
            typer.echo(f"User info: {json.dumps(user_info, indent=2)}")
        else:
            typer.echo("Token found but validation failed. Please login again.")
    except AuthenticationError as e:
        typer.echo(f"Authentication error: {str(e)}", err=True)
        typer.echo("Please login again")


@models_app.command("list")
def models_list():
    """
    List all available models.
    """
    typer.echo("Models list functionality will be implemented here")


@models_app.command("show")
def models_show(model_id: str):
    """
    Show details for a specific model.
    """
    typer.echo(f"Model details functionality will be implemented here for {model_id}")


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
