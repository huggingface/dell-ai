import asyncio
from pathlib import Path
from typing import Annotated, Any, Dict, Optional

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from dell_ai.cli.utils import (
    GLOBAL_AGENT_SKILLS_DIRS,
    LOCAL_AGENT_SKILLS_DIRS,
    get_skills,
)
from dell_ai.mcp.config import MCPConfig
from dell_ai.mcp.tools import format_result

READ_ONLY_ANNOTATIONS = ToolAnnotations(read_only_hint=True, open_world_hint=False)

DEPLOY_ANNOTATIONS = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    open_world_hint=True,
    idempotent_hint=False,
)


def register_skills_tools(mcp: MCPServer, config: MCPConfig) -> None:
    if not config.capabilities.tools:
        return

    @mcp.tool(title="List skills", annotations=READ_ONLY_ANNOTATIONS)
    async def list_skills() -> str:
        """List available agent skills from the Dell AI skills catalog."""
        result = await asyncio.to_thread(get_skills)
        return format_result(result)

    @mcp.tool(title="Get skill", annotations=READ_ONLY_ANNOTATIONS)
    async def get_skill(
        name: Annotated[str, Field(description="Skill name")],
    ) -> str:
        """Return the full markdown content of a skill."""
        result = await asyncio.to_thread(_get_skill, name)
        if result is None:
            return f"Skill '{name}' not found."
        return result

    if config.allow_destructive:

        @mcp.tool(title="Install skill", annotations=DEPLOY_ANNOTATIONS)
        async def install_skill(
            name: Annotated[str, Field(description="Skill name")],
            codex: Annotated[bool, Field(description="Install for Codex")] = False,
            claude: Annotated[bool, Field(description="Install for Claude")] = False,
            cursor: Annotated[bool, Field(description="Install for Cursor")] = False,
            opencode: Annotated[
                bool, Field(description="Install for OpenCode")
            ] = False,
            is_global: Annotated[
                bool,
                Field(
                    description="Install in user-level directory instead of the current project"
                ),
            ] = False,
            force: Annotated[
                bool, Field(description="Overwrite existing skill files")
            ] = False,
        ) -> str:
            """Symlink a skill into assistant skills directories."""
            result = _install_skill(
                name=name,
                codex=codex,
                claude=claude,
                cursor=cursor,
                opencode=opencode,
                is_global=is_global,
                force=force,
            )
            return format_result(result)


def register_skills_resources(mcp: MCPServer, config: MCPConfig) -> None:
    if not config.capabilities.resources:
        return

    @mcp.resource(
        "deh://skills",
        name="skills",
        mime_type="application/json",
    )
    async def skills_resource() -> str:
        """List available agent skills."""
        result = await asyncio.to_thread(get_skills)
        return format_result(result)

    @mcp.resource(
        "deh://skills/{name}",
        name="skill",
        mime_type="text/markdown",
    )
    async def skill_resource(name: str) -> str:
        """Markdown content of a skill."""
        result = await asyncio.to_thread(_get_skill, name)
        if result is None:
            return f"Skill '{name}' not found."
        return result


def _get_skill(name: str) -> Optional[str]:
    skills = get_skills()
    skill = next((s for s in skills if s["name"] == name), None)
    if skill is None:
        return None
    return Path(skill["path"]).read_text(encoding="utf-8")


def _install_skill(
    name: str,
    codex: bool,
    claude: bool,
    cursor: bool,
    opencode: bool,
    is_global: bool,
    force: bool,
) -> Dict[str, Any]:
    skills = get_skills()
    skill = next((s for s in skills if s["name"] == name), None)
    if skill is None:
        return {"success": False, "error": f"Skill '{name}' not found"}

    source = Path(skill["path"]).resolve()
    agent_dirs = GLOBAL_AGENT_SKILLS_DIRS if is_global else LOCAL_AGENT_SKILLS_DIRS
    targets = []
    if codex:
        targets.append(agent_dirs["codex"])
    if claude:
        targets.append(agent_dirs["claude"])
    if cursor:
        targets.append(agent_dirs["cursor"])
    if opencode:
        targets.append(agent_dirs["opencode"])

    if not targets:
        return {
            "success": False,
            "error": "Select at least one assistant (codex, claude, cursor, opencode)",
        }

    messages = []
    for target in targets:
        skill_dir = Path(target).expanduser() / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        link = skill_dir / source.name
        if link.exists() or link.is_symlink():
            if not force:
                messages.append(f"Skipped (already exists): {link}")
                continue
            link.unlink()
        link.symlink_to(source)
        messages.append(f"Linked skill at: {link}")

    return {"success": True, "messages": messages}
