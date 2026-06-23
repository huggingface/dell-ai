import json
import time
from unittest.mock import MagicMock

import pytest

from dell_ai import constants
from dell_ai.exceptions import ResourceNotFoundError, ValidationError
from dell_ai.goodput import (
    GoodputReference,
    OptimizedConfig,
    get_goodput_scenarios,
    get_optimized_configs,
)

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

MOCK_MODEL_WITH_OPTIMIZED = {
    "repo_name": "google/gemma-3-27b-it",
    "description": "Gemma model.",
    "license": "gemma",
    "creator_type": "org",
    "size": 27400,
    "has_system_prompt": True,
    "is_multimodal": True,
    "status": "new",
    "configsDeploy": {
        "containerTags": {},
        "configPerSku": {
            "xe9680-nvidia-h100": [{"num_gpus": 2}],
        },
        "optimizedConfigPerSku": {
            "xe9680-nvidia-h100": {
                "balanced": {
                    "backend": "vllm",
                    "num_gpus": 1,
                    "max_model_len": 8192,
                    "max_num_seqs": 256,
                    "gpu_memory_utilization": 0.9,
                },
                "high-concurrency": {
                    "backend": "vllm",
                    "num_gpus": 2,
                    "max_model_len": 4096,
                    "max_num_seqs": 512,
                },
            }
        },
    },
}

MOCK_MODEL_NO_OPTIMIZED = {
    "repo_name": "google/gemma-3-12b-it",
    "description": "Gemma model, no optimized configs.",
    "license": "gemma",
    "size": 12000,
    "status": "active",
    "configsDeploy": {
        "containerTags": {},
        "configPerSku": {"xe9680-nvidia-h100": [{"num_gpus": 1}]},
    },
}


@pytest.fixture
def mock_client(tmp_path, monkeypatch):
    """Fixture that provides a mock Dell AI client with isolated caches."""
    monkeypatch.setattr(constants, "MODEL_CACHE_DIR", tmp_path / "models")
    monkeypatch.setattr(constants, "GOODPUT_CACHE_DIR", tmp_path / "goodput")
    constants.MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
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
        json.dumps(
            {"retrieved_at": time.time(), "reference": MOCK_GOODPUT_REFERENCE}
        ),
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


# get_optimized_configs tests


def _dispatch_factory(model_details):
    """Route _make_request by endpoint to model details or goodput reference."""

    def _dispatch(method, endpoint, *args, **kwargs):
        if endpoint == "/goodput-scenarios":
            return MOCK_GOODPUT_REFERENCE
        if endpoint.startswith("/models/"):
            return model_details
        raise AssertionError(f"Unexpected endpoint: {endpoint}")

    return _dispatch


def test_get_optimized_configs_all_scenarios(mock_client):
    """All scenarios for a platform are returned and joined with their SLOs."""
    mock_client._make_request.side_effect = _dispatch_factory(
        MOCK_MODEL_WITH_OPTIMIZED
    )

    results = get_optimized_configs(
        mock_client, "google/gemma-3-27b-it", "xe9680-nvidia-h100"
    )

    assert len(results) == 2
    assert all(isinstance(r, OptimizedConfig) for r in results)

    by_scenario = {r.scenario: r for r in results}
    assert set(by_scenario) == {"balanced", "high-concurrency"}

    balanced = by_scenario["balanced"]
    assert balanced.config.num_gpus == 1
    assert balanced.config.max_model_len == 8192
    # SLO target joined from the reference data
    assert balanced.slo is not None
    assert balanced.slo.virtual_users == 128
    assert balanced.slo.input_tokens == [64, 4096]


def test_get_optimized_configs_single_scenario(mock_client):
    """The scenario filter narrows results to one entry."""
    mock_client._make_request.side_effect = _dispatch_factory(
        MOCK_MODEL_WITH_OPTIMIZED
    )

    results = get_optimized_configs(
        mock_client,
        "google/gemma-3-27b-it",
        "xe9680-nvidia-h100",
        scenario="balanced",
    )

    assert len(results) == 1
    assert results[0].scenario == "balanced"


def test_get_optimized_configs_no_slo_for_scenario(mock_client):
    """A scenario without a documented SLO still returns its config, slo=None."""
    model = json.loads(json.dumps(MOCK_MODEL_WITH_OPTIMIZED))
    model["configsDeploy"]["optimizedConfigPerSku"]["xe9680-nvidia-h100"][
        "long-context"
    ] = {"backend": "vllm", "num_gpus": 4, "max_model_len": 32768}
    mock_client._make_request.side_effect = _dispatch_factory(model)

    results = get_optimized_configs(
        mock_client,
        "google/gemma-3-27b-it",
        "xe9680-nvidia-h100",
        scenario="long-context",
    )

    assert len(results) == 1
    assert results[0].config.num_gpus == 4
    # No SLO documented for long-context on this SKU in the reference data.
    assert results[0].slo is None


def test_get_optimized_configs_platform_without_optimized(mock_client):
    """A platform with no optimized configs raises ValidationError."""
    mock_client._make_request.side_effect = _dispatch_factory(
        MOCK_MODEL_WITH_OPTIMIZED
    )

    with pytest.raises(ValidationError) as exc_info:
        get_optimized_configs(
            mock_client, "google/gemma-3-27b-it", "r760xa-nvidia-l40s"
        )

    assert exc_info.value.valid_values == ["xe9680-nvidia-h100"]


def test_get_optimized_configs_model_without_optimized(mock_client):
    """A model without any optimized configs raises ValidationError."""
    mock_client._make_request.side_effect = _dispatch_factory(MOCK_MODEL_NO_OPTIMIZED)

    with pytest.raises(ValidationError):
        get_optimized_configs(
            mock_client, "google/gemma-3-12b-it", "xe9680-nvidia-h100"
        )


def test_get_optimized_configs_unknown_scenario(mock_client):
    """Requesting a scenario the platform doesn't offer raises ValidationError."""
    mock_client._make_request.side_effect = _dispatch_factory(
        MOCK_MODEL_WITH_OPTIMIZED
    )

    with pytest.raises(ValidationError) as exc_info:
        get_optimized_configs(
            mock_client,
            "google/gemma-3-27b-it",
            "xe9680-nvidia-h100",
            scenario="performance",
        )

    assert exc_info.value.valid_values == ["balanced", "high-concurrency"]


def test_get_optimized_configs_model_not_found(mock_client):
    """A missing model propagates ResourceNotFoundError."""
    mock_client._make_request.side_effect = ResourceNotFoundError(
        "model", "google/nonexistent"
    )

    with pytest.raises(ResourceNotFoundError):
        get_optimized_configs(
            mock_client, "google/nonexistent", "xe9680-nvidia-h100"
        )
