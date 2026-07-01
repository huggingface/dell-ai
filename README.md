# Dell AI SDK and CLI

[![Version](https://img.shields.io/badge/version-0.1.6-orange)](https://github.com/huggingface/dell-ai)
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
- Deploy models and applications directly onto the local node
- Manage local and global environment variables
- Check the status of deployed endpoints, checkpoints, and active deployments
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
dell-ai models get-snippet --model-id meta-llama/Llama-4-Maverick-17B-128E-Instruct --platform-id xe9680-nvidia-h200 --engine docker --gpus 8 --replicas 1
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

## Deploying models and applications

In addition to generating snippets, `dell-ai` can execute them directly on the
local node, so the code you get from the Dell Enterprise Hub is deployed for you.
Deployment uses the locally available engine: `docker` (Docker CLI), `kubernetes`
(`kubectl apply`), or Helm for applications.

By default deployments run in detached/background mode. For Docker, the
interactive flags (`-it`) are automatically converted to detached mode (`-d`),
the container ID is captured, and the inferred endpoint URL is recorded.

On a successful deployment the following environment variables are saved to the
**local** scope (see [Environment variables](#environment-variables)) so they can
later be inspected with `dell-ai status`:

- `DELL_AI_ENDPOINT` — the inferred endpoint URL (e.g. `http://localhost:80`)
- `DELL_AI_LAST_DEPLOYED_ENGINE` — `docker`, `kubernetes`, or `helm`
- `DELL_AI_LAST_DEPLOYED_CONTAINER` — Docker container ID (Docker only)
- `DELL_AI_LAST_DEPLOYED_K8S_DEPLOYMENT` — deployment name (Kubernetes only)

### Using the CLI

```bash
# Deploy a model with Docker (runs in the background by default)
dell-ai models deploy --model-id meta-llama/Llama-4-Maverick-17B-128E-Instruct --platform-id xe9680-nvidia-h200 --engine docker --gpus 8 --replicas 1

# Deploy a model with Kubernetes
dell-ai models deploy -m meta-llama/Llama-4-Maverick-17B-128E-Instruct -p xe9680-nvidia-h200 -e kubernetes -g 8 -r 1

# Run in the foreground instead of detached mode
dell-ai models deploy -m meta-llama/Llama-4-Maverick-17B-128E-Instruct -p xe9680-nvidia-h200 -e docker --no-detach

# Deploy an application (Helm)
dell-ai apps deploy openwebui --config '{"config":[{"helmPath":"main.config.storageClassName","type":"string","value":"custom-storage-class"}]}'
```

### Using the SDK

```python
from dell_ai.client import DellAIClient

client = DellAIClient()

# Deploy a model on the local node
result = client.deploy_model(
    model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
    platform_id="xe9680-nvidia-h200",
    engine="docker",
    num_gpus=8,
    num_replicas=1,
    detach=True,
)
print(result["success"], result.get("container_id"), result.get("endpoint"))

# Deploy an application on the local node
result = client.deploy_app(app_id="openwebui", config=[], detach=True)
print(result["success"])
```

> [!NOTE]
> Deployment executes the snippet returned by the Dell Enterprise Hub on the
> local machine, so it requires the relevant tooling (`docker`, `kubectl`, or
> `helm`) to be installed and configured.

## Environment variables

`dell-ai` can store configuration as environment variables in two scopes:

- **Local** — stored in `.dell-ai-env.json` in the current working directory
- **Global** — stored in `~/.config/dell-ai/env.json` (user-wide)

Variables are loaded automatically into the process environment on CLI startup
and when a `DellAIClient` is created. When resolving a variable, precedence is:
the active shell environment, then local, then global. This is useful for
recording endpoints (`DELL_AI_ENDPOINT`), checkpoint paths (`DELL_AI_CHECKPOINT`),
and other settings that `dell-ai status` can later report on.

### Using the CLI

```bash
# Set a variable locally (current directory) or globally (-g/--global)
dell-ai env set DELL_AI_ENDPOINT http://localhost:80
dell-ai env set DELL_AI_ENDPOINT http://localhost:80 --global

# Get a variable's value
dell-ai env get DELL_AI_ENDPOINT

# List variables (combined by default; --local or --global to scope)
dell-ai env list
dell-ai env list --local
dell-ai env list --global

# Delete a variable (from local, or --global)
dell-ai env delete DELL_AI_ENDPOINT
```

### Using the SDK

```python
from dell_ai import env

# Set / get / delete
env.set_env_var("DELL_AI_ENDPOINT", "http://localhost:80", is_global=False)
print(env.get_env_var("DELL_AI_ENDPOINT"))
env.delete_env_var("DELL_AI_ENDPOINT", is_global=False)

# List (is_global=None -> combined, True -> global only, False -> local only)
print(env.list_env_vars())
```

## Checking deployment status

`dell-ai status` inspects your environment and local node and reports on:

- **Model endpoints** — probes URLs stored in `DELL_AI_ENDPOINT` (or any
  `*_ENDPOINT` variable) and reports whether they are online and their response time
- **Checkpoints** — checks whether paths in `DELL_AI_CHECKPOINT` (or any
  `*_CHECKPOINT` variable) exist, and reports their type and size
- **Active deployments** — scans the local Docker daemon and Kubernetes cluster
  for running Dell Enterprise Hub deployments

```bash
dell-ai status
```

> [!NOTE]
> Docker and Kubernetes scanning are skipped gracefully if `docker` or `kubectl`
> are not available on the node.

## Testing

The project uses pytest for testing. To run the tests:

```bash
# Check code formatting
ruff format --check .

# Check linting and import sorting
ruff check .

# Format code
ruff format .

# Run all tests
pytest

# Run tests with coverage report
pytest --cov=dell_ai

# Run specific test file
pytest tests/unit/test_exceptions.py
```

## Contributing

Contributions are welcome! Please see [RELEASE_PROCESS.md](RELEASE_PROCESS.md) for information on how the release process works when contributing code changes.

When submitting a PR:
1. Ensure all tests pass
2. Add tests for new functionality
3. Follow the existing code style

## License

Licensed under the Apache License, Version 2.0.
