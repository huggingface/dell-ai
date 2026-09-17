# Dell AI SDK and CLI

[![Version](https://img.shields.io/badge/version-1.1.0-orange)](https://github.com/huggingface/dell-ai)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Versions](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)

A Python SDK and CLI for interacting with the Dell Enterprise Hub (DEH), allowing users to programmatically browse available AI models, view platform configurations, generate deployment snippets or run DEH models and apps on Dell systems.

## Features

- Browse available AI models and apps
- View platform configurations
- Generate deployment snippets for running AI models on Dell hardware
- Size deployments for a goodput scenario (e.g. `balanced`) and let the server pick the optimal configuration, instead of choosing a GPU count by hand
- Inspect goodput scenario definitions and per-SKU SLO targets
- Deploy models and applications directly onto the local node, with automatic host port and GPU management
- Track, discover, and tear down local deployments through a deployment registry
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

# List the container image tags available for a model on a platform
dell-ai models list-tags --model-id meta-llama/Llama-4-Maverick-17B-128E-Instruct --platform-id xe9680-nvidia-h200

# Pin one of those tags in the snippet
dell-ai models get-snippet --model-id meta-llama/Llama-4-Maverick-17B-128E-Instruct --platform-id xe9680-nvidia-h200 --engine docker --gpus 8 --image-tag vllm-v0.11.2
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
    num_replicas=1,
    image_tag="vllm-v0.11.2",  # optional; pin a specific container image tag
)
print(snippet)

# Inspect the container image tags available for a model on a platform
tags = client.get_container_tags(
    model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
    platform_id="xe9680-nvidia-h200",
)
print([tag.id for tag in tags])
```

## Deploying models and applications

In addition to generating snippets, `dell-ai` can execute them directly on the
local node, so the code you get from the Dell Enterprise Hub is deployed for you.
Deployment uses the locally available engine: `docker` (Docker CLI), `kubernetes`
(`kubectl apply`), or Helm for applications.

By default deployments run in detached/background mode. For Docker, the
interactive flags (`-it`) are automatically converted to detached mode (`-d`),
the container ID is captured, and the inferred endpoint URL is recorded.

For Docker deployments, `dell-ai` also manages host resources automatically: if
the snippet's host port is already in use it is remapped to a free port, and free
GPU indices are allocated and pinned to the container.

On a successful deployment the metadata (endpoint, engine, container ID or
Kubernetes deployment name, and any assigned GPUs) is recorded in the
**deployment registry** so it can later be inspected with `dell-ai status` and
torn down with `dell-ai models undeploy`. See
[Deployment registry](#deployment-registry).

### Using the CLI

```bash
# Deploy a model with Docker (runs in the background by default)
dell-ai models deploy --model-id meta-llama/Llama-4-Maverick-17B-128E-Instruct --platform-id xe9680-nvidia-h200 --engine docker --gpus 8 --replicas 1

# Deploy a model with Kubernetes
dell-ai models deploy -m meta-llama/Llama-4-Maverick-17B-128E-Instruct -p xe9680-nvidia-h200 -e kubernetes -g 8 -r 1

# Run in the foreground instead of detached mode
dell-ai models deploy -m meta-llama/Llama-4-Maverick-17B-128E-Instruct -p xe9680-nvidia-h200 -e docker --no-detach

# Deploy optimized for a goodput scenario instead of a fixed GPU count (mutually exclusive with --gpus)
dell-ai models deploy -m meta-llama/Llama-4-Maverick-17B-128E-Instruct -p xe9680-nvidia-h200 -e docker --goodput balanced

# Mount local model weights instead of downloading from the Hub (Docker only)
dell-ai models deploy -m meta-llama/Llama-4-Maverick-17B-128E-Instruct -p xe9680-nvidia-h200 -e docker --gpus 8 --local-dir /data/my-model
# Or reuse an existing HuggingFace cache directory (mutually exclusive with --local-dir)
dell-ai models deploy -m meta-llama/Llama-4-Maverick-17B-128E-Instruct -p xe9680-nvidia-h200 -e docker --gpus 8 --hf-cache-dir ~/.cache/huggingface

# Deploy an application (Helm)
dell-ai apps deploy openwebui --config '{"config":[{"helmPath":"main.config.storageClassName","type":"string","value":"custom-storage-class"}]}'

# Stop and remove a deployment (Docker container / K8s deployment) and its registry entry.
# The ID is the "Deployment ID" shown by `dell-ai status` (see note on duplicates below).
dell-ai models undeploy -d meta-llama/Llama-4-Maverick-17B-128E-Instruct
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
    num_gpus=8,          # or use goodput="balanced" instead of num_gpus
    num_replicas=1,
    detach=True,
    # local_dir="/data/my-model",          # mount local weights (Docker only)
    # hf_cache_dir="~/.cache/huggingface",  # or reuse an existing HF cache
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

## Optimized Configurations

Instead of picking GPU count and deployment args by hand, `dell-ai` and **Dell Enterprise Hub** offer optimized configurations for a snippet or deployment for a set of **goodput scenarios**.

Goodput scenarios are named workload profiles (e.g. `balanced`) with an
associated set of Service Level Objectives (SLOs). When you pass `--goodput`
(CLI) or `goodput=` (SDK), DEH offers the optimal configuration for that
scenario on the target platform.

> [!NOTE]
> Check out the [Goodput Scenarios documentation](https://dell.huggingface.co/docs/optimized-deployments/goodput-scenarios) on DEH to learn more.

The available scenarios, the SLO field descriptions, and the SLO *targets* per
SKU come from global reference data (`dell-ai models goodput-scenarios`).

### Using the CLI

```bash
# List the available goodput scenarios and SLO field descriptions
dell-ai models goodput-scenarios --format table

# Drill into the SLO targets for a single SKU (scenario x SLO-field grid)
dell-ai models goodput-scenarios --platform-id xe9680-nvidia-h100 --format table

# Generate a snippet optimized for a scenario instead of a fixed GPU count
dell-ai models get-snippet -m google/gemma-3-27b-it -p xe9680-nvidia-h100 --engine docker --goodput balanced

# Deploy optimized for a scenario (mutually exclusive with --gpus)
dell-ai models deploy -m google/gemma-3-27b-it -p xe9680-nvidia-h100 --engine docker --goodput balanced
```

> [!NOTE]
> `--goodput`/`goodput` and `--gpus`/`num_gpus`
> are **mutually exclusive** — provide exactly one.

### Using the SDK

```python
from dell_ai.client import DellAIClient

client = DellAIClient()

# Get the global goodput reference data (scenarios, SLO docs, SLO targets per SKU)
reference = client.get_goodput_scenarios()
for scenario in reference.scenarios:
    print(scenario.id, "-", scenario.label)

# Inspect the SLO targets for a specific SKU
slos = reference.slos_by_platform_id.get("xe9680-nvidia-h100", {})
print({scenario: slo.model_dump() for scenario, slo in slos.items()})

# Generate a snippet optimized for a scenario (omit num_gpus)
snippet = client.get_deployment_snippet(
    model_id="google/gemma-3-27b-it",
    platform_id="xe9680-nvidia-h100",
    engine="docker",
    goodput="balanced",  # mutually exclusive with num_gpus
    num_replicas=1,
)
print(snippet)

# Deploy optimized for a scenario
result = client.deploy_model(
    model_id="google/gemma-3-27b-it",
    platform_id="xe9680-nvidia-h100",
    engine="docker",
    goodput="balanced",  # mutually exclusive with num_gpus
    num_replicas=1,
    detach=True,
)
print(result["success"], result.get("endpoint"))
```

## Deployment registry

Successful deployments are recorded in a **deployment registry** so they can be
listed, inspected, and torn down later. The registry has two scopes:

- **Local** — `.dell-ai-deployments.json` in the current working directory
- **Global** — `~/.config/dell-ai/deployments.json` (user-wide)

Each entry is keyed by a **deployment ID** and stores the endpoint, engine,
container ID or Kubernetes deployment name, assigned GPUs, and a timestamp. When
listing deployments (e.g. via `dell-ai status`), running Dell Enterprise Hub
Docker containers that are not yet tracked are **auto-discovered** and added, and
registry entries whose Docker containers are no longer running are pruned
automatically.

The deployment ID defaults to the model ID. If the **same model is deployed more
than once**, each additional instance gets a numeric suffix (e.g.
`meta-llama/Llama-4`, `meta-llama/Llama-4_1`, …) so they can coexist — each
instance is automatically given its own host port and GPU indices.

Use `dell-ai models undeploy -d <deployment_id>` to stop the underlying container
or Kubernetes deployment and remove its registry entry. Undeploy acts on **one
deployment at a time**: with duplicate instances, run `dell-ai status` first to
see the suffixed IDs, then undeploy each one individually.

## Environment variables

`dell-ai` can store configuration as environment variables in two scopes:

- **Local** — stored in `.dell-ai-env.json` in the current working directory
- **Global** — stored in `~/.config/dell-ai/env.json` (user-wide)

Variables are loaded automatically into the process environment on CLI startup
and when a `DellAIClient` is created. When resolving a variable, precedence is:
the active shell environment, then local, then global. This is useful for
recording checkpoint paths (`DELL_AI_CHECKPOINT`, which `dell-ai status` reports
on) and any other settings your deployments rely on.

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

- **Active deployments** — reads the [deployment registry](#deployment-registry),
  probes each recorded endpoint, and reports whether it is online and its
  response time (running Dell Enterprise Hub containers are auto-discovered)
- **Checkpoints** — checks whether paths in `DELL_AI_CHECKPOINT` (or any
  `*_CHECKPOINT` variable) exist, and reports their type and size
- **Active Docker/K8s** — scans the local Docker daemon and Kubernetes cluster
  for running Dell Enterprise Hub deployments

```bash
dell-ai status

# Also remove exited Docker containers and stopped Kubernetes deployments
dell-ai status --clean
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
