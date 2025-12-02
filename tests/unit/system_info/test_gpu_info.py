from pathlib import Path

import pytest

from dell_ai.system_utils.gpu_info import (
    GPUInfo,
    GPUInfoGetter,
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
    fp.register(["nvidia-smi"], returncode=1, stdout="nvidia-smi: Command not found")
    fp.register(
        ["nvidia-ctk", fp.any()], returncode=1, stdout="nvidia-ctk: Command not found"
    )
    fp.register(["kubectl", fp.any()], returncode=1)
    info = NvidiaInfoPopulater()
    assert info.details.cuda_version_from_nvidia_smi == None
    assert info.details.driver_version == None
    assert info.details.nvidia_ctk_version == None


def test_nvidia_info_populator_k8s_info(fp):
    fp.register(["nvidia-smi"], returncode=1, stdout="nvidia-smi: Command not found")
    fp.register(
        ["nvidia-ctk", fp.any()], returncode=1, stdout="nvidia-ctk: Command not found"
    )
    fp.register(
        ["kubectl", "get", "nodes", "-o", "json"],
        stdout=(resource_folder / "kubectl_get_nodes.json").read_text(),
    )
    info = NvidiaInfoPopulater()
    assert info.details.cuda_version_from_nvidia_smi == None
    assert info.details.driver_version == None
    assert info.details.nvidia_ctk_version == "1.17.8"


def test_get_driver_info(commandline_patches):
    info = get_driver_info()
    assert info.model_dump() == {
        "nvidia": {
            "cuda_version_from_nvidia_smi": "12.8",
            "nvidia_ctk_version": "1.17.8",
            "driver_version": "570.172.08",
            "nvidia_container_toolkit_version": None,
        }
    }
