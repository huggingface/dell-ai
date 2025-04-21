# Dell AI SDK and CLI

A Python SDK and CLI for interacting with the Dell Enterprise Hub (DEH), allowing users to programmatically browse available AI models, view platform configurations, and generate deployment snippets for running AI models on Dell hardware.

## Features

- Browse available AI models
- View platform configurations
- Generate deployment snippets for running AI models on Dell hardware
- Simple and easy-to-use API
- Consistent CLI commands

## Installation

```bash
pip install dell-ai
```

Or with uv:

```bash
uv pip install dell-ai
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

## CLI Usage

```bash
# Authenticate
dell-ai auth login

# List models
dell-ai models list

# Generate deployment snippet
dell-ai snippets get organization/model_name platform_sku --container docker --gpus 4 --replicas 1
```

## License

Licensed under the MIT License.
