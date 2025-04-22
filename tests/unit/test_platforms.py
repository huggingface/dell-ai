import pytest
from unittest.mock import MagicMock
from dell_ai.platforms import Platform, list_platforms, get_platform
from dell_ai.exceptions import DellAIError, ResourceNotFoundError

# Mock API responses
MOCK_PLATFORMS_LIST = ["dell-xe9640", "dell-xe9640-8gpu", "dell-xe9640-16gpu"]

MOCK_PLATFORM_DETAILS = {
    "id": "dell-xe9640",
    "name": "Dell XE9640",
    "disabled": False,
    "server": "PowerEdge XE9640",
    "vendor": "Dell",
    "gputype": "NVIDIA H100",
    "gpuram": "80GB",
    "gpuinterconnect": "NVLink",
    "productName": "PowerEdge XE9640",
    "totalgpucount": 8,
    "interonnect_east_west": "NVLink",
    "interconnect_north_south": "PCIe",
}


@pytest.fixture
def mock_client():
    client = MagicMock()
    return client


def test_list_platforms_success(mock_client):
    """Test successful retrieval of platform list"""
    mock_client._make_request.return_value = {"platforms": MOCK_PLATFORMS_LIST}

    result = list_platforms(mock_client)

    assert result == MOCK_PLATFORMS_LIST
    mock_client._make_request.assert_called_once()


def test_list_platforms_error(mock_client):
    """Test error handling in list_platforms"""
    mock_client._make_request.side_effect = DellAIError("API Error")

    with pytest.raises(DellAIError):
        list_platforms(mock_client)


def test_get_platform_success(mock_client):
    """Test successful retrieval of platform details"""
    mock_client._make_request.return_value = MOCK_PLATFORM_DETAILS

    result = get_platform(mock_client, "dell-xe9640")

    assert isinstance(result, Platform)
    assert result.id == "dell-xe9640"
    assert result.name == "Dell XE9640"
    assert result.totalgpucount == 8
    mock_client._make_request.assert_called_once()


def test_get_platform_not_found(mock_client):
    """Test handling of non-existent platform"""
    mock_client._make_request.side_effect = ResourceNotFoundError(
        "platform", "nonexistent-platform"
    )

    with pytest.raises(ResourceNotFoundError):
        get_platform(mock_client, "nonexistent-platform")


def test_platform_validation():
    """Test Platform Pydantic model validation"""
    # Test valid platform data
    platform = Platform(**MOCK_PLATFORM_DETAILS)
    assert platform.id == "dell-xe9640"
    assert platform.totalgpucount == 8

    # Test invalid platform data
    invalid_data = MOCK_PLATFORM_DETAILS.copy()
    invalid_data["totalgpucount"] = (
        "not a number"  # Changed to invalid type instead of negative number
    )

    with pytest.raises(ValueError):
        Platform(**invalid_data)

    # Test missing required field
    invalid_data = MOCK_PLATFORM_DETAILS.copy()
    del invalid_data["id"]

    with pytest.raises(ValueError):
        Platform(**invalid_data)
