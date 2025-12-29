import itertools
from typing import List, Optional

from pydantic.experimental.missing_sentinel import MISSING
from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel, Printer
from dell_ai.system_utils.cpu_info import CPUInfo, get_cpu_info
from dell_ai.system_utils.gpu_info import (
    Accelerator,
    AmdDriverInfo,
    GPUInfo,
    IntelDriverInfo,
    NvidiaDriverInfo,
    get_driver_info,
    get_gpus_and_accelerator_info,
)
from dell_ai.system_utils.k8s_info import K8SInfo, get_kube_info
from dell_ai.system_utils.mem_info import MemInfo, get_mem_info
from dell_ai.system_utils.os_info import OSInfo, get_os_info
from dell_ai.system_utils.storage_info import StorageInfo, get_storage_info


class HardwareInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        if self.cpu is not None:
            self.cpu.compare([other.cpu for other in others if other.cpu is not None])
        self.memory.compare([other.memory for other in others])

    cpu: CPUInfo | None
    memory: MemInfo
    storage: StorageInfo


class ContainersAndK8sInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.kubernetes.compare([other.kubernetes for other in others])

    kubernetes: K8SInfo


class ROCMInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        pass

    rocminfo_present: bool = False


class SoftwareInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.containers_and_k8s.compare([other.containers_and_k8s for other in others])
        if self.nvidia is None and self.amd is None and self.intel is None:
            Printer.echo("No Supported GPU entry found", level="error")
        if self.nvidia is not None:
            self.nvidia.compare([other.nvidia for other in others if other.nvidia is not None])
        if self.amd is not None:
            self.amd.compare([other.amd for other in others if other.amd is not None])
        if self.intel is not None:
            self.intel.compare([other.intel for other in others if other.intel is not None])
        
    amd_rocm: ROCMInfo
    containers_and_k8s: ContainersAndK8sInfo
    nvidia: NvidiaDriverInfo | None | MISSING = MISSING
    amd: AmdDriverInfo | None | MISSING = MISSING
    intel: IntelDriverInfo | None | MISSING = MISSING


class SystemInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.os.compare([other.os for other in others])
        self.software.compare([other.software for other in others])
        self.hardware.compare([other.hardware for other in others])
        self.accelerators.compare([other.accelerators for other in others])
        # perform GPU comparison
        # 1. Length comparison
        available_gpu_lens = [len(other.gpus) for other in others]
        if len(self.gpus) not in available_gpu_lens:
            Printer.echo(
                f"GPU length {len(self.gpus)} is not tested {available_gpu_lens}", level="warn"
            )

        # 2. GPU to GPU comparison
        # Ignore if any of them are missing, raise info
        flattened_gpu_list = list(
            itertools.chain.from_iterable([other.gpus for other in others])
        )
        for gpu in self.gpus:
            gpu.compare(flattened_gpu_list)

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
        driver_info = get_driver_info()
        software_info = SoftwareInfo(
            amd_rocm=rocm_info,
            containers_and_k8s=ContainersAndK8sInfo(kubernetes=get_kube_info()),
            nvidia=driver_info.get("nvidia"), # type: ignore
            amd=driver_info.get("amd"), # type: ignore
            intel=driver_info.get("intel"), # type: ignore
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
