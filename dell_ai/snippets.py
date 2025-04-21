"""Snippet generation functionality for the Dell AI SDK."""

from dell_ai import constants
from dell_ai.client import DellAIClient
from dell_ai.exceptions import ValidationError


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
        ValidationError: If the container type is invalid
    """
    # Validate container type
    if container_type.lower() not in ["docker", "kubernetes"]:
        raise ValidationError(
            f"Invalid container type: {container_type}. "
            "Valid types are: docker, kubernetes"
        )

    # Build request data
    data = {
        "model_id": model_id,
        "sku_id": sku_id,
        "container_type": container_type.lower(),
        "num_gpus": num_gpus,
        "num_replicas": num_replicas,
    }

    # Make API request
    response = client._make_request("POST", constants.SNIPPETS_ENDPOINT, data=data)

    return response.get("snippet", "")
