"""Platform-related functionality for the Dell AI SDK."""

from typing import Dict, List, Any

from dell_ai import constants
from dell_ai.client import DellAIClient


def list_platforms(client: DellAIClient) -> List[str]:
    """
    Get a list of all available platform SKU IDs.

    Args:
        client: The Dell AI client

    Returns:
        A list of platform SKU IDs
    """
    response = client._make_request("GET", constants.PLATFORMS_ENDPOINT)
    return response.get("platforms", [])


def get_platform(client: DellAIClient, sku_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific platform.

    Args:
        client: The Dell AI client
        sku_id: The platform SKU ID

    Returns:
        Detailed platform information
    """
    endpoint = f"{constants.PLATFORMS_ENDPOINT}/{sku_id}"
    return client._make_request("GET", endpoint)
