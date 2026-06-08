---
name: dell-ai
description: Skill for interacting with Dell Enterprise Hub (DEH) - discovering models, exploring hardware platforms, generating deployment snippets, etc.
---

# Dell AI

dell-ai interacts with the Dell Enterprise Hub (DEH) — discovering models, exploring hardware platforms, generating deployment snippets, managing app catalog entries, checking system compatibility, etc.

## When to use

- User wants to find AI models available on Dell Enterprise Hub
- User wants to find AI models available on DEH for their hardware platform
- User needs to check which Dell hardware platforms support a given model
- User wants to generate Docker or Kubernetes deployment commands for a model and then run it.
- User wants to explore or deploy applications from the Dell app catalog
- User needs to check system compatibility with Dell AI platforms
- User asks about Dell AI, Dell Enterprise Hub, or DEH
- User wants to authenticate with Dell AI using a Hugging Face token
- User wants to check their system info or check system compatibility against Dell AI validated configs

## Installation

```bash
uv pip install dell-ai
```

## Authentication

Uses a Hugging Face token. Auto-loads from HF token cache, or accepts one directly.

```python
from dell_ai import DellAIClient

client = DellAIClient()                        # Uses cached HF token
client = DellAIClient(token="your_hf_token")   # Or explicit token

client.is_authenticated()  # Returns bool
client.get_user_info()     # Returns dict with name, email, orgs, etc.
```

## Models

### Search and list models

`list_models` returns `List[str]` of IDs. `search_models` accepts the same filters but returns full `Model` objects.

```python
# List model IDs (all filters are optional and combinable)
models = client.list_models(
    query="llama",                    # Search name/description
    multimodal=True,                  # True for multimodal, False for text-only
    min_size=7000,                    # Min params in millions
    max_size=70000,                   # Max params in millions
    license_filter="apache",          # License substring match
    platform_id="xe9680-nvidia-h200", # Only models compatible with this platform
)

# Full Model objects with same filters
results = client.search_models(query="llama", multimodal=True)
# Model fields: repo_name, description, license, size, is_multimodal,
#               has_system_prompt, creator_type, status, configs_deploy
```

### Get model details and compatible platforms

```python
# Returns Model object
model = client.get_model("meta-llama/Llama-4-Maverick-17B-128E-Instruct")

platforms = client.get_compatible_platforms("google/gemma-3-27b-it")
# Returns List[PlatformCompatibility] with platform_id and configs (List[ModelConfig])
for p in platforms:
    print(p.platform_id, [c.model_dump() for c in p.configs])
```

### Check model access (gated repos)

```python
# Returns True, or raises GatedRepoAccessError / AuthenticationError
client.check_model_access("meta-llama/Llama-4-Maverick-17B-128E-Instruct")
```

### Get model Deployment Snippets

Automatically validates model access and model-platform compatibility.

```python
snippet = client.get_deployment_snippet(
    model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
    platform_id="xe9680-nvidia-h200",
    engine="docker",       # "docker" or "kubernetes"
    num_gpus=8,
    num_replicas=1,
)
print(snippet)  # Ready-to-use docker command or k8s manifest
```

## Platforms

```python
platforms = client.list_platforms()  # Returns List[str] of SKU IDs

platform = client.get_platform("xe9680-nvidia-h200")
# Fields: id, name, platform_type, vendor, accelerator_type, accelerator,
#   gpuram, gpuinterconnect, totalgpucount, product_name

sys_infos = client.get_platform_system_info("xe9680-nvidia-h200")  # List[SystemInfo]
```

## Applications

### List and inspect apps

```python
apps = client.list_apps()  # Returns List[str] of app names

app = client.get_app("openwebui")
# App fields: id, name, license, description, features, instructions,
#   tags, recommendedModels, components
```

### Explore configurable parameters

```python
for component in app.components:
    for param in component.config:
        print(f"  {param.name}: {param.helmPath} ({param.type}), default={param.default}")
    for secret in component.secrets:
        print(f"  [secret] {secret.name}: {secret.helmPath}")
```

### Generate app deployment snippet

Each config item requires: `helmPath`, `type` (`"string"`, `"boolean"`, `"number"`, or `"json"`), and `value`.

```python
config = [
    {"helmPath": "main.config.storageClassName", "type": "string", "value": "gp2"},
    {"helmPath": "main.config.enableOpenAI", "type": "boolean", "value": True},
]
snippet = client.get_app_snippet("openwebui", config)
print(snippet)  # Helm install command
```

## System Utilities (CLI only, Linux)

```bash
dell-ai utils describe-system              # Get system info as JSON
dell-ai utils describe-system -o out.json  # Save to file
dell-ai utils describe-system | jq         # Pretty-print
dell-ai utils check-system                 # Check compatibility against Dell AI validated configs
```

Requires: `lscpu`, `lspci`, `lsblk`, `dmidecode`. For GPUs: `nvidia-smi`, `nvidia-ctk`. For K8s: `kubectl`.

## Exceptions

All in `dell_ai.exceptions`:
- `AuthenticationError` — Invalid or missing token
- `GatedRepoAccessError` — No access to a gated model repository
- `ResourceNotFoundError` — Model, platform, or app not found
- `ValidationError` — Invalid parameters (may include `valid_values`)
- `APIError` — General API errors
