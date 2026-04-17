from pathlib import Path
import platform
from unittest.mock import call

import pytest

from dell_ai.system_utils.base import Printer
from dell_ai.system_utils.gpu_info import (
    GPUInfoGetter,
    get_driver_info,
    get_gpus_and_accelerator_info,
)
from dell_ai.system_utils.gpu_info.accelerator import Accelerator, AcceleratorInfo
from dell_ai.system_utils.gpu_info.driver_info.amd_driver_info import AmdDriverInfo
from dell_ai.system_utils.gpu_info.driver_info.nvidia_driver_info import (
    NvidiaDriverInfo,
)
from dell_ai.system_utils.gpu_info.gpu_info import GPUInfo
from dell_ai.system_utils.gpu_info.info_getter.amd_info_getter import AmdInfoGetter
from dell_ai.system_utils.gpu_info.info_populator.amd_info_populator import (
    AMDInfoPopulater,
)
from dell_ai.system_utils.gpu_info.info_populator.nvidia_info_populator import (
    NvidiaInfoPopulater,
)

resource_folder = Path(__file__).parent / "resources"


class TestAmdGpuInfoGetter:
    @pytest.fixture
    def lspci_amd(self, fp):
        output = "dd:00.0 Processing accelerators [1200]: Advanced Micro Devices, Inc. [AMD/ATI] Aqua Vanjaram [Instinct MI300X] [1002:74a1]"
        fp.register(["lspci", "-nn"], stdout=output)
        yield

    @pytest.fixture
    def amd_smi_static_root(self, fp):
        fp.register(
            ["amd-smi", "static", "--json"],
            stdout=(resource_folder / "amd_smi_static_json_root.json").read_text(),
        )
        yield

    @pytest.fixture
    def amd_smi_static_nonroot(self, fp):
        fp.register(
            ["amd-smi", "static", "--json"],
            stdout=(resource_folder / "amd_smi_static_json_non_root.txt").read_text(),
        )
        yield

    @pytest.fixture
    def amd_smi_version_root(self, fp):
        fp.register(
            ["amd-smi", "version", "--json"],
            stdout=(resource_folder / "amd_smi_version_root.json").read_text(),
        )

    @pytest.fixture
    def amd_smi_version_nonroot(self, fp):
        fp.register(
            ["amd-smi", "version", "--json"],
            stdout=(resource_folder / "amd_smi_version_non_root.json").read_text(),
        )

    @pytest.fixture
    def kubectl_get_nodes_amd(self, fp, monkeypatch):
        fp.register(
            ["kubectl", "get", "nodes", "-o", "json"],
            stdout=(resource_folder / "kubectl_get_nodes_amd.json").read_text(),
        )

        class uname_result:
            system = "Linux"
            node = "deh-waco-62"
            release = "6.8.0-88-generic"
            version = "89-Ubuntu SMP PREEMPT_DYNAMIC Sat Oct 11 01:02:46 UTC 2025"
            machine = "x86_64"

        monkeypatch.setattr(platform, "uname", lambda: uname_result())

    def test_get_gpu_vendors_pass(self, lspci_amd):
        vendors = GPUInfoGetter.get_gpu_vendors()
        assert "AMD" in vendors, "GPU entries are present"

    def test_get_gpu_accelerator_fail(self, lspci_amd, fp):
        """
        Test gpu and accelarator info is empty if nvidia-smi does not exist
        """
        fp.register(
            ["amd-smi", fp.any()],
            returncode=1,
            stdout="amd-smi: Command not found",
        )
        fp.register(["kubectl", fp.any()], returncode=1, occurrences=4)

        gpu, accelerators = GPUInfoGetter().get_gpu_accelerator()
        assert (gpu, accelerators.model_dump()) == ([], {"amd": []})

    def test_get_gpu_accelerator_pass(
        self, lspci_amd, amd_smi_static_root, kubectl_get_nodes_amd
    ):
        """
        With the patched CLI commands, test success case of GPU and accelerator information.
        Tests the collect_gpu_info function
        """
        gpus, accelerators = get_gpus_and_accelerator_info()
        assert gpus == [
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X",
                ram=196592,
                driver_version="6.16.13",
                compute_cap=304,
                index=0,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X",
                ram=196592,
                driver_version="6.16.13",
                compute_cap=304,
                index=1,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X",
                ram=196592,
                driver_version="6.16.13",
                compute_cap=304,
                index=2,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X",
                ram=196592,
                driver_version="6.16.13",
                compute_cap=304,
                index=3,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X",
                ram=196592,
                driver_version="6.16.13",
                compute_cap=304,
                index=4,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X",
                ram=196592,
                driver_version="6.16.13",
                compute_cap=304,
                index=5,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X",
                ram=196592,
                driver_version="6.16.13",
                compute_cap=304,
                index=6,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X",
                ram=196592,
                driver_version="6.16.13",
                compute_cap=304,
                index=7,
            ),
        ]
        assert accelerators.model_dump() == {
            "amd": [
                {"driver_version": "6.16.13", "name": "AMD Instinct MI300X"},
                {"driver_version": "6.16.13", "name": "AMD Instinct MI300X"},
                {"driver_version": "6.16.13", "name": "AMD Instinct MI300X"},
                {"driver_version": "6.16.13", "name": "AMD Instinct MI300X"},
                {"driver_version": "6.16.13", "name": "AMD Instinct MI300X"},
                {"driver_version": "6.16.13", "name": "AMD Instinct MI300X"},
                {"driver_version": "6.16.13", "name": "AMD Instinct MI300X"},
                {"driver_version": "6.16.13", "name": "AMD Instinct MI300X"},
            ]
        }

    def test_get_gpu_accelerator_nonroot(
        self, lspci_amd, amd_smi_static_nonroot, kubectl_get_nodes_amd
    ):
        """
        Falls back on kubectl calls to populate information
        """
        gpus, accelerators = get_gpus_and_accelerator_info()
        assert gpus == [
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X OAM",
                ram=196608,
                driver_version="6.18.8",
                compute_cap=304,
                index=0,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X OAM",
                ram=196608,
                driver_version="6.18.8",
                compute_cap=304,
                index=1,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X OAM",
                ram=196608,
                driver_version="6.18.8",
                compute_cap=304,
                index=2,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X OAM",
                ram=196608,
                driver_version="6.18.8",
                compute_cap=304,
                index=3,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X OAM",
                ram=196608,
                driver_version="6.18.8",
                compute_cap=304,
                index=4,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X OAM",
                ram=196608,
                driver_version="6.18.8",
                compute_cap=304,
                index=5,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X OAM",
                ram=196608,
                driver_version="6.18.8",
                compute_cap=304,
                index=6,
            ),
            GPUInfo(
                vendor="AMD",
                model="AMD Instinct MI300X OAM",
                ram=196608,
                driver_version="6.18.8",
                compute_cap=304,
                index=7,
            ),
        ]
        assert accelerators.model_dump() == {
            "amd": [
                {"driver_version": "6.18.8", "name": "AMD Instinct MI300X OAM"},
                {"driver_version": "6.18.8", "name": "AMD Instinct MI300X OAM"},
                {"driver_version": "6.18.8", "name": "AMD Instinct MI300X OAM"},
                {"driver_version": "6.18.8", "name": "AMD Instinct MI300X OAM"},
                {"driver_version": "6.18.8", "name": "AMD Instinct MI300X OAM"},
                {"driver_version": "6.18.8", "name": "AMD Instinct MI300X OAM"},
                {"driver_version": "6.18.8", "name": "AMD Instinct MI300X OAM"},
                {"driver_version": "6.18.8", "name": "AMD Instinct MI300X OAM"},
            ]
        }

    def test_get_gpu_accelerator_nonroot_nokube(
        self, lspci_amd, amd_smi_static_nonroot, fp
    ):
        """
        Falls back on kubectl calls to populate information
        """
        fp.register(
            ["kubectl", fp.any()], returncode=1, stdout="kubectl: command not found"
        )
        gpus, accelerators = get_gpus_and_accelerator_info()
        assert gpus == [
            GPUInfo(
                vendor="AMD",
                model="",
                ram=None,
                driver_version=None,
                compute_cap=0,
                index=0,
            ),
            GPUInfo(
                vendor="AMD",
                model="",
                ram=None,
                driver_version=None,
                compute_cap=0,
                index=1,
            ),
            GPUInfo(
                vendor="AMD",
                model="",
                ram=None,
                driver_version=None,
                compute_cap=0,
                index=2,
            ),
            GPUInfo(
                vendor="AMD",
                model="",
                ram=None,
                driver_version=None,
                compute_cap=0,
                index=3,
            ),
            GPUInfo(
                vendor="AMD",
                model="",
                ram=None,
                driver_version=None,
                compute_cap=0,
                index=4,
            ),
            GPUInfo(
                vendor="AMD",
                model="",
                ram=None,
                driver_version=None,
                compute_cap=0,
                index=5,
            ),
            GPUInfo(
                vendor="AMD",
                model="",
                ram=None,
                driver_version=None,
                compute_cap=0,
                index=6,
            ),
            GPUInfo(
                vendor="AMD",
                model="",
                ram=None,
                driver_version=None,
                compute_cap=0,
                index=7,
            ),
        ]
        assert accelerators.model_dump() == {
            "amd": [
                {"driver_version": "N/A", "name": "N/A"},
                {"driver_version": "N/A", "name": "N/A"},
                {"driver_version": "N/A", "name": "N/A"},
                {"driver_version": "N/A", "name": "N/A"},
                {"driver_version": "N/A", "name": "N/A"},
                {"driver_version": "N/A", "name": "N/A"},
                {"driver_version": "N/A", "name": "N/A"},
                {"driver_version": "N/A", "name": "N/A"},
            ]
        }

    def test_get_driver_info(self, lspci_amd, amd_smi_version_root):
        """
        Test model assignment. Should be of type
            {
                "amd": AmdDriverInfo(...)
            }
        """
        info = get_driver_info()
        assert info == {
            "amd": AmdDriverInfo.model_validate(
                {
                    "cuda_version_from_rocm_smi": "7.2.1",
                    "driver_version": "6.16.13",
                }
            )
        }

    def test_get_driver_info_nonroot(
        self, lspci_amd, amd_smi_version_nonroot, kubectl_get_nodes_amd
    ):
        info = get_driver_info()
        assert info == {
            "amd": AmdDriverInfo.model_validate(
                {
                    "cuda_version_from_rocm_smi": "7.2.1",
                    "driver_version": "6.18.8",
                }
            )
        }


class TestGPUInfoGetter:
    """Tests for GPUInfoGetter (info_getter module) and top-level aggregation functions."""

    @pytest.fixture
    def lspci(self, fp):
        """
        Fixture to mock the lspci command for nvidia gpus
        """
        lspci_nvidia_out = resource_folder / "lspci_stdout_nvidia_gpu.txt"
        fp.register(["lspci", "-nn"], stdout=lspci_nvidia_out.read_text())
        yield

    @pytest.fixture
    def lspci_intel(self, fp):
        """
        Fixture to mock the lspci command for intel accelerators.
        """
        intel_output = (
            "00:02.0 3D controller [0302]: Intel Corporation Device [8086:56c0]\n"
        )
        fp.register(["lspci", "-nn"], stdout=intel_output)
        yield

    def test_get_gpu_vendors_pass(self, lspci):
        """
        Test vendor discovery using lscpi fixture
        """
        vendors = GPUInfoGetter.get_gpu_vendors()
        assert "NVIDIA" in vendors, "GPU entries are present"

    def test_gpu_vendors_fail(self, fp):
        """
        Do not get any GPU vendor if lspci errors out
        """
        fp.register(["lspci", fp.any()], returncode=1)
        assert GPUInfoGetter.get_gpu_vendors() == []

    def test_get_gpu_accelerator_fail(self, lspci, fp):
        """
        Test gpu and accelarator info is empty if nvidia-smi does not exist
        """
        fp.register(
            ["nvidia-smi", fp.any()],
            returncode=1,
            stdout="nvidia-smi: Command not found",
        )
        fp.register(["kubectl", fp.any()], returncode=1, occurrences=4)

        gpu, accelerators = GPUInfoGetter().get_gpu_accelerator()
        assert (gpu, accelerators.model_dump()) == ([], {"nvidia": []})

    def test_get_gpu_accelerator_intel_branch(self, lspci_intel):
        """
        Test intel vendor is routed to intel accelerator branch.
        """
        gpu, accelerators = GPUInfoGetter().get_gpu_accelerator()
        print(gpu, accelerators)
        assert (gpu, accelerators.model_dump()) == ([], {"intel": []})

    def test_get_gpu_accelerator_pass(self, commandline_patches):
        """
        With the patched CLI commands, test success case of GPU and accelerator information.
        Tests the collect_gpu_info function
        """
        gpus, accelerators = get_gpus_and_accelerator_info()
        assert gpus == [
            GPUInfo(
                vendor="NVIDIA",
                model="NVIDIA L40S",
                ram=46068,
                driver_version="570.172.08",
                compute_cap=89,
                index=0,
            ),
            GPUInfo(
                vendor="NVIDIA",
                model="NVIDIA L40S",
                ram=46068,
                driver_version="570.172.08",
                compute_cap=89,
                index=1,
            ),
            GPUInfo(
                vendor="NVIDIA",
                model="NVIDIA L40S",
                ram=46068,
                driver_version="570.172.08",
                compute_cap=89,
                index=2,
            ),
            GPUInfo(
                vendor="NVIDIA",
                model="NVIDIA L40S",
                ram=46068,
                driver_version="570.172.08",
                compute_cap=89,
                index=3,
            ),
        ]
        assert accelerators.model_dump() == {
            "nvidia": [
                {"driver_version": "570.172.08", "name": "NVIDIA L40S"},
                {"driver_version": "570.172.08", "name": "NVIDIA L40S"},
                {"driver_version": "570.172.08", "name": "NVIDIA L40S"},
                {"driver_version": "570.172.08", "name": "NVIDIA L40S"},
            ]
        }

    def test_get_driver_info(self, commandline_patches):
        """
        Test model assignment. Should be of type
            {
                "nvidia": NvidiaDriverInfo(...)
            }
        for nvidia and similar for amd and intel. Those tests will be implemented later
        """
        info = get_driver_info()
        assert info == {
            "nvidia": NvidiaDriverInfo.model_validate(
                {
                    "cuda_version_from_nvidia_smi": "12.8",
                    "nvidia_ctk_version": "1.17.8",
                    "driver_version": "570.172.08",
                    "nvidia_container_toolkit_version": "1.17.8",
                }
            )
        }


class TestNvidiaInfoPopulater:
    """Tests for NvidiaInfoPopulater (info_populator/nvidia_info_populator.py)."""

    def test_nvidia_info_populator(self, commandline_patches):
        """
        Test all getters in the NvidiaInfoPopulater class
        """
        info = NvidiaInfoPopulater()
        assert info.details.cuda_version_from_nvidia_smi == "12.8"
        assert info.details.nvidia_ctk_version == "1.17.8"
        assert info.details.driver_version == "570.172.08"

    def test_smi_get_cuda_success(self, fp):
        """
        Test smi_get_cuda parses CUDA version and driver version from nvidia-smi output
        """
        nvidia_smi_out = resource_folder / "nvidia_smi.txt"
        fp.register(["nvidia-smi"], stdout=nvidia_smi_out.read_text(), occurrences=2)
        fp.register(
            ["kubectl", "get", "nodes", "-o", "json"], returncode=1, occurrences=4
        )
        fp.register(["nvidia-ctk", fp.any()], returncode=1, occurrences=2)
        fp.register(
            ["/usr/bin/nvidia-container-runtime-hook", fp.any()],
            returncode=1,
            occurrences=2,
        )

        info = NvidiaInfoPopulater()
        assert info.details.cuda_version_from_nvidia_smi == "12.8"
        assert info.details.driver_version == "570.172.08"

    def test_smi_get_cuda_nvidia_smi_fails(self, fp):
        """
        Test smi_get_cuda returns early when nvidia-smi command fails
        """
        fp.register(
            ["nvidia-smi"],
            returncode=1,
            stdout="nvidia-smi: Command not found",
            occurrences=2,
        )
        fp.register(
            ["kubectl", "get", "nodes", "-o", "json"], returncode=1, occurrences=4
        )
        fp.register(["nvidia-ctk", fp.any()], returncode=1, occurrences=2)
        fp.register(
            ["/usr/bin/nvidia-container-runtime-hook", fp.any()],
            returncode=1,
            occurrences=2,
        )

        info = NvidiaInfoPopulater()
        assert info.details.cuda_version_from_nvidia_smi is None
        assert info.details.driver_version is None

    def test_smi_get_cuda_partial_output(self, fp):
        """
        Test smi_get_cuda when nvidia-smi output has CUDA version but not driver version
        """
        partial_output = "CUDA Version: 12.5"
        fp.register(["nvidia-smi"], stdout=partial_output, occurrences=2)
        fp.register(
            ["kubectl", "get", "nodes", "-o", "json"], returncode=1, occurrences=4
        )
        fp.register(["nvidia-ctk", fp.any()], returncode=1, occurrences=2)
        fp.register(
            ["/usr/bin/nvidia-container-runtime-hook", fp.any()],
            returncode=1,
            occurrences=2,
        )

        info = NvidiaInfoPopulater()
        assert info.details.cuda_version_from_nvidia_smi == "12.5"
        assert info.details.driver_version is None

    def test_smi_get_cuda_driver_only(self, fp):
        """
        Test smi_get_cuda when nvidia-smi output has driver version but not CUDA version.
        Note: When CUDA regex doesn't match and kubectl fails, the method returns early
        before checking driver regex (expected behavior per current implementation).
        """
        partial_output = "Driver Version: 535.104.05"
        fp.register(["nvidia-smi"], stdout=partial_output, occurrences=2)
        fp.register(
            ["kubectl", "get", "nodes", "-o", "json"], returncode=1, occurrences=4
        )
        fp.register(["nvidia-ctk", fp.any()], returncode=1, occurrences=2)
        fp.register(
            ["/usr/bin/nvidia-container-runtime-hook", fp.any()],
            returncode=1,
            occurrences=2,
        )

        info = NvidiaInfoPopulater()
        # Both are None because CUDA regex doesn't match and kubectl fails,
        # so the method returns early before checking driver regex
        assert info.details.cuda_version_from_nvidia_smi is None
        assert info.details.driver_version is None

    def test_smi_get_cuda_no_regex_match(self, fp):
        """
        Test smi_get_cuda when nvidia-smi output doesn't match any regex patterns
        """
        invalid_output = "Some random output without version info"
        fp.register(["nvidia-smi"], stdout=invalid_output, occurrences=2)
        fp.register(
            ["kubectl", "get", "nodes", "-o", "json"], returncode=1, occurrences=4
        )
        fp.register(["nvidia-ctk", fp.any()], returncode=1, occurrences=2)
        fp.register(
            ["/usr/bin/nvidia-container-runtime-hook", fp.any()],
            returncode=1,
            occurrences=2,
        )

        info = NvidiaInfoPopulater()
        assert info.details.cuda_version_from_nvidia_smi is None
        assert info.details.driver_version is None

    def test_smi_get_cuda_different_versions(self, fp):
        """
        Test smi_get_cuda with various CUDA and driver version formats
        """
        custom_output = "+-----------------------------------------------------------------------------------------+\n| NVIDIA-SMI 545.23.06              Driver Version: 545.23.06     CUDA Version: 12.3     |\n"
        fp.register(["nvidia-smi"], stdout=custom_output, occurrences=2)
        fp.register(
            ["kubectl", "get", "nodes", "-o", "json"], returncode=1, occurrences=4
        )
        fp.register(["nvidia-ctk", fp.any()], returncode=1, occurrences=2)
        fp.register(
            ["/usr/bin/nvidia-container-runtime-hook", fp.any()],
            returncode=1,
            occurrences=2,
        )

        info = NvidiaInfoPopulater()
        assert info.details.cuda_version_from_nvidia_smi == "12.3"
        assert info.details.driver_version == "545.23.06"

    def test_nvidia_info_populator_no_nvidia(self, fp):
        """
        Test getters if driver is not installed correctly and CLI tools are missing
        """
        fp.register(
            ["nvidia-smi"],
            returncode=1,
            stdout="nvidia-smi: Command not found",
            occurrences=2,
        )
        fp.register(
            ["nvidia-ctk", fp.any()],
            returncode=1,
            stdout="nvidia-ctk: Command not found",
            occurrences=2,
        )
        fp.register(["kubectl", fp.any()], returncode=1, occurrences=4)
        fp.register(
            ["/usr/bin/nvidia-container-runtime-hook", fp.any()],
            returncode=1,
            stdout="/usr/bin/nvidia-container-runtime-hook: File not found",
            occurrences=2,
        )
        info = NvidiaInfoPopulater()
        assert info.details.cuda_version_from_nvidia_smi is None
        assert info.details.driver_version is None
        assert info.details.nvidia_ctk_version is None
        assert info.details.nvidia_container_toolkit_version is None

    def test_nvidia_info_populator_k8s_info(self, fp):
        """
        Test fallback on kubectl if CLI tools are missing
        """
        fp.register(
            ["nvidia-smi"],
            returncode=1,
            stdout="nvidia-smi: Command not found",
            occurrences=2,
        )
        fp.register(
            ["nvidia-ctk", fp.any()],
            returncode=1,
            stdout="nvidia-ctk: Command not found",
            occurrences=2,
        )
        fp.register(
            ["kubectl", "get", "nodes", "-o", "json"],
            stdout=(resource_folder / "kubectl_get_nodes.json").read_text(),
            occurrences=4,
        )
        fp.register(
            ["/usr/bin/nvidia-container-runtime-hook", fp.any()],
            returncode=1,
            stdout="/usr/bin/nvidia-container-runtime-hook: File not found",
            occurrences=2,
        )
        info = NvidiaInfoPopulater()
        assert info.details.cuda_version_from_nvidia_smi is None
        assert info.details.driver_version is None
        assert info.details.nvidia_ctk_version == "1.17.8"
        assert info.details.nvidia_container_toolkit_version is None


class TestAmdInfoGetter:
    def test_try_fallback_json_parse_with_warning_lines(self):
        """Test fallback JSON parsing with warning/error lines before JSON"""
        output_with_warnings = """Permission needed to access required GPU device node(s):
  • /dev/kfd: Permission denied
  • /dev/dri/renderD*: 64 device(s) denied

To resolve this issue, try the following:
  • Add your user to the required group(s)

{"gpu_data": [{"gpu": 0, "asic": {"market_name": "AMD Instinct MI300X"}}]}"""

        result = AmdInfoGetter._try_fallback_json_parse(output_with_warnings)
        assert result is not None
        assert result["gpu_data"][0]["gpu"] == 0
        assert result["gpu_data"][0]["asic"]["market_name"] == "AMD Instinct MI300X"

    def test_try_fallback_json_parse_valid_json(self):
        """Test fallback parsing with valid JSON (no warnings)"""
        valid_json = '{"gpu_data": [{"gpu": 1, "asic": {"market_name": "Test GPU"}}]}'
        result = AmdInfoGetter._try_fallback_json_parse(valid_json)
        assert result is not None
        assert result["gpu_data"][0]["gpu"] == 1

    def test_try_fallback_json_parse_invalid_json(self):
        """Test fallback parsing with completely invalid JSON"""
        invalid_output = """Some random text
Not JSON at all
{ incomplete json"""

        result = AmdInfoGetter._try_fallback_json_parse(invalid_output)
        assert result is None

    def test_try_fallback_json_parse_no_json_start(self):
        """Test fallback parsing when no opening brace is found"""
        no_json = """Error: command failed
No JSON data here
Just plain text"""

        result = AmdInfoGetter._try_fallback_json_parse(no_json)
        assert result is None

    def test_try_fallback_json_parse_multiline_json(self):
        """Test fallback parsing with multiline JSON after warnings"""
        multiline_output = """Warning: Permission denied
{
    "gpu_data": [
        {
            "gpu": 0,
            "asic": {
                "market_name": "MI300X"
            }
        }
    ]
}"""

        result = AmdInfoGetter._try_fallback_json_parse(multiline_output)
        assert result is not None
        assert result["gpu_data"][0]["asic"]["market_name"] == "MI300X"


class TestAmdInfoPopulator:
    @pytest.fixture
    def amd_smi_root(self, fp):
        fp.register(
            ["amd-smi", "version", "--json"],
            stdout=(resource_folder / "amd_smi_version_root.json").read_text(),
        )

    @pytest.fixture
    def amd_smi_nonroot(self, fp):
        fp.register(
            ["amd-smi", "version", "--json"],
            stdout=(resource_folder / "amd_smi_version_non_root.json").read_text(),
        )

    @pytest.fixture
    def kubectl_get_nodes_amd(self, fp, monkeypatch):
        fp.register(
            ["kubectl", "get", "nodes", "-o", "json"],
            stdout=(resource_folder / "kubectl_get_nodes_amd.json").read_text(),
        )

        class uname_result:
            system = "Linux"
            node = "deh-waco-62"
            release = "6.8.0-88-generic"
            version = "89-Ubuntu SMP PREEMPT_DYNAMIC Sat Oct 11 01:02:46 UTC 2025"
            machine = "x86_64"

        monkeypatch.setattr(platform, "uname", lambda: uname_result())

    def test_amd_smi_version_root(self, amd_smi_root):
        info = AMDInfoPopulater()
        assert info.details.cuda_version_from_rocm_smi == "7.2.1"
        assert info.details.driver_version == "6.16.13"

    def test_amd_smi_version_nonroot(self, amd_smi_nonroot, kubectl_get_nodes_amd):
        info = AMDInfoPopulater()
        assert info.details.cuda_version_from_rocm_smi == "7.2.1"
        assert info.details.driver_version == "6.18.8"

    def test_kubectl_only(self, fp, kubectl_get_nodes_amd):
        fp.register(
            ["amd-smi", fp.any()], returncode=1, stdout="amd-smi: command not found"
        )
        info = AMDInfoPopulater()
        assert info.details.cuda_version_from_rocm_smi is None
        assert info.details.driver_version == "6.18.8"

    def test_both_amd_smi_and_kubectl_not_working(self, fp):
        fp.register(
            ["amd-smi", fp.any()], returncode=1, stdout="amd-smi: command not found"
        )
        fp.register(
            ["kubectl", fp.any()], returncode=1, stdout="kubectl: command not found"
        )

        info = AMDInfoPopulater()
        assert info.details.driver_version is None
        assert info.details.cuda_version_from_rocm_smi is None


class TestDriverInfoCompare:
    """Tests for driver info compare methods (driver_info module)."""

    def test_nvidia_driver_info_compare(self, printer_echo_mock):
        """
        Tests the comparison of NvidiaDriverInfo objects.

        This function creates several NvidiaDriverInfo objects with different versions
        of CUDA, driver, and NVIDIA Container Toolkit, and then compares them to test
        the compare method of the NvidiaDriverInfo class.

        """
        # all versions in tested range
        success = NvidiaDriverInfo(
            cuda_version_from_nvidia_smi="12.8",
            driver_version="566.125.15",
            nvidia_container_toolkit_version="17.8.1",
        )
        others = [
            NvidiaDriverInfo(
                cuda_version_from_nvidia_smi="12.8",
                driver_version="594.564.56",
                nvidia_container_toolkit_version="17.8.1",
            ),
            NvidiaDriverInfo(
                cuda_version_from_nvidia_smi="13.0", driver_version="566.125.15"
            ),
        ]

        # cuda version lower than tested, missing nvidia_container_toolkit_version
        failure = NvidiaDriverInfo(
            cuda_version_from_nvidia_smi="11.0", driver_version="566.125.15"
        )

        # success case, should not print anything
        success.compare(others)
        printer_echo_mock.assert_not_called()

        # cuda version check should return error as its lower than tested, and container toolkit version is missing
        failure.compare(others)
        printer_echo_mock.assert_has_calls(
            calls=[
                call(
                    Printer.minimum_styled(
                        self_value="11.0",
                        supported_values=["12.8", "13.0"],
                        tag="CUDA version from NVIDIA SMI",
                        attr_name="cuda_version_from_nvidia_smi",
                    ),
                    level="error",
                ),
                call(
                    Printer.not_found(
                        tag="NVIDIA Container Toolkit version",
                        attr_name="nvidia_container_toolkit_version",
                    ),
                    level="error",
                ),
            ],
            any_order=True,
        )

    def test_amd_driver_info_compare(self, printer_echo_mock):
        """
        Similar test as above for AMD
        """
        # all versions in allowed range
        success = AmdDriverInfo(
            cuda_version_from_rocm_smi="12.8", driver_version="566.125.15"
        )
        others = [
            AmdDriverInfo(
                cuda_version_from_rocm_smi="12.8", driver_version="594.564.56"
            ),
            AmdDriverInfo(
                cuda_version_from_rocm_smi="13.0", driver_version="566.125.15"
            ),
        ]

        # lower cuda version
        failure = AmdDriverInfo(
            cuda_version_from_rocm_smi="11.0", driver_version="566.125.15"
        )

        # no output
        success.compare(others)
        printer_echo_mock.assert_not_called()

        # should print error for cuda version
        failure.compare(others)
        printer_echo_mock.assert_called_once_with(
            Printer.minimum_styled(
                self_value="11.0",
                supported_values=["12.8", "13.0"],
                tag="CUDA version from ROCM SMI",
                attr_name="cuda_version_from_rocm_smi",
            ),
            level="error",
        )


class TestAccelerator:
    """Tests for AcceleratorInfo and Accelerator compare methods (accelerator module)."""

    def test_accelerator_info_compare(self, printer_echo_mock):
        """
        Testing nvidia accelerator info compareagainst other nvidia accelerator infos (apples to apples comparison)
        """
        # version tested
        success = AcceleratorInfo(driver_version="566.125.15", name="NVIDIA B200")
        others = [
            AcceleratorInfo(driver_version="594.564.56", name="NVIDIA B200"),
            AcceleratorInfo(driver_version="566.125.15", name="NVIDIA B200"),
        ]
        # version lower than tested, should generate error
        failure = AcceleratorInfo(driver_version="560.125.15", name="NVIDIA B200")

        success.compare(others)
        printer_echo_mock.assert_not_called()

        failure.compare(others)
        printer_echo_mock.assert_called_once_with(
            Printer.version_compare_styled(
                self_value="560.125.15",
                min_supported_value="566.125.15",
                max_supported_value="594.564.56",
                tag="Driver version",
                attr_name="driver_version",
                greater=False,
            ),
            level="error",
        )

    def test_accelerator_compare(self, printer_echo_mock):
        """
        Test accelerator info object comparison of different types (apples to oranges)
        """

        obj = Accelerator.model_validate(
            {
                "nvidia": [
                    AcceleratorInfo(driver_version="562.124.012", name="Nvidia H200"),
                    AcceleratorInfo(driver_version="562.124.012", name="Nvidia H200"),
                ]
            }
        )
        items = [
            Accelerator.model_validate(
                {
                    "nvidia": [
                        AcceleratorInfo(
                            driver_version="562.124.12", name="Nvidia H200"
                        ),
                        AcceleratorInfo(
                            driver_version="562.124.12", name="Nvidia H200"
                        ),
                    ]
                }
            ),
            Accelerator.model_validate(
                {
                    "nvidia": [
                        AcceleratorInfo(
                            driver_version="563.124.12", name="Nvidia H200"
                        ),
                        AcceleratorInfo(
                            driver_version="561.124.12", name="Nvidia H200"
                        ),
                    ]
                }
            ),
        ]

        # nvidia against nvidia comparison, no errors
        obj.compare(items)
        printer_echo_mock.assert_not_called()

        amd_obj = Accelerator.model_validate(
            {
                "amd": [
                    AcceleratorInfo(driver_version="562.124.12", name="AMD Mi355"),
                    AcceleratorInfo(driver_version="562.124.12", name="AMD Mi355"),
                ]
            }
        )

        # amd against nvidia comparison, should generate error
        amd_obj.compare(items)
        printer_echo_mock.assert_called()
        printer_echo_mock.assert_called_with(
            Printer.list_compare_styled(
                self_value="amd",
                tag="Accelerator",
                supported_values=["nvidia"],
                attr_name="info",
            ),
            level="error",
        )


class TestGPUInfo:
    """Tests for GPUInfo compare method (gpu_info module)."""

    def test_gpu_info_compare_diff_vendor(self, printer_echo_mock):
        """Test GPU info comparison when vendors tested are different, should generate error"""

        obj = GPUInfo(
            vendor="NVIDIA",
            model="NVIDIA H200",
            ram=64,
            driver_version="576.125.42",
            compute_cap=89,
            index=1,
        )
        amd_items = [
            GPUInfo(
                vendor="AMD", model="AMD Mi355x", ram=64, driver_version="546.435.56"
            )
        ]
        obj.compare(amd_items)
        printer_echo_mock.assert_called_with(
            "Found no supported vendor configuration for vendor NVIDIA, supported ['AMD']",
            level="error",
        )

    def test_gpu_info_compare_pass(self, printer_echo_mock):
        """
        Test GPU info comparison when vendors are same.
        """
        obj = GPUInfo(
            vendor="NVIDIA",
            model="NVIDIA H200",
            ram=64,
            driver_version="576.125.42",
            compute_cap=89,
            index=1,
        )
        items = [
            GPUInfo(
                vendor="AMD", model="AMD Mi355x", ram=64, driver_version="546.435.56"
            ),
            GPUInfo(
                vendor="NVIDIA",
                model="NVIDIA H200",
                ram=64,
                driver_version="576.125.42",
                compute_cap=89,
                index=1,
            ),
            GPUInfo(
                vendor="NVIDIA",
                model="NVIDIA H100",
                ram=64,
                driver_version="576.125.42",
                compute_cap=87,
                index=1,
            ),
        ]
        obj.compare(items)
        printer_echo_mock.assert_not_called()
