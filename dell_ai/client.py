"""Main client class for the Dell AI SDK."""

import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import requests

from dell_ai import auth, constants, env
from dell_ai.exceptions import (
    APIError,
    AuthenticationError,
    ResourceNotFoundError,
    ValidationError,
)
from dell_ai.system_utils.system_info import SystemInfo

if TYPE_CHECKING:
    from dell_ai.apps import App
    from dell_ai.goodput import GoodputReference
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
        # Load local and global environment variables into os.environ
        env.load_all_env_to_os()

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
            # Prefer the API's own error message when present. The API uses
            # either "message" or "error" in its JSON error bodies.
            api_error_message = None
            try:
                error_data = response.json()
                if isinstance(error_data, dict):
                    api_error_message = error_data.get("message") or error_data.get(
                        "error"
                    )
            except (json.JSONDecodeError, AttributeError):
                pass

            error_message = api_error_message or response.text or f"HTTP Error: {e}"

            if response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed. Please check your token or login again."
                )
            elif response.status_code == 404:
                # Extract resource type and ID from the endpoint
                parts = endpoint.strip("/").split("/")
                resource_type = parts[0] if parts else "resource"
                resource_id = parts[-1] if len(parts) > 1 else "unknown"

                raise ResourceNotFoundError(
                    resource_type, resource_id, message=api_error_message
                )
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

    def list_models(
        self,
        query: Optional[str] = None,
        multimodal: Optional[bool] = None,
        min_size: Optional[float] = None,
        max_size: Optional[float] = None,
        license_filter: Optional[str] = None,
        platform_id: Optional[str] = None,
    ) -> List[str]:
        """
        Get a list of available model IDs.

        Args:
            query: Search query to match against model repo name or description
            multimodal: If set, filter for multimodal (True) or text-only (False) models
            min_size: Minimum model size in millions of parameters
            max_size: Maximum model size in millions of parameters
            license_filter: Filter by license type
            platform_id: Filter models that support a specific platform SKU

        Returns:
            A list of model IDs in the format "organization/model_name"

        Raises:
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        from dell_ai import models

        return models.list_models(
            self,
            query=query,
            multimodal=multimodal,
            min_size=min_size,
            max_size=max_size,
            license_filter=license_filter,
            platform_id=platform_id,
        )

    def search_models(
        self,
        query: Optional[str] = None,
        multimodal: Optional[bool] = None,
        min_size: Optional[float] = None,
        max_size: Optional[float] = None,
        license_filter: Optional[str] = None,
        platform_id: Optional[str] = None,
    ) -> List["Model"]:
        """
        Search and filter available models.

        Fetches all models and filters them based on the provided criteria.

        Args:
            query: Search query to match against model repo name or description (case-insensitive)
            multimodal: If set, filter for multimodal (True) or text-only (False) models
            min_size: Minimum model size in millions of parameters
            max_size: Maximum model size in millions of parameters
            license_filter: Filter by license type (case-insensitive substring match)
            platform_id: Filter models that support a specific platform SKU

        Returns:
            A list of Model objects matching the filter criteria

        Raises:
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        from dell_ai import models

        return models.search_models(
            self,
            query=query,
            multimodal=multimodal,
            min_size=min_size,
            max_size=max_size,
            license_filter=license_filter,
            platform_id=platform_id,
        )

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

    def get_compatible_platforms(self, model_id: str) -> List:
        """
        Get all platforms compatible with a given model, along with their GPU configurations.

        Args:
            model_id: The model ID in the format "organization/model_name"

        Returns:
            A list of PlatformCompatibility objects, each containing a platform ID
            and its supported GPU configurations for the given model.

        Raises:
            ValidationError: If the model_id format is invalid
            ResourceNotFoundError: If the model is not found
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        from dell_ai import models

        return models.get_compatible_platforms(self, model_id)

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

    def get_platform_system_info(self, platform_id: str) -> "List[SystemInfo]":
        """
        Get system information list for a specific platform

        Args:
            platform_id: The platform SKU ID

        Returns:
            System information list of tested Platforms

        Raises:
            ResourceNotFoundError: If the platform is not found
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        from dell_ai import platforms

        return platforms.get_platform_system_info(self, platform_id)

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
        num_gpus: Optional[int] = None,
        num_replicas: int = 1,
        goodput: Optional[str] = None,
    ) -> str:
        """
        Get a deployment snippet for the specified model and configuration.

        Provide either ``num_gpus`` for a manually-sized deployment, or
        ``goodput`` to let the server generate a snippet optimized for that
        goodput scenario (the two are mutually exclusive).

        Args:
            model_id: The model ID in the format "organization/model_name"
            platform_id: The platform SKU ID
            engine: The deployment engine ("docker" or "kubernetes")
            num_gpus: The number of GPUs to use (omit when using goodput)
            num_replicas: The number of replicas to deploy
            goodput: Goodput scenario to optimize for (e.g. "balanced")

        Returns:
            A string containing the deployment snippet (docker command or k8s manifest)

        Raises:
            ValidationError: If any of the input parameters are invalid
            ResourceNotFoundError: If the model or platform is not found
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        from dell_ai import models

        return models.get_deployment_snippet(
            self,
            model_id=model_id,
            platform_id=platform_id,
            engine=engine,
            num_gpus=num_gpus,
            num_replicas=num_replicas,
            goodput=goodput,
        )

    def get_goodput_scenarios(self) -> "GoodputReference":
        """
        Get the global goodput reference data (scenarios, SLO docs, SLO targets).

        This data is static, so it is cached on disk and reused until the cache
        entry expires.

        Returns:
            A GoodputReference object with scenario definitions, SLO field
            descriptions, and SLO targets per SKU

        Raises:
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        from dell_ai import goodput

        return goodput.get_goodput_scenarios(self)

    def list_apps(self) -> List[str]:
        """
        Get a list of all available application names.

        Returns:
            A list of application names

        Raises:
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        from dell_ai import apps

        return apps.list_apps(self)

    def get_app(self, app_id: str) -> "App":
        """
        Get detailed information about a specific application.

        Args:
            app_id: The application ID

        Returns:
            Detailed application information as an App object

        Raises:
            ResourceNotFoundError: If the application is not found
            AuthenticationError: If authentication fails
            APIError: If the API returns an error
        """
        from dell_ai import apps

        return apps.get_app(self, app_id)

    def get_app_snippet(self, app_id: str, config: List[Dict[str, Any]]) -> str:
        """
        Get a deployment snippet for the specified app with the provided configuration.

        Args:
            app_id: The application ID
            config: List of configuration parameters with helmPath, type, and value

        Returns:
            A string containing the deployment snippet (Helm command)

        Raises:
            ValidationError: If any of the input parameters are invalid
            ResourceNotFoundError: If the application is not found
            APIError: If the API returns an error
        """
        from dell_ai import apps

        return apps.get_app_snippet(self, app_id, config)

    def deploy_model(
        self,
        model_id: str,
        platform_id: str,
        engine: str,
        num_gpus: int,
        num_replicas: int,
        detach: bool = True,
    ) -> Dict[str, Any]:
        """
        Deploy a model on the local node.

        Args:
            model_id: The model ID in the format "organization/model_name"
            platform_id: The platform SKU ID
            engine: The deployment engine ("docker" or "kubernetes")
            num_gpus: The number of GPUs to use
            num_replicas: The number of replicas to deploy
            detach: Whether to run in detached (background) mode. Defaults to True.

        Returns:
            A dictionary containing deployment execution details.
        """
        snippet = self.get_deployment_snippet(
            model_id=model_id,
            platform_id=platform_id,
            engine=engine,
            num_gpus=num_gpus,
            num_replicas=num_replicas,
        )
        result = self._execute_snippet(snippet, detach=detach)

        # Save env vars if successful
        if result.get("success"):
            env.set_env_var(
                "DELL_AI_LAST_DEPLOYED_ENGINE", result.get("engine", "unknown")
            )
            if "container_id" in result:
                env.set_env_var(
                    "DELL_AI_LAST_DEPLOYED_CONTAINER", result["container_id"]
                )
            if "k8s_deployment" in result:
                env.set_env_var(
                    "DELL_AI_LAST_DEPLOYED_K8S_DEPLOYMENT", result["k8s_deployment"]
                )
            if "endpoint" in result and result["endpoint"]:
                env.set_env_var("DELL_AI_ENDPOINT", result["endpoint"])

        return result

    def deploy_app(
        self,
        app_id: str,
        config: List[Dict[str, Any]],
        detach: bool = True,
    ) -> Dict[str, Any]:
        """
        Deploy an application on the local node.

        Args:
            app_id: The application ID
            config: List of configuration parameters
            detach: Whether to run in detached (background) mode. Defaults to True.

        Returns:
            A dictionary containing deployment execution details.
        """
        snippet = self.get_app_snippet(app_id=app_id, config=config)
        result = self._execute_snippet(snippet, detach=detach)

        # Save env vars if successful
        if result.get("success"):
            env.set_env_var("DELL_AI_LAST_DEPLOYED_ENGINE", "helm")
            if "endpoint" in result and result["endpoint"]:
                env.set_env_var("DELL_AI_ENDPOINT", result["endpoint"])

        return result

    def _execute_snippet(self, snippet: str, detach: bool = True) -> Dict[str, Any]:
        """
        Helper method to execute a snippet command on the local node.
        """
        import subprocess
        import re

        snippet_stripped = snippet.strip()

        # Check if it's a Kubernetes YAML manifest
        if "apiVersion:" in snippet_stripped or "kind:" in snippet_stripped:
            try:
                # Try to extract deployment name
                deployment_name = "tgi-deployment"
                match = re.search(
                    r"metadata:\s*\n\s*name:\s*([^\s\n]+)", snippet_stripped
                )
                if match:
                    deployment_name = match.group(1)

                proc = subprocess.run(
                    ["kubectl", "apply", "-f", "-"],
                    input=snippet_stripped,
                    text=True,
                    capture_output=True,
                    check=True,
                )
                return {
                    "success": True,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "k8s_deployment": deployment_name,
                    "engine": "kubernetes",
                    "snippet": snippet_stripped,
                }
            except Exception as e:
                return {"success": False, "error": str(e), "snippet": snippet_stripped}
        else:
            # Shell command (Docker run or Helm install, etc.)
            cmd = snippet_stripped
            is_docker_run = "docker run" in cmd
            is_docker_run_detach = detach and is_docker_run
            if is_docker_run_detach:
                # Replace interactive/foreground flags with detach (-d)
                if "-it" in cmd:
                    cmd = cmd.replace("-it", "-d")
                elif " -i " in cmd:
                    cmd = cmd.replace(" -i ", " -d ")
                elif " -t " in cmd:
                    cmd = cmd.replace(" -t ", " -d ")
                elif " -d " not in cmd:
                    cmd = re.sub(r"(docker run\s+)", r"\1-d ", cmd)

            try:
                # For detached docker run, we capture output to get the container ID
                if is_docker_run_detach:
                    proc = subprocess.run(
                        cmd, shell=True, text=True, capture_output=True, check=True
                    )
                    container_id = proc.stdout.strip().split("\n")[-1]

                    # Try to parse port mapping to construct the endpoint URL
                    port = "80"
                    port_match = re.search(r"-p\s+(\d+):", cmd)
                    if port_match:
                        port = port_match.group(1)

                    endpoint = f"http://localhost:{port}"
                    return {
                        "success": True,
                        "stdout": proc.stdout,
                        "stderr": proc.stderr,
                        "container_id": container_id,
                        "endpoint": endpoint,
                        "engine": "docker",
                        "snippet": cmd,
                    }
                else:
                    # Let it inherit stdout/stderr so the user can interact/see progress
                    proc = subprocess.run(cmd, shell=True, check=True)
                    return {
                        "success": True,
                        "stdout": "",
                        "stderr": "",
                        "engine": "helm" if "helm" in cmd else "docker",
                        "snippet": cmd,
                    }
            except Exception as e:
                return {"success": False, "error": str(e), "snippet": cmd}
