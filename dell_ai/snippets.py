"""Snippet generation functionality for the Dell AI SDK."""

from pydantic import BaseModel, Field, field_validator

from dell_ai import constants
from dell_ai.client import DellAIClient
from dell_ai.exceptions import ValidationError, ResourceNotFoundError
from dell_ai import models


class SnippetRequest(BaseModel):
    """Request model for generating deployment snippets."""

    model_id: str = Field(
        ..., description="Model ID in format 'organization/model_name'"
    )
    sku_id: str = Field(..., description="Platform SKU ID")
    container_type: str = Field(
        ..., description="Container type ('docker' or 'kubernetes')"
    )
    num_gpus: int = Field(..., gt=0, description="Number of GPUs to use")
    num_replicas: int = Field(..., gt=0, description="Number of replicas to deploy")

    @field_validator("container_type")
    @classmethod
    def validate_container_type(cls, v):
        if v.lower() not in ["docker", "kubernetes"]:
            raise ValueError(
                f"Invalid container type: {v}. Valid types are: docker, kubernetes"
            )
        return v.lower()


class SnippetResponse(BaseModel):
    """Response model for deployment snippets."""

    snippet: str = Field(..., description="The deployment snippet text")


def get_deployment_snippet(
    client: DellAIClient,
    model_id: str,
    sku_id: str,
    container_type: str,
    num_gpus: int,
    num_replicas: int,
) -> str:
    """
    Get a deployment snippet for the specified model and configuration.

    Args:
        client: The Dell AI client
        model_id: The model ID in the format "organization/model_name"
        sku_id: The platform SKU ID
        container_type: The container type ("docker" or "kubernetes")
        num_gpus: The number of GPUs to use
        num_replicas: The number of replicas to deploy

    Returns:
        A string containing the deployment snippet (docker command or k8s manifest)

    Raises:
        ValidationError: If any of the input parameters are invalid
    """
    # Validate input using Pydantic model
    request = SnippetRequest(
        model_id=model_id,
        sku_id=sku_id,
        container_type=container_type,
        num_gpus=num_gpus,
        num_replicas=num_replicas,
    )

    # Split model_id into creator and model components
    try:
        creator_name, model_name = model_id.split("/")
    except ValueError:
        raise ValidationError(
            f"Invalid model_id format: {model_id}. Expected format: 'organization/model_name'"
        )

    # Get model details to validate configuration
    try:
        model = models.get_model(client, model_id)

        # Check if the platform is supported
        if sku_id not in model.configs_deploy:
            raise ValidationError(
                f"Platform {sku_id} is not supported for model {model_id}",
                config_details={
                    "model_id": model_id,
                    "platform_id": sku_id,
                    "valid_configs": [],
                },
            )

        # Validate the configuration
        valid_configs = model.configs_deploy[sku_id]
        valid_gpus = {config.num_gpus for config in valid_configs}

        if num_gpus not in valid_gpus:
            raise ValidationError(
                f"Invalid number of GPUs: {num_gpus}",
                config_details={
                    "model_id": model_id,
                    "platform_id": sku_id,
                    "valid_configs": valid_configs,
                },
            )

    except ResourceNotFoundError:
        # If model not found, continue with the request - the API will handle this error
        pass

    # Build API path and query parameters
    path = f"{constants.SNIPPETS_ENDPOINT}/models/{creator_name}/{model_name}/deploy"
    params = {
        "sku": sku_id,
        "container": container_type,
        "replicas": num_replicas,
        "gpus": num_gpus,
    }

    # Make API request
    response = client._make_request("GET", path, params=params)

    # Parse and validate response
    return SnippetResponse(snippet=response.get("snippet", "")).snippet
