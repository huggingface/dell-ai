#!/usr/bin/env python3
"""
Example script demonstrating how to list available platforms using the Dell AI SDK.

This script shows how to:
1. Initialize the Dell AI client
2. List all available platforms
3. Display platform information in a formatted way
4. Handle potential errors
"""

from dell_ai import DellAIClient
from dell_ai.exceptions import DellAIError


def main():
    try:
        # Initialize the client
        client = DellAIClient()

        # Get list of available platforms
        platforms = client.list_platforms()

        if not platforms:
            print("No platforms found")
            return

        print("\nAvailable Platforms:")
        print("=" * 80)
        for sku_id in platforms:
            # Get detailed information for each platform
            platform_info = client.get_platform(sku_id)
            print(f"SKU ID: {sku_id}")
            print(f"Name: {platform_info.get('name', 'N/A')}")
            print(f"Server: {platform_info.get('server', 'N/A')}")
            print(f"Vendor: {platform_info.get('vendor', 'N/A')}")
            print(f"GPU Type: {platform_info.get('gputype', 'N/A')}")
            print(f"GPU RAM: {platform_info.get('gpuram', 'N/A')}")
            print(f"Total GPU Count: {platform_info.get('totalgpucount', 'N/A')}")
            print(f"Product Name: {platform_info.get('productName', 'N/A')}")
            print("-" * 80)

    except DellAIError as e:
        print(f"Error listing platforms: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
