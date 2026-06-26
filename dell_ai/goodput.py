"""Goodput scenario reference data for the Dell AI SDK.

:func:`get_goodput_scenarios` returns the global reference data
(``GET /goodput-scenarios``): scenario definitions, SLO field docs, and the SLO
*targets* per SKU. This is global and static, so it is cached on disk like model
details.

To generate a snippet optimized for a goodput scenario, pass ``goodput`` to
:func:`dell_ai.models.get_deployment_snippet`; the server handles the sizing.
"""

import json
import time
from typing import TYPE_CHECKING, Dict, List, Optional

from pydantic import BaseModel, Field

from dell_ai import constants

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
