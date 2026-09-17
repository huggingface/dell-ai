import asyncio
from unittest import mock

import pytest

pytest.importorskip("mcp")

from dell_ai.mcp import deploy as deploy_module
from dell_ai.mcp import resources as resources_module
from dell_ai.mcp import skills as skills_module
from dell_ai.mcp import tools as tools_module
from dell_ai.mcp.config import MCPConfig
from dell_ai.mcp.server import create_server
from mcp import Client

EXPECTED_CATALOG_TOOLS = {
    "list_models",
    "search_models",
    "get_model",
    "get_compatible_platforms",
    "list_platforms",
    "get_platform",
    "get_platform_system_info",
    "check_model_access",
    "get_deployment_snippet",
    "get_container_tags",
    "get_goodput_scenarios",
    "list_apps",
    "get_app",
    "get_app_snippet",
    "list_deployments",
    "describe_system",
}

EXPECTED_DEPLOY_TOOLS = {
    "deploy_model",
    "deploy_app",
    "undeploy",
    "install_skill",
}

EXPECTED_SKILLS_TOOLS = {
    "list_skills",
    "get_skill",
}


def test_create_server_registers_catalog_tools():
    cfg = MCPConfig(capabilities={"tools": True, "resources": False, "prompts": False})
    mcp = create_server(cfg)
    tool_names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert EXPECTED_CATALOG_TOOLS.issubset(tool_names)
    assert EXPECTED_SKILLS_TOOLS.issubset(tool_names)
    assert not EXPECTED_DEPLOY_TOOLS.intersection(tool_names)


def test_create_server_allows_destructive_tools():
    cfg = MCPConfig(
        capabilities={"tools": True, "resources": False, "prompts": False},
        allow_destructive=True,
    )
    mcp = create_server(cfg)
    tool_names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert EXPECTED_CATALOG_TOOLS.issubset(tool_names)
    assert EXPECTED_SKILLS_TOOLS.issubset(tool_names)
    assert EXPECTED_DEPLOY_TOOLS.issubset(tool_names)


def test_create_server_tools_disabled():
    cfg = MCPConfig(capabilities={"tools": False, "resources": False, "prompts": False})
    mcp = create_server(cfg)
    tool_names = [t.name for t in asyncio.run(mcp.list_tools())]
    assert tool_names == []


def test_create_server_registers_resources():
    cfg = MCPConfig(capabilities={"tools": False, "resources": True, "prompts": False})
    mcp = create_server(cfg)
    resource_uris = {r.uri for r in asyncio.run(mcp.list_resources())}
    template_uris = {t.uri_template for t in asyncio.run(mcp.list_resource_templates())}
    assert "deh://deployments" in resource_uris
    assert "deh://system" in resource_uris
    assert "deh://skills" in resource_uris
    assert "deh://models/{+model_id}" in template_uris
    assert "deh://platforms/{platform_id}" in template_uris
    assert "deh://apps/{app_id}" in template_uris
    assert "deh://skills/{name}" in template_uris


def test_create_server_resources_disabled():
    cfg = MCPConfig(capabilities={"tools": False, "resources": False, "prompts": False})
    mcp = create_server(cfg)
    assert asyncio.run(mcp.list_resources()) == []


def test_create_server_registers_prompts():
    cfg = MCPConfig(capabilities={"tools": False, "resources": False, "prompts": True})
    mcp = create_server(cfg)
    prompt_names = {p.name for p in asyncio.run(mcp.list_prompts())}
    assert {"deploy_model", "deploy_app"}.issubset(prompt_names)


def test_create_server_prompts_disabled():
    cfg = MCPConfig(capabilities={"tools": False, "resources": False, "prompts": False})
    mcp = create_server(cfg)
    assert asyncio.run(mcp.list_prompts()) == []


def _run_tool(mcp, name, arguments=None):
    arguments = arguments or {}

    async def _main():
        async with Client(mcp, raise_exceptions=True) as client:
            return await client.call_tool(name, arguments)

    return asyncio.run(_main())


def _run_read_resource(mcp, uri):
    async def _main():
        async with Client(mcp, raise_exceptions=True) as client:
            return await client.read_resource(uri)

    return asyncio.run(_main())


def _fake_client():
    client = mock.MagicMock()
    client.list_models.return_value = ["org/model-a", "org/model-b"]
    client.search_models.return_value = []
    client.get_model.return_value = mock.MagicMock()
    client.get_model.return_value.model_dump.return_value = {"repo_name": "org/model"}
    client.get_compatible_platforms.return_value = []
    client.list_platforms.return_value = ["sku-1"]
    client.get_platform.return_value = mock.MagicMock()
    client.get_platform.return_value.model_dump.return_value = {"id": "sku-1"}
    client.get_platform_system_info.return_value = []
    client.check_model_access.return_value = True
    client.get_deployment_snippet.return_value = "docker run ..."
    client.get_container_tags.return_value = []
    client.get_goodput_scenarios.return_value = mock.MagicMock()
    client.get_goodput_scenarios.return_value.model_dump.return_value = {
        "scenarios": []
    }
    client.list_apps.return_value = ["openwebui"]
    client.get_app.return_value = mock.MagicMock()
    client.get_app.return_value.model_dump.return_value = {"id": "openwebui"}
    client.get_app_snippet.return_value = "helm install ..."
    client.deploy_model.return_value = {
        "success": True,
        "endpoint": "http://localhost:8000",
    }
    client.deploy_app.return_value = {
        "success": True,
        "endpoint": "http://localhost:8001",
    }
    return client


def test_list_models_tool(monkeypatch):
    fake_client = _fake_client()
    monkeypatch.setattr(tools_module, "create_client", lambda cfg: fake_client)

    cfg = MCPConfig()
    mcp = create_server(cfg)
    result = _run_tool(mcp, "list_models")

    assert not result.is_error
    assert "org/model-a" in result.content[0].text
    fake_client.list_models.assert_called_once_with(
        query=None,
        multimodal=None,
        min_size=None,
        max_size=None,
        license_filter=None,
        platform_id=None,
    )


def test_get_deployment_snippet_tool(monkeypatch):
    fake_client = _fake_client()
    monkeypatch.setattr(tools_module, "create_client", lambda cfg: fake_client)

    cfg = MCPConfig()
    mcp = create_server(cfg)
    result = _run_tool(
        mcp,
        "get_deployment_snippet",
        {
            "model_id": "org/model",
            "platform_id": "sku-1",
            "engine": "docker",
            "num_gpus": 1,
        },
    )

    assert not result.is_error
    assert result.content[0].text == "docker run ..."
    fake_client.get_deployment_snippet.assert_called_once_with(
        model_id="org/model",
        platform_id="sku-1",
        engine="docker",
        num_gpus=1,
        num_replicas=1,
        goodput=None,
        image_tag=None,
    )


def test_list_deployments_tool(monkeypatch):
    monkeypatch.setattr(tools_module.deployments_module, "list_deployments", lambda: {})

    cfg = MCPConfig()
    mcp = create_server(cfg)
    result = _run_tool(mcp, "list_deployments")

    assert not result.is_error
    assert result.content[0].text == "{}"


def test_describe_system_tool(monkeypatch):
    monkeypatch.setattr(tools_module, "get_system_info", lambda: {"os": "linux"})

    cfg = MCPConfig()
    mcp = create_server(cfg)
    result = _run_tool(mcp, "describe_system")

    assert not result.is_error
    assert "linux" in result.content[0].text


def test_deploy_model_tool(monkeypatch):
    fake_client = _fake_client()
    monkeypatch.setattr(tools_module, "create_client", lambda cfg: fake_client)

    cfg = MCPConfig(allow_destructive=True)
    mcp = create_server(cfg)
    result = _run_tool(
        mcp,
        "deploy_model",
        {
            "model_id": "org/model",
            "platform_id": "sku-1",
            "engine": "docker",
            "num_gpus": 1,
        },
    )

    assert not result.is_error
    assert "http://localhost:8000" in result.content[0].text
    fake_client.deploy_model.assert_called_once_with(
        model_id="org/model",
        platform_id="sku-1",
        engine="docker",
        num_gpus=1,
        num_replicas=1,
        detach=True,
        goodput=None,
        local_dir=None,
        hf_cache_dir=None,
        image_tag=None,
    )


def test_deploy_model_not_allowed_without_flag():
    cfg = MCPConfig(allow_destructive=False)
    mcp = create_server(cfg)
    tool_names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "deploy_model" not in tool_names


def test_deploy_app_tool(monkeypatch):
    fake_client = _fake_client()
    monkeypatch.setattr(tools_module, "create_client", lambda cfg: fake_client)

    cfg = MCPConfig(allow_destructive=True)
    mcp = create_server(cfg)
    result = _run_tool(mcp, "deploy_app", {"app_id": "openwebui"})

    assert not result.is_error
    assert "http://localhost:8001" in result.content[0].text
    fake_client.deploy_app.assert_called_once_with("openwebui", [], detach=True)


def test_undeploy_tool_docker(monkeypatch):
    fake_deployments = mock.MagicMock()
    fake_deployments.get_deployment.return_value = {
        "engine": "docker",
        "container_id": "abc123",
    }
    fake_deployments.delete_deployment.return_value = True
    monkeypatch.setattr(deploy_module, "deployments_module", fake_deployments)

    mock_run = mock.MagicMock()
    monkeypatch.setattr("dell_ai.mcp.deploy.subprocess.run", mock_run)

    cfg = MCPConfig(allow_destructive=True)
    mcp = create_server(cfg)
    result = _run_tool(mcp, "undeploy", {"deployment_id": "org/model"})

    assert not result.is_error
    assert result.content[0].text
    mock_run.assert_called_once_with(
        ["docker", "stop", "abc123"],
        capture_output=True,
        check=True,
        text=True,
    )
    fake_deployments.delete_deployment.assert_called_once_with("org/model")


def test_read_model_resource(monkeypatch):
    fake_client = _fake_client()
    fake_client.get_model.return_value = {"repo_name": "org/model"}
    monkeypatch.setattr(resources_module, "create_client", lambda cfg: fake_client)

    cfg = MCPConfig(capabilities={"tools": False, "resources": True, "prompts": False})
    mcp = create_server(cfg)
    result = _run_read_resource(mcp, "deh://models/org/model")

    assert result.contents
    assert "org/model" in result.contents[0].text
    fake_client.get_model.assert_called_once_with("org/model")


def test_list_skills_tool(monkeypatch):
    monkeypatch.setattr(skills_module, "get_skills", lambda: [{"name": "dell-ai"}])

    cfg = MCPConfig()
    mcp = create_server(cfg)
    result = _run_tool(mcp, "list_skills")

    assert not result.is_error
    assert "dell-ai" in result.content[0].text


def test_get_skill_tool(monkeypatch):
    monkeypatch.setattr(skills_module, "_get_skill", lambda name: "# Skill")

    cfg = MCPConfig()
    mcp = create_server(cfg)
    result = _run_tool(mcp, "get_skill", {"name": "dell-ai"})

    assert not result.is_error
    assert "# Skill" in result.content[0].text


def test_install_skill_tool(tmp_path, monkeypatch):
    source_file = tmp_path / "SKILL.md"
    source_file.write_text("# Dell AI Skill")
    monkeypatch.setattr(
        skills_module,
        "get_skills",
        lambda: [{"name": "dell-ai", "path": str(source_file)}],
    )
    monkeypatch.chdir(tmp_path)

    cfg = MCPConfig(allow_destructive=True)
    mcp = create_server(cfg)
    result = _run_tool(
        mcp,
        "install_skill",
        {"name": "dell-ai", "codex": True},
    )

    assert not result.is_error
    link = tmp_path / ".codex" / "skills" / "dell-ai" / "SKILL.md"
    assert link.is_symlink()
    assert link.read_text() == "# Dell AI Skill"
    assert "Linked skill" in result.content[0].text


def test_read_skills_resource(monkeypatch):
    monkeypatch.setattr(skills_module, "get_skills", lambda: [{"name": "dell-ai"}])

    cfg = MCPConfig(capabilities={"tools": False, "resources": True, "prompts": False})
    mcp = create_server(cfg)
    result = _run_read_resource(mcp, "deh://skills")

    assert result.contents
    assert "dell-ai" in result.contents[0].text
