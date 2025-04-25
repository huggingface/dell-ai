# Dell AI SDK and CLI

[![Version](https://img.shields.io/badge/version-0.0.1--pre--release-orange)](https://github.com/huggingface/dell-ai)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Versions](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)

A Python SDK and CLI for interacting with the Dell Enterprise Hub (DEH), allowing users to programmatically browse available AI models, view platform configurations, and generate deployment snippets for running AI models on Dell systems.

> [!WARNING]
> This library is intended to be used with the Dell Enterprise Hub on Dell instances,
> and is subject to changes before the 0.1.0 release!

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
```

### Using uv (recommended)

uv is a fast, reliable Python package installer and resolver. To install with uv:

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dell-ai package
uv sync
source .venv/bin/activate
```

### Using pip

You can also install the package using pip:

```bash
# Create and activate a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate

# Install the package in development mode
pip install -e .
```

## Quick Start

For detailed, guided examples of using the Dell AI SDK and CLI, check out the example documents in the `examples` directory:
- `examples/sdk-getting-started.ipynb`: A comprehensive walkthrough of the SDK features
- `examples/cli-getting-started.md`: A guide to using the CLI commands

### Using the CLI

```bash
# Authenticate with Hugging Face
dell-ai login

# List available models
dell-ai models list

# Get details about a specific model
dell-ai models show meta-llama/Llama-4-Maverick-17B-128E-Instruct

# List available platform SKUs
dell-ai platforms list

# Generate a Docker deployment snippet
dell-ai snippets get --model-id meta-llama/Llama-4-Maverick-17B-128E-Instruct --sku-id xe9680-nvidia-h200 --engine docker --gpus 8 --replicas 1
```

### Using the SDK

```python
from dell_ai.client import DellAIClient

# Initialize the client (authentication happens automatically if you've logged in via CLI)
client = DellAIClient()

# List available models
models = client.list_models()
print(models)

# Get model details
model_details = client.get_model_details(model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct")
print(model_details)

# List available platforms
platforms = client.list_platforms()
print(platforms)

# Get deployment snippet
snippet = client.get_deployment_snippet(
    model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
    sku_id="xe9680-nvidia-h200",
    engine="docker",
    num_gpus=8,
    num_replicas=1
)
print(snippet)
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

## License

Licensed under the Apache License, Version 2.0.