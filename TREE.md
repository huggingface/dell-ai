# `dell-ai` Command Tree

A complete tree of the `dell-ai` CLI commands and their options/arguments.

Legend:
- `<arg>` — positional argument (required unless noted)
- `--option` — optional flag/option (default shown in `[...]` where applicable)
- Short aliases are shown after the long form (e.g. `--format, -f`)

```
dell-ai
├── --version, -v                         Show the application version and exit
├── --help                                Show help and exit
│
├── login                                 Log in to Dell AI using a Hugging Face token
│   └── --token <TOKEN>                    HF API token (prompted if omitted)
│
├── logout                                Log out and remove the stored token
│
├── whoami                                Show current authentication status and user info
│
├── status                                Check status of deployed endpoints, checkpoints,
│                                          and active Docker/Kubernetes deployments
│   └── --clean                            Remove exited Docker containers and stopped
│                                          K8s deployments
│
├── models                               Model commands
│   ├── list                              List all available models
│   │   └── --format, -f <json|table>     Output format [json]
│   │
│   ├── show <model_id>                   Show detailed info about a model
│   │
│   ├── search                            Search and filter available models
│   │   ├── --query, -q <TEXT>            Match against model name/description
│   │   ├── --multimodal                 Filter for multimodal (vs text-only) models
│   │   ├── --min-size <FLOAT>            Minimum size (millions of params)
│   │   ├── --max-size <FLOAT>            Maximum size (millions of params)
│   │   ├── --license, -l <TEXT>          Filter by license (substring match)
│   │   ├── --platform-id, -p <SKU>       Filter by supported platform SKU
│   │   ├── --format, -f <json|table>     Output format [json]
│   │   └── --detail, -d                  Show full model details (not just IDs)
│   │
│   ├── compatible-platforms <model_id>   Find platforms compatible with a model
│   │   └── --format, -f <json|table>     Output format [json]
│   │
│   ├── check-access <model_id>           Check access to a (gated) model repository
│   │
│   ├── list-tags                         List container image tags for a model/platform
│   │   ├── --model-id, -m <model_id>     Model ID (required)
│   │   ├── --platform-id, -p <SKU>       Platform SKU ID (required)
│   │   └── --format, -f <json|table>     Output format [json]
│   │
│   ├── goodput-scenarios                 Show global goodput scenario/SLO reference data
│   │   ├── --platform-id, -p <SKU>       Show SLO targets for a single SKU
│   │   └── --format, -f <json|table>     Output format [json]
│   │
│   ├── get-snippet                       Generate a deployment snippet for a model
│   │   ├── --model-id, -m <model_id>     Model ID (required)
│   │   ├── --platform-id, -p <SKU>       Platform SKU ID (required)
│   │   ├── --engine, -e <docker|kubernetes>  Deployment engine [docker]
│   │   ├── --gpus, -g <INT>              Number of GPUs (one of --gpus or --goodput)
│   │   ├── --replicas, -r <INT>          Number of replicas (min 1) [1]
│   │   ├── --goodput <SCENARIO>          Optimize snippet for a goodput scenario
│   │   ├── --image-tag <TAG>             Pin a container image tag
│   │   ├── --local-dir <PATH>            Mount local model weights (Docker only)
│   │   └── --hf-cache-dir <PATH>         Mount a HuggingFace cache dir (Docker only)
│   │
│   ├── deploy                            Deploy a model directly on the local node
│   │   ├── --model-id, -m <model_id>     Model ID (required)
│   │   ├── --platform-id, -p <SKU>       Platform SKU ID (required)
│   │   ├── --engine, -e <docker|kubernetes>  Deployment engine [docker]
│   │   ├── --gpus, -g <INT>              Number of GPUs (one of --gpus or --goodput)
│   │   ├── --replicas, -r <INT>          Number of replicas (min 1) [1]
│   │   ├── --goodput <SCENARIO>          Optimize deploy for a goodput scenario
│   │   ├── --image-tag <TAG>             Pin a container image tag
│   │   ├── --local-dir <PATH>            Mount local model weights (Docker only)
│   │   ├── --hf-cache-dir <PATH>         Mount a HuggingFace cache dir (Docker only)
│   │   └── --detach / --no-detach        Run in background (detached) mode [detach]
│   │
│   └── undeploy                          Stop and remove a deployed model
│       └── --deployment-id, -d <ID>      Deployment ID from `dell-ai status` (required)
│
├── platforms                            Platform commands
│   ├── list                              List all available platforms
│   │   └── --format, -f <json|table>     Output format [json]
│   │
│   └── show <platform_id>                Show detailed info about a platform
│
├── apps                                 Application commands
│   ├── list                              List all available applications
│   │   └── --format, -f <json|table>     Output format [json]
│   │
│   ├── show <app_id>                     Show detailed info about an application
│   │
│   ├── get-snippet <app_id>              Generate a Helm deployment snippet for an app
│   │   └── --config, -c <JSON>           JSON configuration string [{}]
│   │
│   └── deploy <app_id>                   Deploy an application directly on the local node
│       ├── --config, -c <JSON>           JSON configuration string [{}]
│       └── --detach / --no-detach        Run in background (detached) mode [detach]
│
├── utils                                Utilities commands
│   ├── describe-system                   Output the current system representation as JSON
│   │   └── --out, -o <PATH>              Also write output to a file path
│   │
│   └── check-system                      Validate system components vs recommended configs
│
├── skills                               Skills commands
│   ├── list                              List available skills
│   │   └── --format, -f <json|table>     Output format [json]
│   │
│   ├── show <name>                       Show detailed info about a skill
│   │
│   └── add <name>                        Symlink a skill's SKILL.md into assistant dirs
│       ├── --codex                       Symlink into Codex skills directory
│       ├── --claude                      Symlink into Claude skills directory
│       ├── --cursor                      Symlink into Cursor skills directory
│       ├── --opencode                    Symlink into OpenCode skills directory
│       ├── --global, -g                  Install in user-level directory
│       ├── --dest <PATH>                 Custom destination directory
│       └── --force                       Overwrite existing skill files
│
├── env                                  Environment variable commands
│   ├── set <key> <value>                 Set a local or global environment variable
│   │   └── --global, -g                   Set globally (user-wide) [default: local]
│   │
│   ├── get <key>                         Get the value of an environment variable
│   │
│   ├── list                              List environment variables
│   │   ├── --global, -g                   List global variables only
│   │   └── --local, -l                    List local variables only
│   │
│   └── delete <key>                       Delete a local or global environment variable
│       └── --global, -g                   Delete from global scope [default: local]
│
└── mcp                                  MCP server commands
    ├── start                              Start the Dell AI MCP server
    │   ├── --config <PATH>                Path to MCP config file
    │   ├── --transport <stdio|streamable-http|sse>  Transport type (defaults from config)
    │   ├── --host <HOST>                  HTTP host
    │   ├── --port <PORT>                  HTTP port
    │   └── --allow-destructive            Enable destructive tools
    │
    └── validate-config                    Validate an MCP configuration file
        └── --config <PATH>                Path to MCP config file
```

## Notes

- Every command also supports `--help`.
- Environment variables are stored in two scopes: **local** (`.dell-ai-env.json` in the current directory) and **global** (`~/.config/dell-ai/env.json`). They are auto-loaded into the process environment on CLI startup.
- `models get-snippet` and `models deploy` require exactly one of `--gpus` or `--goodput`. `--local-dir` and `--hf-cache-dir` are only supported with `--engine docker` and are mutually exclusive with each other.
- `models deploy` and `apps deploy` execute the generated snippet on the local node and require the relevant tooling (`docker`, `kubectl`, or `helm`) to be installed.
- `models undeploy` uses the deployment ID shown in `dell-ai status` (model ID by default, with `_N` suffixes for duplicate deployments).
- `skills add` cannot combine `--dest` with assistant flags (`--codex`, `--claude`, `--cursor`, `--opencode`) or `--global`.
- `mcp start` requires the `mcp` extra (`uv pip install 'dell-ai[mcp]'`). MCP defaults are read from `.dell-ai-mcp.json` (local) or `~/.config/dell-ai/mcp.json` (global); otherwise they fall back to `stdio` transport on `127.0.0.1:8000`.
