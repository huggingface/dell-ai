"""Authentication functionality for the Dell AI SDK."""

import os
from typing import Optional, Dict, Any

from huggingface_hub import login as hf_login, logout as hf_logout, whoami
from huggingface_hub.utils import get_token as hf_get_token

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

    # Then try from the Hugging Face token cache using native method
    return hf_get_token()


def login(token: str) -> None:
    """
    Log in with a Hugging Face token.

    Args:
        token: The Hugging Face token to use for authentication

    Raises:
        AuthenticationError: If login fails or token is invalid
    """
    try:
        # Use native login method which also validates the token
        hf_login(token=token)
    except Exception as e:
        raise AuthenticationError(f"Failed to login: {str(e)}")


def logout() -> None:
    """
    Log out and remove the stored token.
    """
    hf_logout()


def is_logged_in() -> bool:
    """
    Check if the user is logged in.

    Returns:
        True if the user is logged in, False otherwise
    """
    token = get_token()
    return token is not None


def validate_token(token: str) -> bool:
    """
    Validate a Hugging Face token by making a test API call.

    Args:
        token: The Hugging Face token to validate

    Returns:
        True if the token is valid, False otherwise
    """
    try:
        # Use whoami to validate the token
        whoami(token=token)
        return True
    except Exception:
        return False


def get_user_info(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Get information about the authenticated user.

    Args:
        token: The Hugging Face token to use. If not provided, will use the
               token from get_token().

    Returns:
        A dictionary with user information

    Raises:
        AuthenticationError: If authentication fails or no token is available
    """
    token = token or get_token()
    if not token:
        raise AuthenticationError("No authentication token found. Please login first.")

    try:
        return whoami(token=token)
    except Exception as e:
        raise AuthenticationError(f"Failed to get user information: {str(e)}")
