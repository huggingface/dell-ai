"""App-related functionality for the Dell AI SDK."""

from typing import Dict, List, Optional, Any, TYPE_CHECKING
from pydantic import BaseModel, Field

from dell_ai import constants
from dell_ai.exceptions import ResourceNotFoundError, ValidationError, APIError

if TYPE_CHECKING:
    from dell_ai.client import DellAIClient


class EnvParam(BaseModel):
    """Environment parameter for app configuration."""

    name: str
    description: str
    type: str = Field(
        description="Parameter type", examples=["string", "number", "boolean", "json"]
    )
    example: Optional[str] = None
    required: Optional[bool] = None
    default: Optional[Any] = None
    helmPath: str
    value: Optional[Any] = None


class Secret(BaseModel):
    """Secret parameter for app configuration."""

    name: str
    description: str
    type: str
    example: Optional[str] = None
    required: Optional[bool] = None
    helmPath: str


class AppComponent(BaseModel):
    """Component of an application."""

    id: str
    name: str
    description: str
    required: bool
    config: List[EnvParam]
    secrets: List[Secret]


class App(BaseModel):
    """Represents an application in the catalog."""

    id: str
    name: str
    license: str
    image: str
    screenshot: str
    docs: str
    description: str
    features: str
    instructions: str
    tags: List[str]
    recommendedModels: List[str]
    components: List[AppComponent]


def list_apps(client: "DellAIClient") -> List[str]:
    """
    Get a list of all available application names.

    Args:
        client: The Dell AI client

    Returns:
        A list of application names

    Raises:
        AuthenticationError: If authentication fails
        APIError: If the API returns an error
    """
    response = client._make_request("GET", constants.APPS_ENDPOINT)
    return response.get("apps", [])


def get_app(client: "DellAIClient", app_id: str) -> App:
    """
    Get detailed information about a specific application.

    Args:
        client: The Dell AI client
        app_id: The application ID

    Returns:
        Detailed application information as an App object

    Raises:
        ResourceNotFoundError: If the application is not found
        AuthenticationError: If authentication fails
        APIError: If the API returns an error
    """
    try:
        endpoint = f"{constants.APPS_ENDPOINT}/{app_id}"
        response = client._make_request("GET", endpoint)
        return App.model_validate(response)
    except ResourceNotFoundError:
        # Reraise with more specific information
        raise ResourceNotFoundError("app", app_id)


def get_app_snippet(
    client: "DellAIClient", app_id: str, config: List[Dict[str, Any]]
) -> str:
    """
    Get a deployment snippet for the specified app with the provided configuration.

    Args:
        client: The Dell AI client
        app_id: The application ID
        config: List of configuration parameters with helmPath, type, and value

    Returns:
        A string containing the deployment snippet (Helm command)

    Raises:
        ValidationError: If any of the input parameters are invalid
        ResourceNotFoundError: If the application is not found
        APIError: If the API returns an error
    """
    try:
        # Use the correct endpoint construction from the implementation plan
        endpoint = f"{constants.SNIPPETS_ENDPOINT}/apps/{app_id}"
        data = {"config": config}

        # Make the API request
        response = client._make_request("POST", endpoint, data=data)

        # Extract the snippet from the response
        if (
            isinstance(response, dict)
            and "snippet" in response
            and "raw" in response.get("snippet", {})
        ):
            return response["snippet"]["raw"]
        else:
            # Handle unexpected response format
            raise ValidationError("Unexpected response format from API")
    except ResourceNotFoundError:
        # Reraise with more specific information
        raise ResourceNotFoundError("app", app_id)
    except ValidationError as e:
        # Pass through validation errors
        raise e
    except Exception as e:
        # Handle other errors with appropriate context
        if hasattr(e, "response") and getattr(e, "response", None):
            status_code = getattr(e.response, "status_code", None)
            if status_code == 400:
                raise ValidationError("Invalid request: " + str(e))
            elif status_code == 404:
                raise ResourceNotFoundError("app", app_id)
            elif status_code == 500:
                raise APIError(
                    "Server error. Please verify your configuration and app ID."
                )
        # If not a recognized error, re-raise
        raise
