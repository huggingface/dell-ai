"""Dell AI SDK for interacting with the Dell Enterprise Hub (DEH)."""

__version__ = "0.0.4"

# Import models and types for public API
# These are only imported when the user explicitly imports them,
# not when the package itself is imported
__all__ = ["Model", "ModelConfig", "Platform", "DellAIClient"]

# Import client for creating instances
from dell_ai.client import DellAIClient

# Forward references for type checking
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dell_ai.models import Model, ModelConfig
    from dell_ai.platforms import Platform
