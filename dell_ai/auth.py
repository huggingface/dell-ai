"""Authentication functionality for the Dell AI SDK."""

import os
from typing import Optional

from huggingface_hub.utils import HfFolder

from dell_ai.exceptions import AuthenticationError


def get_token() -> Optional[str]:
    """
    Get the Hugging Face token from the environment or the Hugging Face token cache.

    Returns:
        The Hugging Face token if available, None otherwise
    """
    # First try from environment variable
    token = os.environ.get("HF_TOKEN")
    if token:
        return token

    # Then try from the Hugging Face token cache
    token = HfFolder().get_token()
    return token


def login(token: str) -> None:
    """
    Log in with a Hugging Face token.

    Args:
        token: The Hugging Face token to use for authentication

    Raises:
        AuthenticationError: If login fails
    """
    try:
        HfFolder().save_token(token)
    except Exception as e:
        raise AuthenticationError(f"Failed to save token: {str(e)}")


def logout() -> None:
    """
    Log out and remove the stored token.
    """
    HfFolder().delete_token()


def is_logged_in() -> bool:
    """
    Check if the user is logged in.

    Returns:
        True if the user is logged in, False otherwise
    """
    token = get_token()
    return token is not None
