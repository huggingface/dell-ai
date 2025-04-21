"""Main client class for the Dell AI SDK."""

from typing import Dict, List, Any, Optional
import json

import requests

from dell_ai import constants, auth
from dell_ai.exceptions import (
    APIError,
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
)


class DellAIClient:
    """Main client for interacting with the Dell Enterprise Hub (DEH) API."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Dell AI client.

        Args:
            token: Hugging Face API token. If not provided, will attempt to load from
                  the Hugging Face token cache.
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

        To-do:
        - Check if the token is valid

        Returns:
            True if a token is available, False otherwise
        """
        return bool(self.token)
