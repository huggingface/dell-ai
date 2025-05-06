"""Snippet generation functionality for the Dell AI SDK."""

from pydantic import BaseModel, Field, field_validator

from dell_ai import constants
from dell_ai.client import DellAIClient
from dell_ai.exceptions import (
    ValidationError,
    ResourceNotFoundError,
)
from dell_ai import models


class SnippetRequest(BaseModel):
    """Request model for generating deployment snippets."""

    model_id: str = Field(
        ..., description="Model ID in format 'organization/model_name'"
    )
    platform_id: str = Field(..., description="Platform SKU ID")
    engine: str = Field(..., description="Deployment engine ('docker' or 'kubernetes')")
    num_gpus: int = Field(..., gt=0, description="Number of GPUs to use")
    num_replicas: int = Field(..., gt=0, description="Number of replicas to deploy")

    @field_validator("engine")
    @classmethod
    def validate_engine(cls, v):
        if v.lower() not in ["docker", "kubernetes"]:
            raise ValueError(
                f"Invalid engine: {v}. Valid types are: docker, kubernetes"
            )
        return v.lower()


class SnippetResponse(BaseModel):
    """Response model for deployment snippets."""

    snippet: str = Field(..., description="The deployment snippet text")


def _validate_request_schema(model_id, platform_id, engine, num_gpus, num_replicas):
    """
    Validate the basic schema of the request parameters.

    Args:
        model_id: The model ID
        platform_id: The platform SKU ID
        engine: The deployment engine
        num_gpus: Number of GPUs
        num_replicas: Number of replicas

    Raises:
        ValidationError: If the parameters don't match the expected schema
    """
    try:
        # Let Pydantic handle all validation
        _ = SnippetRequest(
            model_id=model_id,
            platform_id=platform_id,
            engine=engine,
            num_gpus=num_gpus,
            num_replicas=num_replicas,
        )
    except ValueError as e:
        # Simply convert to our custom ValidationError while preserving the original error
        # This maintains a consistent error hierarchy without losing Pydantic's detailed info
        raise ValidationError(str(e), original_error=e)


def _validate_model_id_format(model_id):
    """
    Validate that the model ID follows the expected format.

    Args:
        model_id: The model ID to validate

    Returns:
        tuple: (creator_name, model_name)

    Raises:
        ValidationError: If the model ID format is invalid
    """
    try:
        creator_name, model_name = model_id.split("/")
        return creator_name, model_name
    except ValueError:
        raise ValidationError(
            f"Invalid model_id format: {model_id}. Expected format: 'organization/model_name'"
        )


def _validate_model_platform_compatibility(client, model_id, platform_id, num_gpus):
    """
    Validate that the model and platform combination is valid and the GPU configuration is supported.

    Args:
        client: The Dell AI client
        model_id: The model ID
        platform_id: The platform SKU ID
        num_gpus: The number of GPUs to use

    Raises:
        ValidationError: If the platform is not supported or the GPU configuration is invalid
        ResourceNotFoundError: If the model is not found
    """
    model = models.get_model(client, model_id)

    # Check if the platform is supported
    if platform_id not in model.configs_deploy:
        supported_platforms = list(model.configs_deploy.keys())
        platform_list = ", ".join(supported_platforms)
        raise ValidationError(
            f"Platform {platform_id} is not supported for model {model_id}. Supported platforms: {platform_list}",
            parameter="platform_id",
            valid_values=supported_platforms,
        )

    # Validate the GPU configuration
    valid_configs = model.configs_deploy[platform_id]
    valid_gpus = {config.num_gpus for config in valid_configs}

    if num_gpus not in valid_gpus:
        gpu_list = ", ".join(str(g) for g in sorted(valid_gpus))
        raise ValidationError(
            f"Invalid number of GPUs ({num_gpus}) for model {model_id} on platform {platform_id}. Valid GPU counts: {gpu_list}",
            parameter="num_gpus",
            valid_values=sorted(valid_gpus),
            config_details={
                "model_id": model_id,
                "platform_id": platform_id,
                "valid_configs": valid_configs,
            },
        )


def _handle_resource_not_found(client, e, model_id, platform_id, num_gpus):
    """
    Handle ResourceNotFoundError by providing more specific error messages.

    Args:
        client: The Dell AI client
        e: The original ResourceNotFoundError
        model_id: The model ID
        platform_id: The platform SKU ID
        num_gpus: The number of GPUs

    Raises:
        ResourceNotFoundError: With a more specific error message
        ValidationError: If the configuration is invalid
    """
    # If the error is about the model, provide a specific error
    if e.resource_type.lower() == "models":
        raise ResourceNotFoundError("model", model_id)

    # If we can get the model details, check if this might be a configuration issue
    try:
        model = models.get_model(client, model_id)

        # Check if platform is valid but GPU config is invalid
        if platform_id in model.configs_deploy:
            valid_configs = model.configs_deploy[platform_id]
            valid_gpus = {config.num_gpus for config in valid_configs}

            if num_gpus not in valid_gpus:
                gpu_list = ", ".join(str(g) for g in sorted(valid_gpus))
                raise ValidationError(
                    f"Invalid number of GPUs ({num_gpus}) for model {model_id} on platform {platform_id}. Valid GPU counts: {gpu_list}",
                    parameter="num_gpus",
                    valid_values=sorted(valid_gpus),
                )
    except ResourceNotFoundError:
        # The model truly doesn't exist
        raise ResourceNotFoundError("model", model_id)

    # If we couldn't determine a more specific cause, re-raise the original error
    raise e


def get_deployment_snippet(
    client: DellAIClient,
    model_id: str,
    platform_id: str,
    engine: str,
    num_gpus: int,
    num_replicas: int,
) -> str:
    """
    Get a deployment snippet for the specified model and configuration.

    Args:
        client: The Dell AI client
        model_id: The model ID in the format "organization/model_name"
        platform_id: The platform SKU ID
        engine: The deployment engine ("docker" or "kubernetes")
        num_gpus: The number of GPUs to use
        num_replicas: The number of replicas to deploy

    Returns:
        A string containing the deployment snippet (docker command or k8s manifest)

    Raises:
        ValidationError: If any of the input parameters are invalid
        ResourceNotFoundError: If the model, platform, or configuration is not found
        GatedRepoAccessError: If the model repository is gated and the user doesn't have access
    """
    # Step 1: Validate basic request parameters
    _validate_request_schema(model_id, platform_id, engine, num_gpus, num_replicas)

    # Step 2: Parse and validate model ID format
    creator_name, model_name = _validate_model_id_format(model_id)

    # Step 3: Check if the user has access to the model repository
    # This will raise GatedRepoAccessError if the model is gated and the user doesn't have access
    client.check_model_access(model_id)

    # Step 4: Validate model and platform compatibility if the model exists
    try:
        _validate_model_platform_compatibility(client, model_id, platform_id, num_gpus)
    except ResourceNotFoundError:
        # We'll handle this during the API request
        pass

    # Step 5: Build API path and query parameters
    path = f"{constants.SNIPPETS_ENDPOINT}/models/{creator_name}/{model_name}/deploy"
    params = {
        "sku": platform_id,  # API still expects "sku" as the parameter name
        "container": engine,
        "replicas": num_replicas,
        "gpus": num_gpus,
    }

    # Step 6: Make API request and handle errors
    try:
        response = client._make_request("GET", path, params=params)
        return SnippetResponse(snippet=response.get("snippet", "")).snippet
    except ResourceNotFoundError as e:
        _handle_resource_not_found(client, e, model_id, platform_id, num_gpus)
