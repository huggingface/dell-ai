from pydantic import BaseModel

from dell_ai.system_utils.cpu_info import CPUInfo, get_cpu_info
from dell_ai.system_utils.gpu_info import GPUInfo, get_gpu_info
from dell_ai.system_utils.k8s_info import K8SInfo, get_kube_info
from dell_ai.system_utils.mem_info import MemInfo, get_mem_info
from dell_ai.system_utils.os_info import OSInfo, get_os_info


class SystemInfo(BaseModel):
    os: OSInfo
    mem: MemInfo
    cpu: CPUInfo | None = None
    gpu: GPUInfo | None = None
    kubernetes: K8SInfo | None = None


def get_system_info() -> SystemInfo:
    os_info = get_os_info()
    if os_info.is_linux:
        return SystemInfo(
            os=os_info,
            mem=get_mem_info(),
            cpu=get_cpu_info(),
            gpu=get_gpu_info(),
            kubernetes=get_kube_info(),
        )
    else:
        return SystemInfo(
            os=os_info,
            mem=get_mem_info(),
            cpu=get_cpu_info(),
        )


if __name__ == "__main__":
    print(get_system_info().model_dump_json(indent=2))
