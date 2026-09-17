# Dell AI MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes Dell Enterprise Hub (DEH) discovery, local deployment, and agent-skills management to MCP clients such as Claude Desktop, Cursor, OpenCode, and Codex.

## Overview

The Dell AI MCP server is built on the Python `mcp>=2.0.0,<2.1.0` SDK. The same server process serves both the prior MCP protocol era and the `2026-07-28` specification. It auto-negotiates the protocol with the client, so you can use a single server for legacy and modern MCP clients.

Top-level features:

- **Read-only catalog tools**: discover models, platforms, applications, container tags, goodput scenarios, and deployment snippets.
- **Destructive deployment tools**: deploy and undeploy models/apps on the local machine, gated by `allow_destructive`.
- **Skills management**: list, view, and install agent skills into assistant directories.
- **Resources**: address DEH entities and local state by URI (`deh://models/{+model_id}`, `deh://deployments`, `deh://skills`, ...).
- **Prompts**: guided workflows for deploying a model or application.

## Installation

The MCP server is an optional extra:

```bash
pip install "dell-ai[mcp]"
# or, if developing:
uv sync --extra mcp --extra dev
```

The CLI remains functional without the MCP dependencies.

## Configuration

Configuration is loaded from (in order of precedence):

1. `.dell-ai-mcp.json` in the current working directory
2. `~/.config/dell-ai/mcp.json` (global)
3. CLI flags and environment variables

The file schema is documented in `mcp/config/schema/mcp-config.schema.json`.

### Minimal stdio config

```json
{
  "transport": "stdio",
  "log_level": "INFO",
  "hf_token_source": "env:HF_TOKEN"
}
```

### Streamable-HTTP config

```json
{
  "transport": "streamable-http",
  "host": "0.0.0.0",
  "port": 3000,
  "stateless_http": true,
  "hf_token_source": "env:HF_TOKEN"
}
```

### Config options

| Key | Default | Description |
| --- | --- | --- |
| `transport` | `stdio` | `stdio`, `streamable-http`, or `sse` |
| `host` | `127.0.0.1` | HTTP server host |
| `port` | `8000` | HTTP server port |
| `stateless_http` | `true` | Stateless HTTP mode |
| `json_response` | `false` | Return tool results as JSON |
| `allow_destructive` | `false` | Register `deploy_*`, `undeploy`, and `install_skill` tools |
| `log_level` | `INFO` | Server log level |
| `hf_token_source` | `null` | Where to read the Hugging Face token: `env:HF_TOKEN`, a path, `null` |
| `api_base_url` | `null` | Override DEH API base URL |
| `capabilities` | `{tools:true, resources:true, prompts:true}` | Toggle MCP capability advertisements |

## Running the server

Validate a config:

```bash
dell-ai mcp validate-config
```

Start the server with defaults:

```bash
dell-ai mcp start
```

Enable destructive tools:

```bash
dell-ai mcp start --allow-destructive
```

For HTTP transport:

```bash
dell-ai mcp start --config mcp/config/examples/streamable-http.json
```

## Client integration

### Claude Desktop (stdio)

Add to `~/.config/claude/config.json` or Claude Desktop settings:

```json
{
  "mcpServers": {
    "dell-ai": {
      "command": "dell-ai",
      "args": ["mcp", "start"]
    }
  }
}
```

To enable deployment tools, add `--allow-destructive` to `args` and ensure the config file sets `allow_destructive: true`.

### Cursor / OpenCode / Codex

Most clients accept the same `mcpServers` block. Use `--allow-destructive` only when the client should be allowed to deploy or undeploy on this machine.

## Capabilities

The server advertises three MCP capabilities: **tools**, **resources**, and **prompts**. Each can be disabled independently in the config. Destructive tools only appear when `allow_destructive` is `true`.

## Tools reference

### Read-only catalog tools

| Tool | Description |
| --- | --- |
| `list_models` | List available DEH models |
| `search_models` | Search models by query and filters |
| `get_model` | Get details for a model ID |
| `get_compatible_platforms` | Platforms compatible with a model |
| `list_platforms` | List available platforms |
| `get_platform` | Get platform details |
| `get_platform_system_info` | System info for a platform SKU |
| `check_model_access` | Check whether the local Hugging Face token can access a model |
| `get_deployment_snippet` | Generate a Docker/Kubernetes/Helm snippet |
| `get_container_tags` | List available container tags |
| `get_goodput_scenarios` | List goodput sizing scenarios |
| `list_apps` | List DEH applications |
| `get_app` | Get application details |
| `get_app_snippet` | Get an application install snippet |
| `list_deployments` | List active local deployments |
| `describe_system` | Describe local CPU/GPU/memory/OS |
| `list_skills` | List available agent skills |
| `get_skill` | Return the markdown content of a skill |

### Destructive deployment tools

Requires `allow_destructive: true`.

| Tool | Description |
| --- | --- |
| `deploy_model` | Deploy a DEH model locally (Docker/Kubernetes) |
| `deploy_app` | Deploy a DEH application locally |
| `undeploy` | Stop and remove a local deployment by ID |
| `install_skill` | Symlink a skill into assistant skill directories (Codex/Claude/Cursor/OpenCode) |

`undeploy` handles Docker containers and Kubernetes deployments. Helm releases are not automatically uninstalled; the tool reports the manual `helm uninstall <release>` command if it sees an `engine: helm` deployment.

## Resources reference

Access data via `resources/read` URIs:

| URI | Returns |
| --- | --- |
| `deh://models/{+model_id}` | Model JSON (`model_id` may contain `/`) |
| `deh://platforms/{platform_id}` | Platform JSON |
| `deh://apps/{app_id}` | Application JSON |
| `deh://deployments` | Active local deployment registry |
| `deh://system` | Local CPU, memory, GPU, and OS info |
| `deh://skills` | List of available skills |
| `deh://skills/{name}` | Markdown source of a skill |

Static resources have no URI variables. Templates with `{+...}` accept multi-segment values.

## Prompts reference

| Prompt | Purpose |
| --- | --- |
| `deploy_model` | Guide a user through deploying a model |
| `deploy_app` | Guide a user through deploying an application |

## Security notes

- Keep `allow_destructive` disabled unless the connected client is trusted and the operator accepts local deployment changes.
- The Hugging Face token is resolved from `hf_token_source` at runtime and is never logged.
- `install_skill` creates symlinks into assistant-specific skill directories. It does not copy secrets.

## Examples

See `mcp/config/examples/` for config and client JSON snippets.

- `mcp/config/examples/stdio.json`
- `mcp/config/examples/streamable-http.json`
- `mcp/config/examples/client-claude-desktop-stdio.json`
- `mcp/config/examples/client-claude-desktop-http.json`

## Troubleshooting

- **Tools not showing up**: Ensure `capabilities.tools` is `true` in the config.
- **Deployment tools missing**: Ensure `allow_destructive` is `true` and restart the client.
- **Hugging Face access errors**: Verify `HF_TOKEN` is exported or `hf_token_source` points to a file containing it.
- **Skills install fails**: The `install_skill` tool requires at least one assistant flag (`codex`, `claude`, `cursor`, or `opencode`) or `is_global: true`.

## Development

Unit tests for the MCP server live in `tests/unit/test_mcp_server.py`. Run them with:

```bash
uv run pytest tests/unit/test_mcp_server.py -v
```

Lint with:

```bash
uv run ruff check dell_ai/mcp
```
