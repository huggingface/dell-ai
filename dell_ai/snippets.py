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


def _validate_request_schema(model_id, sku_id, container_type, num_gpus, num_replicas):
    """
    Validate the basic schema of the request parameters.

    Args:
        model_id: The model ID
        sku_id: The platform SKU ID
        container_type: The container type
        num_gpus: Number of GPUs
        num_replicas: Number of replicas

    Raises:
        ValidationError: If the parameters don't match the expected schema
    """
    try:
        _ = SnippetRequest(
            model_id=model_id,
            sku_id=sku_id,
            container_type=container_type,
            num_gpus=num_gpus,
            num_replicas=num_replicas,
        )
    except ValueError as e:
        # Convert Pydantic validation errors to our custom ValidationError
        error_msg = str(e)
        if "container_type" in error_msg and "Invalid container type" in error_msg:
            raise ValidationError(
                "Invalid container type",
                parameter="container_type",
                valid_values=["docker", "kubernetes"],
            )
        elif "num_gpus" in error_msg:
            raise ValidationError(
                "Number of GPUs must be greater than 0", parameter="num_gpus"
            )
        elif "num_replicas" in error_msg:
            raise ValidationError(
                "Number of replicas must be greater than 0", parameter="num_replicas"
            )
        else:
            # Pass through other validation errors
            raise ValidationError(str(e))


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


def _validate_model_platform_compatibility(client, model_id, sku_id, num_gpus):
    """
    Validate that the model and platform combination is valid and the GPU configuration is supported.

    Args:
        client: The Dell AI client
        model_id: The model ID
        sku_id: The platform SKU ID
        num_gpus: The number of GPUs to use

    Raises:
        ValidationError: If the platform is not supported or the GPU configuration is invalid
        ResourceNotFoundError: If the model is not found
    """
    model = models.get_model(client, model_id)

    # Check if the platform is supported
    if sku_id not in model.configs_deploy:
        supported_platforms = list(model.configs_deploy.keys())
        raise ValidationError(
            f"Platform {sku_id} is not supported for model {model_id}",
            parameter="sku_id",
            valid_values=supported_platforms,
            config_details=None,  # Don't include empty configs as they cause confusing output
        )

    # Validate the GPU configuration
    valid_configs = model.configs_deploy[sku_id]
    valid_gpus = {config.num_gpus for config in valid_configs}

    if num_gpus not in valid_gpus:
        raise ValidationError(
            f"Invalid number of GPUs ({num_gpus}) for model {model_id} on platform {sku_id}",
            parameter="num_gpus",
            valid_values=sorted(valid_gpus),
            config_details={
                "model_id": model_id,
                "platform_id": sku_id,
                "valid_configs": valid_configs,
            },
        )


def _handle_resource_not_found(client, e, model_id, sku_id, num_gpus):
    """
    Handle ResourceNotFoundError by providing more specific error messages.

    Args:
        client: The Dell AI client
        e: The original ResourceNotFoundError
        model_id: The model ID
        sku_id: The platform SKU ID
        num_gpus: The number of GPUs

    Raises:
        ResourceNotFoundError: With a more specific error message
        ValidationError: If the configuration is invalid
    """
    # If we reach here and the error is about the model, provide a better error message
    if e.resource_type.lower() == "models":
        raise ResourceNotFoundError("model", model_id)

    # If we reach here and the model exists but API returns 404,
    # it's likely due to an invalid configuration
    # Try to provide a more helpful error message
    try:
        model = models.get_model(client, model_id)
        if sku_id in model.configs_deploy:
            valid_configs = model.configs_deploy[sku_id]
            valid_gpus = {config.num_gpus for config in valid_configs}
            if num_gpus not in valid_gpus:
                raise ValidationError(
                    f"Invalid number of GPUs ({num_gpus}) for model {model_id} on platform {sku_id}",
                    parameter="num_gpus",
                    valid_values=sorted(valid_gpus),
                    config_details={
                        "model_id": model_id,
                        "platform_id": sku_id,
                        "valid_configs": valid_configs,
                    },
                )
    except ResourceNotFoundError:
        # Model truly doesn't exist
        raise ResourceNotFoundError("model", model_id)

    # Re-raise the original error if we couldn't determine a more specific cause
    raise


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
        ResourceNotFoundError: If the model, platform, or configuration is not found
    """
    # Step 1: Validate basic request parameters
    _validate_request_schema(model_id, sku_id, container_type, num_gpus, num_replicas)

    # Step 2: Parse and validate model ID format
    creator_name, model_name = _validate_model_id_format(model_id)

    # Step 3: Validate model and platform compatibility if the model exists
    try:
        _validate_model_platform_compatibility(client, model_id, sku_id, num_gpus)
    except ResourceNotFoundError:
        # Model not found - let the API handle this
        pass

    # Step 4: Build API path and query parameters
    path = f"{constants.SNIPPETS_ENDPOINT}/models/{creator_name}/{model_name}/deploy"
    params = {
        "sku": sku_id,
        "container": container_type,
        "replicas": num_replicas,
        "gpus": num_gpus,
    }

    # Step 5: Make API request and handle errors
    try:
        # Make API request
        response = client._make_request("GET", path, params=params)
        # Parse and validate response
        return SnippetResponse(snippet=response.get("snippet", "")).snippet
    except ResourceNotFoundError as e:
        _handle_resource_not_found(client, e, model_id, sku_id, num_gpus)
