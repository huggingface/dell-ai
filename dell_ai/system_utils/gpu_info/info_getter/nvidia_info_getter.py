from dell_ai.system_utils.base import cmd_stdout
from dell_ai.system_utils.gpu_info.accelerator import AcceleratorInfo
from dell_ai.system_utils.gpu_info.gpu_info import GPUInfo
from dell_ai.system_utils.gpu_info.info_getter.abstract_getter import GetterClass
from dell_ai.system_utils.gpu_info.info_populator import GPUInfoPopulater


class NvidiaInfoGetter(GetterClass):
    vendor = "NVIDIA"

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
            self.collect_gpu_info_from_kubectl()
            return

        gpus = gpus.splitlines()

        for i, gpu in enumerate(gpus):
            values = gpu.split(",")
            gpu_info = GPUInfo(
                vendor=self.vendor,
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

    def collect_gpu_info_from_kubectl(self):
        """
        Fallback: use kubectl labels to obtain GPU info when nvidia-smi is unavailable
        """
        kubectl_labels = GPUInfoPopulater.get_kubectl_label_for_node()
        if not kubectl_labels:
            return

        gpu_name = kubectl_labels.get("nvidia.com/gpu.product", "")
        driver_version = kubectl_labels.get(
            "nvidia.com/cuda.driver-version.full",
            kubectl_labels.get("nvidia.com/driver.version", ""),
        )
        gpu_memory = kubectl_labels.get("nvidia.com/gpu.memory", "0")
        ram = int(gpu_memory) if gpu_memory else 0

        allocatable = GPUInfoPopulater.get_kubectl_allocatable_for_node()
        gpu_count = int(allocatable.get("nvidia.com/gpu", 0))

        for i in range(gpu_count):
            gpu_info = GPUInfo(
                vendor=self.vendor,
                index=i,
                model=gpu_name,
                driver_version=driver_version,
                ram=ram,
                compute_cap=0,
            )
            self.gpu_info.append(gpu_info)
            accelerator_info = AcceleratorInfo(
                driver_version=driver_version, name=gpu_name
            )
            self.accelerator_info.append(accelerator_info)
