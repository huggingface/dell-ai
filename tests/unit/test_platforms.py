import pytest
from unittest.mock import MagicMock
from dell_ai.platforms import Platform, list_platforms, get_platform
from dell_ai.exceptions import ResourceNotFoundError

# Mock API responses
MOCK_PLATFORMS_LIST = [
    "xe9680-nvidia-h200",
    "xe9680-nvidia-h100",
    "xe9680-amd-mi300x",
    "xe9680-intel-gaudi3",
    "xe8640-nvidia-h100",
    "r760xa-nvidia-h100",
    "r760xa-nvidia-l40s",
]

MOCK_PLATFORM_DETAILS = {
    "id": "xe9680-nvidia-h100",
    "name": "XE9680 Nvidia H100",
    "disabled": False,
    "server": "xe9680",
    "vendor": "Nvidia",
    "gputype": "H100",
    "gpuram": "80G",
    "gpuinterconnect": "sxm",
    "product_name": "NVIDIA-H100-80GB-HBM3",
    "totalgpucount": 8,
    "interconnect_east_west": "IB",
    "interconnect_north_south": "ETH",
}


@pytest.fixture
def mock_client():
    """Fixture that provides a mock Dell AI client."""
    return MagicMock()


def test_list_platforms(mock_client):
    """Test that list_platforms returns the correct list of platform IDs."""
    mock_client._make_request.return_value = {"skus": MOCK_PLATFORMS_LIST}
    result = list_platforms(mock_client)
    assert result == MOCK_PLATFORMS_LIST
    mock_client._make_request.assert_called_once()


def test_get_platform(mock_client):
    """Test that get_platform returns a properly constructed Platform object."""
    mock_client._make_request.return_value = MOCK_PLATFORM_DETAILS
    platform = get_platform(mock_client, "xe9680-nvidia-h100")

    assert isinstance(platform, Platform)
    assert platform.id == "xe9680-nvidia-h100"
    assert platform.name == "XE9680 Nvidia H100"
    assert platform.server == "xe9680"
    assert platform.vendor == "Nvidia"
    assert platform.gputype == "H100"
    assert platform.gpuram == "80G"
    assert platform.gpuinterconnect == "sxm"
    assert platform.product_name == "NVIDIA-H100-80GB-HBM3"
    assert platform.totalgpucount == 8
    assert platform.interconnect_east_west == "IB"
    assert platform.interconnect_north_south == "ETH"


def test_get_platform_not_found(mock_client):
    """Test that get_platform raises ResourceNotFoundError for non-existent platforms."""
    mock_client._make_request.side_effect = ResourceNotFoundError(
        "platform", "nonexistent-platform"
    )
    with pytest.raises(ResourceNotFoundError):
        get_platform(mock_client, "nonexistent-platform")


def test_platform_validation():
    """Test that Platform validation works correctly for both valid and invalid data."""
    # Test valid platform data
    platform = Platform(**MOCK_PLATFORM_DETAILS)
    assert platform.id == "xe9680-nvidia-h100"

    # Test invalid platform data
    with pytest.raises(ValueError):
        Platform(**{**MOCK_PLATFORM_DETAILS, "totalgpucount": "not a number"})

    # Test missing required field
    with pytest.raises(ValueError):
        Platform(**{k: v for k, v in MOCK_PLATFORM_DETAILS.items() if k != "id"})
