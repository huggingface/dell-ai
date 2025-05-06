"""Model-related functionality for the Dell AI SDK."""

from typing import Dict, List, TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from dell_ai import constants
from dell_ai.exceptions import ResourceNotFoundError, ValidationError

if TYPE_CHECKING:
    from dell_ai.client import DellAIClient


class ModelConfig(BaseModel):
    """Configuration details for a model deployment."""

    max_batch_prefill_tokens: Optional[int] = None
    max_input_tokens: Optional[int] = None
    max_total_tokens: Optional[int] = None
    num_gpus: int

    model_config = {
        "extra": "allow",  # Allow extra fields not defined in the model
    }


class Model(BaseModel):
    """Represents a model available in the Dell Enterprise Hub."""

    repo_name: str = Field(alias="repoName")
    description: str = ""
    license: str = ""
    creator_type: str = Field(default="", alias="creatorType")
    size: int = Field(default=0, description="Number of model parameters (in millions)")
    has_system_prompt: bool = Field(default=False, alias="hasSystemPrompt")
    is_multimodal: bool = Field(default=False, alias="isMultimodal")
    status: str = ""
    configs_deploy: Dict[str, List[ModelConfig]] = Field(
        default_factory=dict, alias="configsDeploy"
    )

    class Config:
        """Pydantic model configuration.

        The 'populate_by_name' setting allows the model to be populated using either:
        1. The Pythonic snake_case attribute names (e.g., repo_name, configs_deploy)
        2. The original camelCase names from the API (e.g., repoName, configsDeploy)

        This provides compatibility with the API response format while maintaining
        Pythonic naming conventions in our codebase.
        """

        populate_by_name = True


def list_models(client: "DellAIClient") -> List[str]:
    """
    Get a list of all available model IDs.

    Args:
        client: The Dell AI client

    Returns:
        A list of model IDs in the format "organization/model_name"

    Raises:
        AuthenticationError: If authentication fails
        APIError: If the API returns an error
    """
    response = client._make_request("GET", constants.MODELS_ENDPOINT)
    return response.get("models", [])


def get_model(client: "DellAIClient", model_id: str) -> Model:
    """
    Get detailed information about a specific model.

    Args:
        client: The Dell AI client
        model_id: The model ID in the format "organization/model_name"

    Returns:
        Detailed model information as a Model object

    Raises:
        ValidationError: If the model_id format is invalid
        ResourceNotFoundError: If the model is not found
        AuthenticationError: If authentication fails
        APIError: If the API returns an error
    """
    # Validate model_id format
    if "/" not in model_id:
        raise ValidationError(
            "Invalid model ID format. Expected format: 'organization/model_name'",
            parameter="model_id",
        )

    try:
        endpoint = f"{constants.MODELS_ENDPOINT}/{model_id}"
        response = client._make_request("GET", endpoint)

        # Process configsDeploy to convert nested dictionaries to ModelConfig objects
        if "configsDeploy" in response and response["configsDeploy"]:
            for platform, configs in response["configsDeploy"].items():
                response["configsDeploy"][platform] = [
                    ModelConfig.model_validate(config) for config in configs
                ]

        # Create a Model object from the response
        return Model.model_validate(response)
    except ResourceNotFoundError:
        # Reraise with more specific information
        raise ResourceNotFoundError("model", model_id)
