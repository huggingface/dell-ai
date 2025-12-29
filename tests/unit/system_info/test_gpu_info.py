from pathlib import Path

import pytest

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
    lspci_nvidia_out = resource_folder / "lspci_stdout_nvidia_gpu.txt"
    fp.register(["lspci", "-nn"], stdout=lspci_nvidia_out.read_text())
    yield


def test_get_gpu_vendors_pass(lspci):
    vendors = GPUInfoGetter.get_gpu_vendors()
    assert "NVIDIA" in vendors, "GPU entries are present"


def test_gpu_vendors_fail(fp):
    fp.register(["lspci", fp.any()], returncode=1)
    assert GPUInfoGetter.get_gpu_vendors() == []


def test_get_gpu_accelerator_fail(lspci, fp):
    fp.register(
        ["nvidia-smi", fp.any()], returncode=1, stdout="nvidia-smi: Command not found"
    )
    gpu, accelerators = GPUInfoGetter().get_gpu_accelerator()
    assert (gpu, accelerators.model_dump()) == ([], {"nvidia": []})


def test_get_gpu_accelerator_pass(commandline_patches):
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
    info = NvidiaInfoPopulater()
    assert info.details.cuda_version_from_nvidia_smi == "12.8"
    assert info.details.nvidia_ctk_version == "1.17.8"
    assert info.details.driver_version == "570.172.08"


def test_nvidia_info_populator_no_nvidia(fp):
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
    info = NvidiaInfoPopulater()
    assert info.details.cuda_version_from_nvidia_smi == None
    assert info.details.driver_version == None
    assert info.details.nvidia_ctk_version == None


def test_nvidia_info_populator_k8s_info(fp):
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
    info = NvidiaInfoPopulater()
    assert info.details.cuda_version_from_nvidia_smi == None
    assert info.details.driver_version == None
    assert info.details.nvidia_ctk_version == "1.17.8"


def test_get_driver_info(commandline_patches):
    info = get_driver_info()
    assert info == {
        "nvidia": NvidiaDriverInfo.model_validate({
            "cuda_version_from_nvidia_smi": "12.8",
            "nvidia_ctk_version": "1.17.8",
            "driver_version": "570.172.08",
            "nvidia_container_toolkit_version": None,
        })
    }


def test_nvidia_driver_info_compare(typer_echo_mock):
    success = NvidiaDriverInfo(
        cuda_version_from_nvidia_smi="12.8",
        driver_version="566.125.15",
        nvidia_container_toolkit_version="17.8",
    )
    others = [
        NvidiaDriverInfo(
            cuda_version_from_nvidia_smi="12.8",
            driver_version="594.564.56",
            nvidia_container_toolkit_version="17.8",
        ),
        NvidiaDriverInfo(
            cuda_version_from_nvidia_smi="13.0", driver_version="566.125.15"
        ),
    ]
    failure = NvidiaDriverInfo(
        cuda_version_from_nvidia_smi="11.0", driver_version="566.125.15"
    )

    success.compare(others)
    typer_echo_mock.assert_not_called()

    failure.compare(others)
    typer_echo_mock.assert_called_once_with(
        "Expected CUDA version from NVIDIA SMI '11.0' not found in cuda_version_from_nvidia_smi: Supported ['12.8', '13.0']"
    )


def test_amd_driver_info_compare(typer_echo_mock):
    success = AmdDriverInfo(
        cuda_version_from_rocm_smi="12.8", driver_version="566.125.15"
    )
    others = [
        AmdDriverInfo(cuda_version_from_rocm_smi="12.8", driver_version="594.564.56"),
        AmdDriverInfo(cuda_version_from_rocm_smi="13.0", driver_version="566.125.15"),
    ]
    failure = AmdDriverInfo(
        cuda_version_from_rocm_smi="11.0", driver_version="566.125.15"
    )

    success.compare(others)
    typer_echo_mock.assert_not_called()

    failure.compare(others)
    typer_echo_mock.assert_called_once_with(
        "Expected CUDA version from ROCM SMI '11.0' not found in cuda_version_from_rocm_smi: Supported ['12.8', '13.0']"
    )


def test_accelerator_info_compare(typer_echo_mock):
    success = AcceleratorInfo(driver_version="566.125.15", name="NVIDIA B200")
    others = [
        AcceleratorInfo(driver_version="594.564.56"),
        AcceleratorInfo(driver_version="566.125.15"),
    ]
    failure = AcceleratorInfo(driver_version="567.125.15")

    success.compare(others)
    typer_echo_mock.assert_not_called()

    failure.compare(others)
    typer_echo_mock.assert_called_once_with(
        "Expected Driver version '567.125.15' not found in driver_version: Supported ['594.564.56', '566.125.15']"
    )


def test_accelerator_compare(typer_echo_mock):
    obj = Accelerator.model_validate(
        {
            "nvidia": [
                AcceleratorInfo(driver_version="562.124.12", name="Nvidia H200"),
                AcceleratorInfo(driver_version="562.124.12", name="Nvidia H200"),
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
    obj.compare(items)

    typer_echo_mock.assert_not_called()

    amd_obj = Accelerator.model_validate(
        {
            "amd": [
                AcceleratorInfo(driver_version="562.124.12", name="AMD Mi355"),
                AcceleratorInfo(driver_version="562.124.12", name="AMD Mi355"),
            ]
        }
    )
    amd_obj.compare(items)
    typer_echo_mock.assert_called()
    typer_echo_mock.assert_called_with(
        "Accelerator info for amd not in supported list ['nvidia']"
    )


def test_gpu_info_compare_diff_vendor(typer_echo_mock):
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
    typer_echo_mock.assert_called_with(
        "Found no supported vendor configuration for vendor NVIDIA, supported ['AMD']"
    )


def test_gpu_info_compare_pass(typer_echo_mock):
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
    typer_echo_mock.assert_not_called()
