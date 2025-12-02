from typing import List

from dell_ai.system_utils.cpu_info import CPUInfo, get_cpu_info
from dell_ai.system_utils.gpu_info import (
    Accelerator,
    GPUInfo,
    SoftwareDriverInfo,
    get_driver_info,
    get_gpus_and_accelerator_info,
)
from dell_ai.system_utils.k8s_info import K8SInfo, get_kube_info
from dell_ai.system_utils.mem_info import MemInfo, get_mem_info
from dell_ai.system_utils.os_info import OSInfo, get_os_info
from dell_ai.system_utils.storage_info import StorageInfo, get_storage_info
from pydantic import BaseModel


class HardwareInfo(BaseModel):
    cpu: CPUInfo | None
    memory: MemInfo
    storage: StorageInfo


class ContainersAndK8sInfo(BaseModel):
    kubernetes: K8SInfo


class ROCMInfo(BaseModel):
    rocminfo_present: bool = False


class SoftwareInfo(BaseModel):
    amd_rocm: ROCMInfo
    containers_and_k8s: ContainersAndK8sInfo
    versions: SoftwareDriverInfo


class SystemInfo(BaseModel):
    os: OSInfo
    software: SoftwareInfo
    hardware: HardwareInfo
    gpus: List[GPUInfo]
    accelerators: Accelerator


def get_system_info() -> SystemInfo | None:
    os_info = get_os_info()

    if os_info.is_linux:
        hardware_info = HardwareInfo(
            cpu=get_cpu_info(), memory=get_mem_info(), storage=get_storage_info()
        )
        gpu_info, accelerator_info = get_gpus_and_accelerator_info()
        rocm_info = ROCMInfo(
            rocminfo_present="amd" in accelerator_info.model_dump().keys()
        )
        software_info = SoftwareInfo(
            amd_rocm=rocm_info,
            containers_and_k8s=ContainersAndK8sInfo(kubernetes=get_kube_info()),
            versions=get_driver_info(),
        )
        return SystemInfo(
            os=os_info,
            hardware=hardware_info,
            software=software_info,
            gpus=gpu_info,
            accelerators=accelerator_info,
        )
    return None


if __name__ == "__main__":  # pragma: no cover
    print(SystemInfo.model_json_schema())
    sysinfo = get_system_info()
    if sysinfo is not None:
        print(sysinfo.model_dump_json(indent=2))
