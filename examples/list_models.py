#!/usr/bin/env python3
"""
Example script demonstrating how to list available models using the Dell AI SDK.

This script shows how to:
1. Initialize the Dell AI client
2. List all available models
3. Display model information in a formatted way
4. Handle potential errors
"""

from dell_ai import DellAIClient
from dell_ai.exceptions import DellAIError


def main():
    try:
        # Initialize the client
        client = DellAIClient()

        # Get list of available models
        models = client.list_models()

        if not models:
            print("No models found")
            return

        print("\nAvailable Models:")
        print("-" * 50)
        for model_id in models:
            # Get detailed information for each model
            model_info = client.get_model(model_id)
            print(f"Model ID: {model_id}")
            print(f"Description: {model_info.get('description', 'N/A')}")
            print(f"License: {model_info.get('license', 'N/A')}")
            print(f"Status: {model_info.get('status', 'N/A')}")
            print("-" * 50)

    except DellAIError as e:
        print(f"Error listing models: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
