import re
from abc import abstractmethod
from typing import List, Literal, Tuple

from pydantic import BaseModel

from dell_ai.system_utils.helpers import cmd_stdout


class GpuInfoVendorBase(BaseModel):
    vendor: Literal["NVIDIA", "AMD", "INTEL"] | None = None
    model: str | None = None
    count: int | None = None
    ram: int | None = None
    driver_version: str | None = None


class GpuInfoNvidia(GpuInfoVendorBase):
    vendor: Literal["NVIDIA", "AMD", "INTEL"] | None = "NVIDIA"
    cuda_version: str | None = None
    ctk_version: str | None = None


class GPUInfo(BaseModel):
    details: GpuInfoVendorBase | GpuInfoNvidia
    vendors: list[str] = []


class GPUInfoPopulater:
    def __init__(self) -> None:
        self.details = GpuInfoVendorBase()
        self.collect_gpu_info()

    @abstractmethod
    def collect_gpu_info(self):
        raise NotImplementedError()


class AMDInfoPopulater(GPUInfoPopulater):
    pass


class IntelInfoPopulater(GPUInfoPopulater):
    pass


class NvidiaInfoPopulater(GPUInfoPopulater):
    NVIDIA_SMI_REGEX = r"CUDA Version: ([\d\.]+)"
    NVIDIA_CTK_REGEX = r"NVIDIA Container Toolkit CLI version (\d+\.\d+\.\d+)"
    KUBECTL_CTK_REGEX = r"nvcr.io/nvidia/k8s/container-toolkit:v(\d+\.\d+\.\d+)-.+"

    def __init__(self) -> None:
        self.details = GpuInfoNvidia()
        self.collect_gpu_info()

    def collect_gpu_info(self):
        self.smi_query_gpu()
        self.smi_get_cuda()

    def smi_get_cuda(self):
        nvidia_smi_out = cmd_stdout(["nvidia-smi"])
        if nvidia_smi_out is None:
            return
        # use regex to parse
        match = re.search(self.NVIDIA_SMI_REGEX, nvidia_smi_out)
        if match is not None:
            self.details.cuda_version = match.group(1)

    def smi_query_gpu(self):
        gpus = cmd_stdout(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total",
                "--format=csv,noheader",
            ]
        )
        if gpus is None:
            return
        gpus = gpus.splitlines()
        self.details.count = len(gpus)

        # select first value in list
        if len(gpus):
            values = gpus[0].split(",")
            self.details.model = values[0].strip()
            self.details.driver_version = values[1].strip()
            self.details.ram = int(values[2].removesuffix("MiB").strip())

    def get_ctk_version(self):
        # try nvidia-ctk
        ctk_version = self.nvidia_ctk_version()
        # if nvidia-ctk not found, try kubectl get node
        if ctk_version is None:
            ctk_version = self.kubectl_ctk_version()
        self.details.ctk_version = ctk_version

    def nvidia_ctk_version(self):
        output = cmd_stdout(["nvidia-ctk", "--version"])
        if output is None:
            return None
        match = re.search(self.NVIDIA_CTK_REGEX, output)
        if match:
            return match.group(1)

    def kubectl_ctk_version(self):
        output = cmd_stdout(["kubectl", "get", "node", "-o", "json"])
        if output is None:
            return None
        match = re.search(self.KUBECTL_CTK_REGEX, output)
        if match:
            return match.group(1)


class GPUInfoGetter:
    VENDOR_MAP = {
        "10de": "NVIDIA",
        "1002": "AMD",
        "8086": "Intel",
    }
    CLASS_CODES = ["0302", "1200"]

    def __init__(self) -> None:
        vendors, details = self.identify_vendor()
        self.gpu_info: GPUInfo = GPUInfo(vendors=vendors, details=details)

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

    def identify_vendor(self) -> Tuple[List[str], GpuInfoVendorBase | GpuInfoNvidia]:
        vendors = self.get_gpu_vendors()
        if "NVIDIA" in vendors:
            details = NvidiaInfoPopulater().details
        elif "AMD" in vendors:
            raise NotImplementedError()
        elif "INTEL" in vendors:
            raise NotImplementedError()
        return vendors, details


def get_gpu_info() -> GPUInfo:
    return GPUInfoGetter().gpu_info


if __name__ == "__main__":
    print(get_gpu_info().model_dump_json(indent=2))
