import re
from abc import abstractmethod
from typing import Dict, List, Literal, Tuple, Union

from dell_ai.system_utils.helpers import cmd_stdout
from pydantic import BaseModel, RootModel


class NvidiaDriverInfo(BaseModel):
    cuda_version_from_nvidia_smi: str | None= None
    driver_version: str | None = None
    nvidia_container_toolkit_version: str | None = None
    nvidia_ctk_version: str | None = None


class AmdDriverInfo(BaseModel):
    cuda_version_from_rocm_smi: str | None = None
    driver_version: str | None = None


SoftwareDriverInfo = RootModel[
    Dict[Literal["nvidia", "amd", "intel"], Union[NvidiaDriverInfo, AmdDriverInfo]]
]


class AcceleratorInfo(BaseModel):
    driver_version: str
    name: str

Accelerator = RootModel[Dict[Literal["nvidia", "amd", "intel"], List[AcceleratorInfo]]]


class GPUInfo(BaseModel):
    vendor: Literal["NVIDIA", "AMD", "INTEL"] | None = None
    model: str | None = None
    # count: int | None = None
    ram: int | None = None
    driver_version: str | None = None
    compute_cap: int | None = None
    index: int | None = None

class GPUInfoPopulater:
    def __init__(self) -> None:
        self.details: Union[NvidiaDriverInfo, AmdDriverInfo] = NvidiaDriverInfo()
        self.collect_gpu_info()

    @abstractmethod
    def collect_gpu_info(self):
        raise NotImplementedError()
    
    @abstractmethod
    def get_software_driver_info(self):
        raise NotImplementedError()


class AMDInfoPopulater(GPUInfoPopulater):
    # not implemented
    pass


class IntelInfoPopulater(GPUInfoPopulater):
    # not implemented
    pass


class NvidiaInfoPopulater(GPUInfoPopulater):
    NVIDIA_SMI_REGEX = r"CUDA Version: ([\d\.]+)"
    NVIDIA_CTK_REGEX = r"NVIDIA Container Toolkit CLI version (\d+\.\d+\.\d+)"
    KUBECTL_CTK_REGEX = r"nvcr.io/nvidia/k8s/container-toolkit:v(\d+\.\d+\.\d+)-.+"

    def __init__(self) -> None:
        self.details: NvidiaDriverInfo = NvidiaDriverInfo()
        self.collect_gpu_info()
        
    def get_software_driver_info(self) -> SoftwareDriverInfo:
        return SoftwareDriverInfo.model_validate({"nvidia": self.details.model_dump()})

    def collect_gpu_info(self):
        self.smi_get_cuda()

    def smi_get_cuda(self):
        nvidia_smi_out = cmd_stdout(["nvidia-smi"])
        if nvidia_smi_out is None:
            return
        # use regex to parse
        match = re.search(self.NVIDIA_SMI_REGEX, nvidia_smi_out)
        if match is not None:
            self.details.cuda_version_from_nvidia_smi = match.group(1)

    def get_ctk_version(self):
        # try nvidia-ctk
        ctk_version = self.nvidia_ctk_version()
        # if nvidia-ctk not found, try kubectl get node
        if ctk_version is None:
            ctk_version = self.kubectl_ctk_version()
        self.details.nvidia_ctk_version = ctk_version

    def nvidia_ctk_version(self):
        output = cmd_stdout(["nvidia-ctk", "--version"])
        if output is None:
            return None
        match = re.search(self.NVIDIA_CTK_REGEX, output.splitlines()[0])
        if match:
            return match.group(1)

    def kubectl_ctk_version(self):
        output = cmd_stdout(["kubectl", "get", "node", "-o", "json"])
        if output is None:
            return None
        match = re.search(self.KUBECTL_CTK_REGEX, output)
        if match:
            return match.group(1)


class NvidiaInfoGetter():
    def __init__(self):
        self.gpu_info: List[GPUInfo] = []
        self.accelerator_info: List[AcceleratorInfo] = []
        self.collect_gpu_info()
    
    def collect_gpu_info(self):
        gpus = cmd_stdout(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,compute_cap",
                "--format=csv,noheader",
            ]
        )
        if gpus is None:
            return
        gpus = gpus.splitlines()

        for i, gpu in enumerate(gpus):
            values = gpu.split(",")
            gpu_info = GPUInfo(vendor="NVIDIA", index=i, model=values[0].strip(), driver_version=values[1].strip(), ram=int(values[2].removesuffix("MiB").strip()), compute_cap=int(values[3].replace(".", '')))
            self.gpu_info.append(gpu_info)
            accelerator_info = AcceleratorInfo(driver_version=values[1].strip(), name=values[0].strip())
            self.accelerator_info.append(accelerator_info)
    
    def get_gpu_info(self) -> List[GPUInfo]:
        return self.gpu_info
    
    def get_accelerator_info(self) -> List[AcceleratorInfo]:
        return self.accelerator_info


class GPUInfoGetter:
    VENDOR_MAP = {
        "10de": "NVIDIA",
        "1002": "AMD",
        "8086": "Intel",
    }
    CLASS_CODES = ["0302", "1200"]

    def __init__(self):
        self.vendors = self.get_gpu_vendors()
    
    @classmethod
    def get_gpu_vendors(cls) -> list[str]:
        vendors = set()
        output = cmd_stdout(["lspci", "-nn"])
        if output is None:
            return []
        lines = output.splitlines()
        for line in lines:
            # Check if class code matches GPU/accelerator
            if any(f"[{code}]" in line for code in cls.CLASS_CODES):
                # For each vendor id, check if current line matches
                for vendor_id in cls.VENDOR_MAP:
                    if f"[{vendor_id}:" in line:
                        # Add corresponding vendor to the set
                        vendors.add(cls.VENDOR_MAP[vendor_id])
        return sorted(list(vendors))

    def get_gpu_accelerator(self) -> Tuple[List[GPUInfo], Accelerator]:
        if "NVIDIA" in self.vendors:
            info_getter = NvidiaInfoGetter()
            gpus = info_getter.get_gpu_info()
            accelerators = info_getter.get_accelerator_info()
            return gpus, Accelerator.model_validate({"nvidia": accelerators})
        elif "AMD" in self.vendors:
            raise NotImplementedError()
        elif "INTEL" in self.vendors:
            raise NotImplementedError()
        else:
            raise NotImplementedError()
    
    def get_software_details(self) -> SoftwareDriverInfo:
        if "NVIDIA" in self.vendors:
            info_populater = NvidiaInfoPopulater()
            return info_populater.get_software_driver_info()
        elif "AMD" in self.vendors:
            raise NotImplementedError()
        elif "INTEL" in self.vendors:
            raise NotImplementedError()
        else:
            raise NotImplementedError()
        
def get_gpus_and_accelerator_info():
    return GPUInfoGetter().get_gpu_accelerator()    

def get_driver_info():
    return GPUInfoGetter().get_software_details()


if __name__ == "__main__":
    gpus, accelerators = get_gpus_and_accelerator_info()
    [print(gpu.model_dump_json(indent=2)) for gpu in gpus]
    print(accelerators.model_dump_json(indent=2))
    print(get_driver_info().model_dump_json(indent=2))