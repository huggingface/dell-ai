from dell_ai.system_utils.base import cmd_stdout
from dell_ai.system_utils.gpu_info.accelerator import AcceleratorInfo
from dell_ai.system_utils.gpu_info.gpu_info import GPUInfo
from dell_ai.system_utils.gpu_info.info_getter.abstract_getter import GetterClass


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
