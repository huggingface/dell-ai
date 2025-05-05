"""Platform-related functionality for the Dell AI SDK."""

from typing import List, TYPE_CHECKING

from pydantic import BaseModel, Field

from dell_ai import constants
from dell_ai.exceptions import ResourceNotFoundError

if TYPE_CHECKING:
    from dell_ai.client import DellAIClient


class Platform(BaseModel):
    """Represents a platform available in the Dell Enterprise Hub."""

    id: str
    name: str
    disabled: bool
    server: str
    vendor: str
    gputype: str
    gpuram: str
    gpuinterconnect: str
    product_name: str = Field(alias="productName")
    totalgpucount: int
    interconnect_east_west: str = Field(alias="interonnect-east-west")
    interconnect_north_south: str = Field(alias="interconnect-north-south")

    class Config:
        """Pydantic model configuration.

        The 'populate_by_name' setting allows the model to be populated using either:
        1. The Pythonic snake_case attribute names (e.g., product_name)
        2. The original camelCase names from the API (e.g., productName)

        This provides compatibility with the API response format while maintaining
        Pythonic naming conventions in our codebase.
        """

        populate_by_name = True


def list_platforms(client: "DellAIClient") -> List[str]:
    """
    Get a list of all available platform SKU IDs.

    Args:
        client: The Dell AI client

    Returns:
        A list of platform SKU IDs

    Raises:
        AuthenticationError: If authentication fails
        APIError: If the API returns an error
    """
    response = client._make_request("GET", constants.PLATFORMS_ENDPOINT)
    return response.get("skus", [])


def get_platform(client: "DellAIClient", platform_id: str) -> Platform:
    """
    Get detailed information about a specific platform.

    Args:
        client: The Dell AI client
        platform_id: The platform SKU ID

    Returns:
        Detailed platform information as a Platform object

    Raises:
        ResourceNotFoundError: If the platform is not found
        AuthenticationError: If authentication fails
        APIError: If the API returns an error
    """
    try:
        endpoint = f"{constants.PLATFORMS_ENDPOINT}/{platform_id}"
        response = client._make_request("GET", endpoint)
        return Platform.model_validate(response)
    except ResourceNotFoundError:
        # Reraise with more specific information
        raise ResourceNotFoundError("platform", platform_id)
