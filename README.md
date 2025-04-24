# Dell AI SDK and CLI

A Python SDK and CLI for interacting with the Dell Enterprise Hub (DEH), allowing users to programmatically browse available AI models, view platform configurations, and generate deployment snippets for running AI models on Dell hardware.

## Features

- Browse available AI models
- View platform configurations
- Generate deployment snippets for running AI models on Dell hardware
- Simple and easy-to-use API
- Consistent CLI commands

## Installation

This package is not yet available on PyPI. To install:

```bash
# Clone the repository
git clone https://github.com/huggingface/dell-ai.git
cd dell-ai

### Using uv (recommended)

uv is a fast, reliable Python package installer and resolver. To install with uv:

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dell-ai package
uv sync
source .venv/bin/activate
```

## Quick Start

```python
from dell_ai.client import DellAIClient

# Initialize the client
client = DellAIClient()

# List available models
models = client.list_models()
print(models)

# Get deployment snippet
snippet = client.get_deployment_snippet(
    model_id="organization/model_name",
    sku_id="platform_sku",
    container_type="docker",
    num_gpus=4,
    num_replicas=1
)
print(snippet)
```

## Getting Started

The package includes several "getting started" examples to help you use the SDK and CLI effectively:

- Authentication with the Dell AI SDK
- Listing available models and their details
- Retrieving detailed information about specific models
- Listing available platforms and their configurations
- Generating deployment snippets for different configurations

## CLI Usage

```bash
# Authenticate
dell-ai auth login

# List models
dell-ai models list

# Generate deployment snippet
dell-ai snippets get organization/model_name platform_sku --container docker --gpus 4 --replicas 1
```

## Testing

The project uses pytest for testing. To run the tests:

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=dell_ai

# Run specific test file
pytest tests/unit/test_exceptions.py
```

The test suite includes:
- Unit tests for core components
- Integration tests for CLI and API interactions
- Custom test fixtures for mocking API responses

Test coverage reports are generated automatically and can be viewed in the terminal or exported to HTML.

## License

Licensed under the Apache License, Version 2.0.
