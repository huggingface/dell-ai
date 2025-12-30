"""
Common test fixtures for the dell-ai package.
"""

import json
import platform
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dell_ai.client import DellAIClient
from dell_ai.system_utils import mem_info
from dell_ai.system_utils.base import Printer


@pytest.fixture
def mock_api_response():
    """Fixture that returns a mock API response."""
    return {
        "models": [
            {
                "repoName": "test-org/test-model",
                "description": "Test model",
                "license": "apache-2.0",
                "creatorType": "user",
                "size": 1000000,
                "hasSystemPrompt": False,
                "isMultimodal": False,
                "status": "active",
            }
        ],
        "platforms": [
            {
                "id": "test-sku",
                "name": "Test Platform",
                "disabled": False,
                "server": "test-server",
                "vendor": "test-vendor",
                "gputype": "test-gpu",
                "gpuram": "16GB",
                "gpuinterconnect": "test-interconnect",
                "productName": "Test Product",
                "totalgpucount": 4,
                "interconnect-east-west": "test-east-west",
                "interconnect-north-south": "test-north-south",
            }
        ],
    }


@pytest.fixture
def mock_client(mock_api_response):
    """Fixture that returns a mock DellAIClient instance."""
    with patch("dell_ai.client.requests") as mock_requests:
        mock_response = Mock()
        mock_response.json.return_value = mock_api_response
        mock_requests.get.return_value = mock_response

        client = DellAIClient(token="test-token")
        yield client


@pytest.fixture
def patched_platform(monkeypatch, fp):
    class uname_result:
        system = "Linux"
        node = "deh-r760xaL40-53"
        release = "6.8.0-88-generic"
        version = "89-Ubuntu SMP PREEMPT_DYNAMIC Sat Oct 11 01:02:46 UTC 2025"
        machine = "x86_64"

    monkeypatch.setattr(platform, "uname", lambda: uname_result())
    monkeypatch.setattr(
        platform,
        "freedesktop_os_release",
        lambda: {
            "NAME": "Ubuntu",
            "ID": "ubuntu",
            "PRETTY_NAME": "Ubuntu 24.04.3 LTS",
            "VERSION_ID": "24.04",
            "VERSION": "24.04.3 LTS (Noble Numbat)",
            "VERSION_CODENAME": "noble",
            "ID_LIKE": "debian",
            "HOME_URL": "https://www.ubuntu.com/",
            "SUPPORT_URL": "https://help.ubuntu.com/",
            "BUG_REPORT_URL": "https://bugs.launchpad.net/ubuntu/",
            "PRIVACY_POLICY_URL": "https://www.ubuntu.com/legal/terms-and-policies/privacy-policy",
            "UBUNTU_CODENAME": "noble",
            "LOGO": "ubuntu-logo",
        },
    )
    fp.register(["dmidecode", "-s", "system-product-name"], stdout="PowerEdge R760xa")


@pytest.fixture
def commandline_patches(fp, monkeypatch, patched_platform):
    resource_path = Path(__file__).parent / "unit" / "system_info" / "resources"

    fp.register(
        ["lscpu", "--json"], stdout=(resource_path / "lscpu_response.json").read_text()
    )
    fp.register(
        ["lspci", "-nn"],
        stdout=(resource_path / "lspci_stdout_nvidia_gpu.txt").read_text(),
        occurrences=2,
    )
    fp.register(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total,compute_cap",
            "--format=csv,noheader",
        ],
        stdout=(resource_path / "nvidia_gpu_info.txt").read_text(),
    )
    fp.register(
        ["nvidia-smi"],
        stdout=(resource_path / "nvidia_smi.txt").read_text(),
        occurrences=2,
    )
    fp.register(
        ["nvidia-ctk", "--version"],
        stdout=(resource_path / "nvidia_ctk.txt").read_text(),
        occurrences=2,
    )
    fp.register(
        ["/usr/bin/nvidia-container-runtime-hook", "--version"],
        stdout=(resource_path / "nvidia_container_runtime.txt").read_text(),
        occurrences=2,
    )
    fp.register(
        ["kubectl", "get", "nodes", "-o", "json"],
        stdout=(resource_path / "kubectl_get_nodes.json").read_text(),
    )
    fp.register(
        ["kubectl", "version", "-o", "json"],
        stdout=(resource_path / "kubectl_version.json").read_text(),
    )
    fp.register(
        ["lsblk", "-o", "name,model,size,type,mountpoint", "--json"],
        stdout=(resource_path / "lsblk.json").read_text(),
    )

    monkeypatch.setattr(mem_info, "MEMINFO_PATH", resource_path / "meminfo.txt")


@pytest.fixture
def printer_echo_mock(monkeypatch):
    mock = Mock(return_value=None)
    monkeypatch.setattr(Printer, "echo", lambda *a, **k: mock(*a, **k))
    yield mock


@pytest.fixture
def mock_sys_info():
    with open(
        Path(__file__).parent
        / "unit"
        / "system_info"
        / "resources"
        / "system_info_expected.json"
    ) as fp:
        sys_info = json.load(fp)
        yield sys_info
