from typing import List

from dell_ai.system_utils.base import cmd_stdout
from dell_ai.system_utils.gpu_info.accelerator import AcceleratorInfo
from dell_ai.system_utils.gpu_info.gpu_info import GPUInfo
from dell_ai.system_utils.gpu_info.info_populator import GPUInfoPopulater


class NvidiaInfoGetter:
    def __init__(self):
        self.gpu_info: List[GPUInfo] = []
        self.accelerator_info: List[AcceleratorInfo] = []
        self.collect_gpu_info()

    def collect_gpu_info(self):
        """
        Use nvidia-smi to obtain driver version, memory and compute cap of all GPUs
        """
        gpus = cmd_stdout(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,compute_cap",
                "--format=csv,noheader",
            ]
        )
        if gpus is None:
            kubectl_labels = GPUInfoPopulater.get_kubectl_label_for_node()
            if kubectl_labels is None:
                return
            for i in range(int(kubectl_labels.get("nvidia.com/gpu.count", 0))):
                gpu_info = GPUInfo(
                    vendor="NVIDIA",
                    index=i,
                    model=kubectl_labels.get("nvidia.com/gpu.product").replace(
                        "-", " "
                    ),
                    # since the product name from NVIDIA SMI has a space, and product name in kubectl doesn't
                    driver_version=kubectl_labels.get(
                        "nvidia.com/cuda.driver-version.full"
                    ),
                    ram=int(kubectl_labels.get("nvidia.com/gpu.memory", 0)),
                    compute_cap=int(
                        f"{kubectl_labels.get('nvidia.com/gpu.compute.major', 0)}{kubectl_labels.get('nvidia.com/gpu.compute.minor', 0)}"
                    ),
                )
                self.gpu_info.append(gpu_info)
                accelerator_info = AcceleratorInfo(
                    driver_version=kubectl_labels.get(
                        "nvidia.com/cuda.driver-version.full"
                    ),
                    name=kubectl_labels.get("nvidia.com/gpu.product"),
                )
                self.accelerator_info.append(accelerator_info)

            return

        gpus = gpus.splitlines()

        for i, gpu in enumerate(gpus):
            values = gpu.split(",")
            gpu_info = GPUInfo(
                vendor="NVIDIA",
                index=i,
                model=values[0].strip(),
                driver_version=values[1].strip(),
                ram=int(values[2].removesuffix("MiB").strip()),
                compute_cap=int(values[3].replace(".", "")),
            )
            self.gpu_info.append(gpu_info)
            accelerator_info = AcceleratorInfo(
                driver_version=values[1].strip(), name=values[0].strip()
            )
            self.accelerator_info.append(accelerator_info)

    def get_gpu_info(self) -> List[GPUInfo]:
        return self.gpu_info

    def get_accelerator_info(self) -> List[AcceleratorInfo]:
        return self.accelerator_info
