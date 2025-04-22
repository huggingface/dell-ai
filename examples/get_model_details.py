#!/usr/bin/env python3
"""
Example script demonstrating how to get detailed information about a specific model.

This script shows how to:
1. Initialize the Dell AI client
2. Get detailed information about a specific model
3. Display model configuration and deployment options
4. Handle potential errors
"""

import sys
from dell_ai import DellAIClient
from dell_ai.exceptions import DellAIError, ResourceNotFoundError


def main():
    if len(sys.argv) != 2:
        print("Usage: python get_model_details.py <model_id>")
        print("Example: python get_model_details.py dell/llama2-7b")
        return

    model_id = sys.argv[1]

    try:
        # Initialize the client
        client = DellAIClient()

        # Get detailed model information
        model_info = client.get_model(model_id)

        print(f"\nDetailed Information for Model: {model_id}")
        print("=" * 50)
        print(f"Description: {model_info.get('description', 'N/A')}")
        print(f"License: {model_info.get('license', 'N/A')}")
        print(f"Creator Type: {model_info.get('creatorType', 'N/A')}")
        print(f"Size: {model_info.get('size', 'N/A')} bytes")
        print(f"Has System Prompt: {model_info.get('hasSystemPrompt', 'N/A')}")
        print(f"Is Multimodal: {model_info.get('isMultimodal', 'N/A')}")
        print(f"Status: {model_info.get('status', 'N/A')}")

        # Display deployment configurations
        print("\nDeployment Configurations:")
        print("-" * 30)
        configs = model_info.get("configsDeploy", {})
        for platform, config_list in configs.items():
            print(f"\nPlatform: {platform}")
            for config in config_list:
                print(
                    f"  - Max Batch Prefill Tokens: {config.get('max_batch_prefill_tokens', 'N/A')}"
                )
                print(f"  - Max Input Tokens: {config.get('max_input_tokens', 'N/A')}")
                print(f"  - Max Total Tokens: {config.get('max_total_tokens', 'N/A')}")
                print(f"  - Number of GPUs: {config.get('num_gpus', 'N/A')}")
                print("  " + "-" * 20)

    except ResourceNotFoundError:
        print(f"Model '{model_id}' not found")
    except DellAIError as e:
        print(f"Error getting model details: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
