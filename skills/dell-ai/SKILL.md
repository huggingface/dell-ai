---
name: dell-ai
description: Skill for interacting with Dell Enterprise Hub (DEH) - discovering models, exploring hardware platforms, generating deployment snippets, etc.
---

# Dell AI

Use the `dell-ai` SDK and CLI to discover models, platforms, and apps on the Dell Enterprise Hub (DEH) and to deploy them locally.

## Quick start

Install: `uv pip install dell-ai`

Authenticate and create a client:

```python
from dell_ai import DellAIClient
client = DellAIClient()                 # uses cached Hugging Face token
client = DellAIClient(token="...")      # or pass explicitly
```

## When to use

- Find/list models and platforms on DEH.
- Generate Docker/Kubernetes/Helm deployment snippets.
- Run deployments on the local node.
- Check status or tear down deployments.
- Manage `dell-ai` environment variables.
- Check system compatibility.

## Core API

### Models

- `client.list_models(query=, multimodal=, min_size=, max_size=, license_filter=, platform_id=)` -> `List[str]`
- `client.search_models(...)` -> full `Model` objects
- `client.get_model(model_id)` -> `Model`
- `client.get_compatible_platforms(model_id)` -> `List[PlatformCompatibility]`
- `client.check_model_access(model_id)` -> `True` or raises
- `client.get_container_tags(model_id, platform_id)` -> `List[ContainerTag]`
- `client.get_goodput_scenarios()` -> `GoodputReference`

### Platforms

- `client.list_platforms()` -> `List[str]`
- `client.get_platform(platform_id)` -> `Platform`
- `client.get_platform_system_info(platform_id)` -> `List[SystemInfo]`

### Applications

- `client.list_apps()` -> `List[str]`
- `client.get_app(app_id)` -> `App`
- `client.get_app_snippet(app_id, config=[{"helmPath": ..., "type": "string|boolean|number|json", "value": ...}])` -> Helm install command

### Snippets and deployment

`get_deployment_snippet` and `deploy_model` require **exactly one** of `num_gpus` or `goodput`.

```python
# Manual sizing
snippet = client.get_deployment_snippet(
    model_id="...",
    platform_id="xe9680-nvidia-h200",
    engine="docker",      # or "kubernetes"
    num_gpus=8,
    num_replicas=1,
    image_tag="vllm-v0.11.2",  # optional; from get_container_tags
)

# Goodput-optimized
snippet = client.get_deployment_snippet(
    model_id="...",
    platform_id="xe9680-nvidia-h200",
    engine="docker",
    goodput="balanced",   # balanced | long-context | high-concurrency | performance
)
```

### Local deploy / undeploy / status

- `client.deploy_model(..., detach=True, local_dir="...", hf_cache_dir="...")` returns `{"success": ..., "endpoint": ..., "container_id": ...}`
- `client.deploy_app(app_id, config=[...])`
- `dell-ai models undeploy -d <deployment_id>`
- `dell-ai status [--clean]`

Registry helpers:

```python
from dell_ai import deployments
deployments.list_deployments()
deployments.get_deployment(id)
deployments.delete_deployment(id)
```

### Environment variables

- `dell-ai env set VAR value [--global]`
- `dell-ai env get VAR`
- `dell-ai env list [--local|--global]`
- `dell-ai env delete VAR [--global]`

Or use `from dell_ai import env` for SDK equivalents.

### System utilities (Linux CLI)

- `dell-ai utils describe-system [-o out.json]`
- `dell-ai utils check-system`

## Exceptions

All in `dell_ai.exceptions`: `AuthenticationError`, `GatedRepoAccessError`, `ResourceNotFoundError`, `ValidationError`, `APIError`.

## Tips

- Prefer `get_deployment_snippet` unless the user explicitly asks to run locally.
- For `deploy_model`, runtime failures return `{"success": False, "error": ...}`; bad params still raise.
- `local_dir` and `hf_cache_dir` are mutually exclusive on `deploy_model`.
- Container `image_tag` values come from `get_container_tags`.
- Run `dell-ai status` before `dell-ai models undeploy -d <id>`.
- For full details, see `README.md` and `docs/` in this repo or run `dell-ai --help`.
