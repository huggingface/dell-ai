"""Main client class for the Dell AI SDK."""

from typing import Dict, List, Any, Optional

import requests

from dell_ai import constants
from dell_ai.exceptions import APIError, AuthenticationError, ResourceNotFoundError


class DellAIClient:
    """Main client for interacting with the Dell Enterprise Hub (DEH) API."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Dell AI client.

        Args:
            token: Hugging Face API token. If not provided, will attempt to load from
                  the Hugging Face token cache.
        """
        self.token = token
        self.base_url = constants.API_BASE_URL
        self.session = requests.Session()

        # Set up authentication if token is provided
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            # We'll implement proper HF token loading in auth.py
            pass

    def _make_request(
        self, method: str, endpoint: str, params: Dict = None, data: Dict = None
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
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method, url=url, params=params, json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Please check your token."
                )
            elif response.status_code == 404:
                raise ResourceNotFoundError(f"Resource not found: {endpoint}")
            else:
                raise APIError(
                    f"API Error: {str(e)}",
                    status_code=response.status_code,
                    response=response.text,
                )
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")
