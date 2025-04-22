#!/usr/bin/env python3
"""
Example script demonstrating authentication with the Dell AI SDK.

This script shows how to:
1. Initialize the Dell AI client
2. Authenticate using a token
3. Check authentication status
4. Handle authentication errors
"""

from dell_ai import DellAIClient
from dell_ai.exceptions import AuthenticationError


def main():
    try:
        # Initialize the client without a token
        # It will attempt to use the cached Hugging Face token
        client = DellAIClient()

        # Check if we're authenticated
        if client.is_authenticated():
            print("Successfully authenticated using cached token")
        else:
            print("Not authenticated. Please run 'dell-ai auth login' first")
            return

        # Alternatively, you can initialize with a specific token
        # token = "your-token-here"
        # client = DellAIClient(token=token)

    except AuthenticationError as e:
        print(f"Authentication error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
