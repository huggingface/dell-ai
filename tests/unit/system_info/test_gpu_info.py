from pathlib import Path
from unittest.mock import call

import pytest

from dell_ai.system_utils.base import Printer
from dell_ai.system_utils.gpu_info import (
    Accelerator,
    AcceleratorInfo,
    AmdDriverInfo,
    GPUInfo,
    GPUInfoGetter,
    NvidiaDriverInfo,
    NvidiaInfoPopulater,
    get_driver_info,
    get_gpus_and_accelerator_info,
)

resource_folder = Path(__file__).parent / "resources"


@pytest.fixture
def lspci(fp):
    """
    Fixture to mock the lspci command for nvidia gpus
    """
    lspci_nvidia_out = resource_folder / "lspci_stdout_nvidia_gpu.txt"
    fp.register(["lspci", "-nn"], stdout=lspci_nvidia_out.read_text())
    yield


def test_get_gpu_vendors_pass(lspci):
    """
    Test vendor discovery using lscpi fixture
    """
    vendors = GPUInfoGetter.get_gpu_vendors()
    assert "NVIDIA" in vendors, "GPU entries are present"


def test_gpu_vendors_fail(fp):
    """
    Do not get any GPU vendor if lspci errors out
    """
    fp.register(["lspci", fp.any()], returncode=1)
    assert GPUInfoGetter.get_gpu_vendors() == []


def test_get_gpu_accelerator_fail(lspci, fp):
    """
    Test gpu and accelarator info is empty if nvidia-smi does not exist
    """
    fp.register(
        ["nvidia-smi", fp.any()], returncode=1, stdout="nvidia-smi: Command not found"
    )
    gpu, accelerators = GPUInfoGetter().get_gpu_accelerator()
    assert (gpu, accelerators.model_dump()) == ([], {"nvidia": []})


def test_get_gpu_accelerator_pass(commandline_patches):
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
            dict(driver_version="570.172.08", name="NVIDIA L40S"),
            dict(driver_version="570.172.08", name="NVIDIA L40S"),
            dict(driver_version="570.172.08", name="NVIDIA L40S"),
            dict(driver_version="570.172.08", name="NVIDIA L40S"),
        ]
    }


def test_nvidia_info_populator(commandline_patches):
    """
    Test all getters in the NvidiaInfoPopulater class
    """
    info = NvidiaInfoPopulater()
    assert info.details.cuda_version_from_nvidia_smi == "12.8"
    assert info.details.nvidia_ctk_version == "1.17.8"
    assert info.details.driver_version == "570.172.08"


def test_nvidia_info_populator_no_nvidia(fp):
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
    fp.register(["kubectl", fp.any()], returncode=1, occurrences=2)
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


def test_nvidia_info_populator_k8s_info(fp):
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
        occurrences=2,
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


def test_get_driver_info(commandline_patches):
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


def test_nvidia_driver_info_compare(printer_echo_mock):
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


def test_amd_driver_info_compare(printer_echo_mock):
    """
    Similar test as above for AMD
    """
    # all versions in allowed range
    success = AmdDriverInfo(
        cuda_version_from_rocm_smi="12.8", driver_version="566.125.15"
    )
    others = [
        AmdDriverInfo(cuda_version_from_rocm_smi="12.8", driver_version="594.564.56"),
        AmdDriverInfo(cuda_version_from_rocm_smi="13.0", driver_version="566.125.15"),
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


def test_accelerator_info_compare(printer_echo_mock):
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


def test_accelerator_compare(printer_echo_mock):
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
                    AcceleratorInfo(driver_version="562.124.12", name="Nvidia H200"),
                    AcceleratorInfo(driver_version="562.124.12", name="Nvidia H200"),
                ]
            }
        ),
        Accelerator.model_validate(
            {
                "nvidia": [
                    AcceleratorInfo(driver_version="563.124.12", name="Nvidia H200"),
                    AcceleratorInfo(driver_version="561.124.12", name="Nvidia H200"),
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


def test_gpu_info_compare_diff_vendor(printer_echo_mock):
    """ Test GPU info comparison when vendors tested are different, should generate error """
    
    obj = GPUInfo(
        vendor="NVIDIA",
        model="NVIDIA H200",
        ram=64,
        driver_version="576.125.42",
        compute_cap=89,
        index=1,
    )
    amd_items = [
        GPUInfo(vendor="AMD", model="AMD Mi355x", ram=64, driver_version="546.435.56")
    ]
    obj.compare(amd_items)
    printer_echo_mock.assert_called_with(
        "Found no supported vendor configuration for vendor NVIDIA, supported ['AMD']",
        level="error",
    )


def test_gpu_info_compare_pass(printer_echo_mock):
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
        GPUInfo(vendor="AMD", model="AMD Mi355x", ram=64, driver_version="546.435.56"),
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
