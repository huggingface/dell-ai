"""Model-related functionality for the Dell AI SDK."""

from typing import Dict, List, Any

from dell_ai import constants
from dell_ai.client import DellAIClient


def list_models(client: DellAIClient) -> List[str]:
    """
    Get a list of all available model IDs.

    Args:
        client: The Dell AI client

    Returns:
        A list of model IDs in the format "organization/model_name"
    """
    response = client._make_request("GET", constants.MODELS_ENDPOINT)
    return response.get("models", [])


def get_model(client: DellAIClient, model_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific model.

    Args:
        client: The Dell AI client
        model_id: The model ID in the format "organization/model_name"

    Returns:
        Detailed model information including compatible platforms
    """
    endpoint = f"{constants.MODELS_ENDPOINT}/{model_id}"
    return client._make_request("GET", endpoint)
