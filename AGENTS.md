# Dell AI agent notes

## Commands
- Run all tests: `uv run pytest`
- Run specific tests: `uv run pytest tests/unit/test_env.py`

## Features Added
- **Local & Global Environment Variables**: Manages directory-specific `.dell-ai-env.json` and user-wide `~/.config/dell-ai/env.json` variables, dynamically loading them into `os.environ` during SDK and CLI startup.
- **Unified Deployment (`deploy`)**: Fetches Docker / Kubernetes / Helm snippets from Dell Enterprise Hub and automatically deploys/executes them locally on the node.
- **Robust Status Check (`status`)**: Root command `dell-ai status` scans active endpoints, local checkpoints, and running Docker / Kubernetes deployments to report live status.
