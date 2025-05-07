# Dell AI SDK and CLI

[![Version](https://img.shields.io/badge/version-0.0.4-orange)](https://github.com/huggingface/dell-ai)
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

We recommend installing the package using `uv`, a fast Rust-based Python package and project manager, after setting up a Python virtual environment:

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv .venv
source .venv/bin/activate

# Install dell-ai
uv pip install dell-ai
```

### Alternative: `pip`

You can also use `pip` to install the package:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dell-ai
pip install dell-ai
```

### Installing from Source

If you want to contribute to development or need the latest changes, you can install from source:

```bash
# Clone the repository
git clone https://github.com/huggingface/dell-ai.git
cd dell-ai

# Create and activate virtual environment (using either method above)
# Then install in development mode
pip install -e .  # or uv pip install -e .
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
dell-ai snippets get --model-id meta-llama/Llama-4-Maverick-17B-128E-Instruct --platform-id xe9680-nvidia-h200 --engine docker --gpus 8 --replicas 1
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
model_details = client.get_model(model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct")
print(model_details.model_dump())

# List available platforms
platforms = client.list_platforms()
print(platforms)

# Get platform details
platform_details = client.get_platform(platform_id="xe9680-nvidia-h200")
print(platform_details.model_dump())

# Get deployment snippet
snippet = client.get_deployment_snippet(
    model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
    platform_id="xe9680-nvidia-h200",
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