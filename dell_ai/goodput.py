"""Goodput scenario functionality for the Dell AI SDK.

Two pieces of data combine to describe a goodput-optimized deployment:

* The **reference data** (``GET /goodput-scenarios``): scenario definitions, SLO
  field docs, and the SLO *targets* per SKU. This is global and static, so it is
  cached on disk like model details.
* The **optimized configs** that actually meet those targets, which live on the
  catalog model object at ``configsDeploy.optimizedConfigPerSku`` (already
  fetched by :func:`dell_ai.models.get_model`).

:func:`get_optimized_configs` joins the two for a chosen ``(model, platform)``.
"""

import json
import time
from typing import TYPE_CHECKING, Dict, List, Optional

from pydantic import BaseModel, Field

from dell_ai import constants
from dell_ai.exceptions import ValidationError
from dell_ai.models import ModelConfig, get_model

if TYPE_CHECKING:
    from dell_ai.client import DellAIClient

# A single fixed cache key: the reference data is global, not per-resource.
_GOODPUT_CACHE_KEY = "goodput-scenarios"


class Scenario(BaseModel):
    """A goodput scenario definition (e.g. balanced, high-concurrency)."""

    model_config = {"extra": "ignore"}

    id: str
    label: str = ""
    description: str = ""


class Slo(BaseModel):
    """
    SLO targets for a (SKU, scenario) pair.
    """

    model_config = {
        "extra": "allow",
        "validate_by_alias": True,
        "validate_by_name": True,
    }

    max_model_context: Optional[int] = Field(default=None, alias="maxModelContext")
    virtual_users: Optional[int] = Field(default=None, alias="virtualUsers")
    # Token ranges are ``[min, max]`` tuples.
    input_tokens: Optional[List[int]] = Field(default=None, alias="inputTokens")
    output_tokens: Optional[List[int]] = Field(default=None, alias="outputTokens")


class GoodputReference(BaseModel):
    """Global goodput reference data returned by ``GET /goodput-scenarios``."""

    model_config = {
        "extra": "ignore",
        "validate_by_alias": True,
        "validate_by_name": True,
    }

    scenarios: List[Scenario] = Field(default_factory=list)
    slo_field_descriptions: Dict[str, str] = Field(
        default_factory=dict, alias="sloFieldDescriptions"
    )
    # Sparse: keyed by SkuId, then scenario id. SKUs without documented SLOs
    # (e.g. AMD/Intel platforms) are omitted entirely.
    slos_by_sku: Dict[str, Dict[str, Slo]] = Field(
        default_factory=dict, alias="slosBySku"
    )


class OptimizedConfig(BaseModel):
    """An optimized deploy config for one scenario, joined with its SLO target."""

    scenario: str = Field(description="Scenario id, e.g. 'balanced'")
    config: ModelConfig = Field(description="The goodput-optimized deploy config")
    slo: Optional[Slo] = Field(
        default=None,
        description="Target SLO for this SKU/scenario, if documented",
    )


def _get_goodput_cache_path():
    """Return the on-disk cache file path for the goodput reference data."""
    return constants.GOODPUT_CACHE_DIR / f"{_GOODPUT_CACHE_KEY}.json"


def _read_cached_reference() -> Optional[GoodputReference]:
    """Read fresh cached reference data, if present and not expired."""
    cache_path = _get_goodput_cache_path()
    try:
        with cache_path.open("r", encoding="utf-8") as cache_file:
            cached = json.load(cache_file)

        retrieved_at = cached.get("retrieved_at")
        reference_data = cached.get("reference")
        if not isinstance(retrieved_at, (int, float)) or not isinstance(
            reference_data, dict
        ):
            return None
        if time.time() - retrieved_at > constants.GOODPUT_CACHE_TTL_SECONDS:
            return None

        return GoodputReference.model_validate(reference_data)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _write_cached_reference(reference_data: Dict) -> None:
    """Write the goodput reference data to the on-disk cache (best-effort)."""
    cache_path = _get_goodput_cache_path()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"retrieved_at": time.time(), "reference": reference_data}
        temp_path = cache_path.with_suffix(".json.tmp")
        with temp_path.open("w", encoding="utf-8") as cache_file:
            json.dump(payload, cache_file)
        temp_path.replace(cache_path)
    except OSError:
        # Cache writes are best-effort; API data should still be returned.
        return


def get_goodput_scenarios(client: "DellAIClient") -> GoodputReference:
    """
    Get the global goodput reference data (scenarios, SLO docs, SLO targets).

    This data is static per the API spec, so it is cached on disk and reused
    until the cache entry expires.

    Args:
        client: The Dell AI client

    Returns:
        A GoodputReference object

    Raises:
        AuthenticationError: If authentication fails
        APIError: If the API returns an error
    """
    cached_reference = _read_cached_reference()
    if cached_reference is not None:
        return cached_reference

    response = client._make_request("GET", constants.GOODPUT_SCENARIOS_ENDPOINT)
    reference = GoodputReference.model_validate(response)
    _write_cached_reference(reference.model_dump(by_alias=True))
    return reference


def get_optimized_configs(
    client: "DellAIClient",
    model_id: str,
    platform_id: str,
    scenario: Optional[str] = None,
) -> List[OptimizedConfig]:
    """
    Get goodput-optimized deploy configs for a model on a platform.

    Joins the optimized configs on the model (``optimizedConfigPerSku``) with the
    SLO targets from the goodput reference data. By default returns every
    scenario documented for the platform; pass ``scenario`` to narrow to one.

    Args:
        client: The Dell AI client
        model_id: The model ID in the format "organization/model_name"
        platform_id: The platform SKU ID
        scenario: Optional scenario id to filter to (e.g. "balanced")

    Returns:
        A list of OptimizedConfig objects, one per matching scenario

    Raises:
        ValidationError: If the platform has no optimized configs for this model,
            or the requested scenario is not available for it
        ResourceNotFoundError: If the model is not found
        AuthenticationError: If authentication fails
        APIError: If the API returns an error
    """
    model = get_model(client, model_id)
    sku_configs = model.configs_deploy.optimized_config_per_sku.get(platform_id)

    if not sku_configs:
        supported = sorted(model.configs_deploy.optimized_config_per_sku.keys())
        platform_list = ", ".join(supported) if supported else "none"
        raise ValidationError(
            f"No goodput-optimized configs for model {model_id} on platform "
            f"{platform_id}. Platforms with optimized configs: {platform_list}",
            parameter="platform_id",
            valid_values=supported,
        )

    if scenario is not None and scenario not in sku_configs:
        available = sorted(sku_configs.keys())
        scenario_list = ", ".join(available)
        raise ValidationError(
            f"Scenario '{scenario}' is not available for model {model_id} on "
            f"platform {platform_id}. Available scenarios: {scenario_list}",
            parameter="scenario",
            valid_values=available,
        )

    reference = get_goodput_scenarios(client)
    slos = reference.slos_by_sku.get(platform_id, {})

    results: List[OptimizedConfig] = []
    for scenario_id, config in sku_configs.items():
        if scenario is not None and scenario_id != scenario:
            continue
        results.append(
            OptimizedConfig(
                scenario=scenario_id,
                config=config,
                slo=slos.get(scenario_id),
            )
        )

    return results
