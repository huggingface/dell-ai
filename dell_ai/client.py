"""Main client class for the Dell AI SDK."""

from typing import Dict, List, Any, Optional, TYPE_CHECKING
import json

import requests

from dell_ai import constants, auth
from dell_ai.exceptions import (
    APIError,
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
)

if TYPE_CHECKING:
    from dell_ai.models import Model
    from dell_ai.platforms import Platform


class DellAIClient:
    """Main client for interacting with the Dell Enterprise Hub (DEH) API."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Dell AI client.

        Args:
            token: Hugging Face API token. If not provided, will attempt to load from
                  the Hugging Face token cache.

        Raises:
            AuthenticationError: If a token is provided but invalid
        """
        self.base_url = constants.API_BASE_URL
        self.session = requests.Session()

        # Set default headers
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "dell-ai-sdk/python",
            }
        )

        # Set up authentication
        self.token = token or auth.get_token()
        if self.token:
            # If token was explicitly provided, validate it
            if token and not auth.validate_token(token):
                raise AuthenticationError("Invalid authentication token provided.")

            self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data

        Returns:
            Response data as a dictionary

        Raises:
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
            ResourceNotFoundError: If the requested resource is not found
            ValidationError: If the input parameters are invalid
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method, url=url, params=params, json=data
            )
            response.raise_for_status()

            # Ensure we have a valid JSON response
            try:
                return response.json()
            except json.JSONDecodeError:
                raise APIError(
                    "Invalid JSON response from API",
                    status_code=response.status_code,
                    response=response.text,
                )

        except requests.exceptions.HTTPError as e:
            error_message = f"HTTP Error: {e}"

            try:
                error_data = response.json()
                if "message" in error_data:
                    error_message = error_data["message"]
            except (json.JSONDecodeError, AttributeError):
                # Use the response text if can't parse JSON
                if response.text:
                    error_message = response.text

            if response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Please check your token or login again."
                )
            elif response.status_code == 404:
                # Extract resource type and ID from the endpoint
                parts = endpoint.strip("/").split("/")
                resource_type = parts[0] if parts else "resource"
                resource_id = parts[-1] if len(parts) > 1 else "unknown"
                raise ResourceNotFoundError(resource_type, resource_id)
            elif response.status_code == 400:
                raise ValidationError(f"Invalid request: {error_message}")
            else:
                raise APIError(
                    error_message,
                    status_code=response.status_code,
                    response=response.text,
                )
        except requests.exceptions.ConnectionError as e:
            raise APIError(f"Connection error: {str(e)}")
        except requests.exceptions.Timeout as e:
            raise APIError(f"Request timed out: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")

    def is_authenticated(self) -> bool:
        """
        Check if the client has a valid authentication token.

        Returns:
            True if the token is valid, False otherwise
        """
        if not self.token:
            return False

        try:
            return auth.validate_token(self.token)
        except Exception:
            return False

    def get_user_info(self) -> Dict[str, Any]:
        """
        Get information about the authenticated user.

        Returns:
            A dictionary with user information

        Raises:
            AuthenticationError: If authentication fails or no token is available
        """
        if not self.token:
            raise AuthenticationError(
                "No authentication token available. Please login first."
            )

        return auth.get_user_info(self.token)

    def list_models(self) -> List[str]:
        """
        Get a list of all available model IDs.

        Returns:
            A list of model IDs in the format "organization/model_name"

        Raises:
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        from dell_ai import models

        return models.list_models(self)

    def get_model(self, model_id: str) -> "Model":
        """
        Get detailed information about a specific model.

        Args:
            model_id: The model ID in the format "organization/model_name"

        Returns:
            Detailed model information as a Model object

        Raises:
            ValidationError: If the model_id format is invalid
            ResourceNotFoundError: If the model is not found
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        from dell_ai import models

        return models.get_model(self, model_id)

    def list_platforms(self) -> List[str]:
        """
        Get a list of all available platform SKU IDs.

        Returns:
            A list of platform SKU IDs

        Raises:
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        from dell_ai import platforms

        return platforms.list_platforms(self)

    def get_platform(self, platform_id: str) -> "Platform":
        """
        Get detailed information about a specific platform.

        Args:
            platform_id: The platform SKU ID

        Returns:
            Detailed platform information as a Platform object

        Raises:
            ResourceNotFoundError: If the platform is not found
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        from dell_ai import platforms

        return platforms.get_platform(self, platform_id)

    def check_model_access(self, model_id: str) -> bool:
        """
        Check if the authenticated user has access to a specific model repository.

        Args:
            model_id: The model ID in the format "organization/model_name"

        Returns:
            True if the user has access to the model repository

        Raises:
            AuthenticationError: If no token is available or authentication fails
            GatedRepoAccessError: If the repository is gated and the user doesn't have access
            ResourceNotFoundError: If the model doesn't exist
        """
        from dell_ai import auth

        return auth.check_model_access(model_id, self.token)

    def get_deployment_snippet(
        self,
        model_id: str,
        platform_id: str,
        engine: str,
        num_gpus: int,
        num_replicas: int,
    ) -> str:
        """
        Get a deployment snippet for the specified model and configuration.

        Args:
            model_id: The model ID in the format "organization/model_name"
            platform_id: The platform SKU ID
            engine: The deployment engine ("docker" or "kubernetes")
            num_gpus: The number of GPUs to use
            num_replicas: The number of replicas to deploy

        Returns:
            A string containing the deployment snippet (docker command or k8s manifest)

        Raises:
            ValidationError: If any of the input parameters are invalid
            ResourceNotFoundError: If the model or platform is not found
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        from dell_ai import snippets

        return snippets.get_deployment_snippet(
            self,
            model_id=model_id,
            platform_id=platform_id,
            engine=engine,
            num_gpus=num_gpus,
            num_replicas=num_replicas,
        )
