from mcp.server import MCPServer

from dell_ai.mcp.config import MCPConfig


def register_prompts(mcp: MCPServer, config: MCPConfig) -> None:
    if not config.capabilities.prompts:
        return

    @mcp.prompt()
    def deploy_model() -> str:
        """Guide for deploying a model locally."""
        return (
            "I want to deploy a Dell Enterprise Hub model on this machine. Ask me "
            "for the model ID, platform SKU, engine (docker or kubernetes), and "
            "whether to size by num_gpus or a goodput scenario. Only call "
            "deploy_model after I confirm the configuration."
        )

    @mcp.prompt()
    def deploy_app() -> str:
        """Guide for deploying an application locally."""
        return (
            "I want to deploy a Dell Enterprise Hub application on this machine. "
            "Ask me for the app ID and any required configuration values, then "
            "call deploy_app."
        )
