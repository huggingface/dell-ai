import json
import time
from unittest.mock import MagicMock

import pytest

from dell_ai import constants
from dell_ai.goodput import GoodputReference, get_goodput_scenarios

# Mock API responses

MOCK_GOODPUT_REFERENCE = {
    "scenarios": [
        {"id": "balanced", "label": "Balanced", "description": "A balanced config."},
        {
            "id": "high-concurrency",
            "label": "High concurrency",
            "description": "Many users.",
        },
        {"id": "long-context", "label": "Long context", "description": "Big context."},
    ],
    "sloFieldDescriptions": {
        "maxModelContext": "Max context length (tokens).",
        "virtualUsers": "Number of concurrent users.",
        "inputTokens": "Input-token range sampled per request.",
        "outputTokens": "Output-token range sampled per request.",
    },
    "slosBySku": {
        "xe9680-nvidia-h100": {
            "balanced": {
                "maxModelContext": 8192,
                "virtualUsers": 128,
                "inputTokens": [64, 4096],
                "outputTokens": [64, 1024],
            },
            "high-concurrency": {
                "maxModelContext": 4096,
                "virtualUsers": 256,
                "inputTokens": [64, 2048],
                "outputTokens": [64, 512],
            },
        }
    },
}


@pytest.fixture
def mock_client(tmp_path, monkeypatch):
    """Fixture that provides a mock Dell AI client with an isolated cache."""
    monkeypatch.setattr(constants, "GOODPUT_CACHE_DIR", tmp_path / "goodput")
    constants.GOODPUT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return MagicMock()


# get_goodput_scenarios tests


def test_get_goodput_scenarios(mock_client):
    """Reference data parses into a GoodputReference object."""
    mock_client._make_request.return_value = MOCK_GOODPUT_REFERENCE
    reference = get_goodput_scenarios(mock_client)

    assert isinstance(reference, GoodputReference)
    assert len(reference.scenarios) == 3
    assert reference.scenarios[0].id == "balanced"
    assert reference.scenarios[0].label == "Balanced"
    assert "maxModelContext" in reference.slo_field_descriptions

    slo = reference.slos_by_sku["xe9680-nvidia-h100"]["balanced"]
    assert slo.max_model_context == 8192
    assert slo.virtual_users == 128
    assert slo.input_tokens == [64, 4096]
    assert slo.output_tokens == [64, 1024]

    mock_client._make_request.assert_called_once_with("GET", "/goodput-scenarios")


def test_get_goodput_scenarios_uses_fresh_file_cache(mock_client):
    """A fresh cache entry is reused without an API call."""
    cache_path = constants.GOODPUT_CACHE_DIR / "goodput-scenarios.json"
    cache_path.write_text(
        json.dumps({"retrieved_at": time.time(), "reference": MOCK_GOODPUT_REFERENCE}),
        encoding="utf-8",
    )

    reference = get_goodput_scenarios(mock_client)

    assert len(reference.scenarios) == 3
    mock_client._make_request.assert_not_called()


def test_get_goodput_scenarios_refreshes_expired_cache(mock_client, monkeypatch):
    """An expired cache entry is ignored and refetched."""
    monkeypatch.setattr(constants, "GOODPUT_CACHE_TTL_SECONDS", 60)
    cache_path = constants.GOODPUT_CACHE_DIR / "goodput-scenarios.json"
    cache_path.write_text(
        json.dumps(
            {
                "retrieved_at": time.time() - 120,
                "reference": {**MOCK_GOODPUT_REFERENCE, "scenarios": []},
            }
        ),
        encoding="utf-8",
    )
    mock_client._make_request.return_value = MOCK_GOODPUT_REFERENCE

    reference = get_goodput_scenarios(mock_client)

    assert len(reference.scenarios) == 3
    mock_client._make_request.assert_called_once_with("GET", "/goodput-scenarios")


def test_get_goodput_scenarios_writes_cache(mock_client):
    """A successful fetch populates the on-disk cache for reuse."""
    mock_client._make_request.return_value = MOCK_GOODPUT_REFERENCE

    get_goodput_scenarios(mock_client)
    get_goodput_scenarios(mock_client)

    # Second call should hit the cache, so only one network request total.
    mock_client._make_request.assert_called_once()
