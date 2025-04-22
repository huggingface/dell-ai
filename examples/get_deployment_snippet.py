#!/usr/bin/env python3
"""
Example script demonstrating how to generate deployment snippets using the Dell AI SDK.

This script shows how to:
1. Initialize the Dell AI client
2. Generate deployment snippets for different configurations
3. Display the generated snippets
4. Handle potential errors
"""

import sys
import argparse
from dell_ai import DellAIClient
from dell_ai.exceptions import DellAIError, ValidationError


def main():
    parser = argparse.ArgumentParser(
        description="Generate deployment snippet for a model"
    )
    parser.add_argument("model_id", help="Model ID (e.g., dell/llama2-7b)")
    parser.add_argument("sku_id", help="Platform SKU ID")
    parser.add_argument(
        "--container",
        choices=["docker", "kubernetes"],
        default="docker",
        help="Container type (default: docker)",
    )
    parser.add_argument(
        "--gpus", type=int, default=1, help="Number of GPUs to use (default: 1)"
    )
    parser.add_argument(
        "--replicas",
        type=int,
        default=1,
        help="Number of replicas to deploy (default: 1)",
    )

    args = parser.parse_args()

    try:
        # Initialize the client
        client = DellAIClient()

        # Generate the deployment snippet
        snippet = client.get_deployment_snippet(
            model_id=args.model_id,
            sku_id=args.sku_id,
            container_type=args.container,
            num_gpus=args.gpus,
            num_replicas=args.replicas,
        )

        print(f"\nDeployment Snippet for {args.model_id} on {args.sku_id}")
        print("=" * 80)
        print(snippet)

    except ValidationError as e:
        print(f"Invalid configuration: {e}")
    except DellAIError as e:
        print(f"Error generating deployment snippet: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
