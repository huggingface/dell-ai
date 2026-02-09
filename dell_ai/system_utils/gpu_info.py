import json
import logging
import re
import platform
from abc import abstractmethod
from typing import Dict, List, Literal, Tuple, Union

from pydantic import RootModel
from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel, Printer, cmd_stdout

logger = logging.getLogger(__name__)


class NvidiaDriverInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.more_than_at_least_one(
            "cuda_version_from_nvidia_smi",
            others,
            "CUDA version from NVIDIA SMI",
            level="error",
        )
        self.software_version_compare("driver_version", others, "Driver version")
        self.software_version_compare(
            "nvidia_container_toolkit_version",
            others,
            "NVIDIA Container Toolkit version",
        )
        self.software_version_compare(
            "nvidia_ctk_version", others, "NVIDIA CTK version"
        )

    cuda_version_from_nvidia_smi: str | None = None
    driver_version: str | None = None
    nvidia_container_toolkit_version: str | None = None
    nvidia_ctk_version: str | None = None


class AmdDriverInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.more_than_at_least_one(
            "cuda_version_from_rocm_smi",
            others,
            "CUDA version from ROCM SMI",
            level="error",
        )
        self.software_version_compare("driver_version", others, "Driver version")

    cuda_version_from_rocm_smi: str | None = None
    driver_version: str | None = None


class IntelDriverInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.more_than_at_least_one(
            "driver_version", others, "Driver version", level="error"
        )

    driver_version: str | None = None


class AcceleratorInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.software_version_compare("driver_version", others, "Driver version")

    driver_version: str | None = None
    name: str | None = None


class Accelerator(RootModel):
    root: Dict[Literal["nvidia", "amd", "intel"], List[AcceleratorInfo]]

    def __iter__(self):
        return iter(self.root.items())

    def __getitem__(self, item):
        return self.root[item]

    def __contains__(self, item):
        return item in self.root.keys()

    def compare(self, others: List[Self]):
        """
        Compare against others by filtering against the root key, so that nvidia accelerator is
        only compared against other nvidia accelerator infos.
        
        Params:
            others (List): Other Accelerator objects
        """
        if len(self.root.keys()) > 1:
            logger.error(f"Found more than one root key {list(self.root.keys())}")
        else:
            _main_key = list(self.root.keys())[0]
            vals = []
            other_keys = []
            for other in others:
                for key in other.root:
                    if key not in other_keys:
                        other_keys.append(key)
                if _main_key in other.root:
                    val = other.root[_main_key]
                    vals.extend(val)
            if _main_key not in other_keys:
                Printer.echo(
                    Printer.list_compare_styled(
                        tag="Accelerator",
                        self_value=_main_key,
                        supported_values=other_keys,
                        attr_name="info",
                    ),
                    level="error",
                )
                return
            for accel_info in self.root.values():
                for accel in accel_info:
                    accel.compare(vals)


class GPUInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        other_vendors = list(
            {other.vendor for other in others if other.vendor is not None}
        )
        relevant_others = [other for other in others if other.vendor == self.vendor]
        if not relevant_others:
            Printer.echo(
                f"Found no supported vendor configuration for vendor {self.vendor}, supported {other_vendors}",
                level="error",
            )
            return
        self.simple_list_compare("model", relevant_others, "Model", level="info")
        self.more_than_at_least_one("ram", relevant_others, "GPU RAM", level="warn")
        self.software_version_compare(
            "driver_version", relevant_others, "Driver Version"
        )
        self.more_than_at_least_one(
            "compute_cap", relevant_others, "Compute Cap", level="error"
        )

    vendor: Literal["NVIDIA", "AMD", "INTEL"] | None = None
    model: str | None = None
    # count: int | None = None
    ram: int | None = None
    driver_version: str | None = None
    compute_cap: int | None = None
    index: int | None = None


class GPUInfoPopulater:
    """
    Abstract class for populating GPU info in the details property
    """
    def __init__(self) -> None:
        self.details: Union[NvidiaDriverInfo, AmdDriverInfo, IntelDriverInfo] = (
            NvidiaDriverInfo()
        )
        self.collect_gpu_info()

    @abstractmethod
    def collect_gpu_info(self):
        raise NotImplementedError()

    def get_software_driver_info(
        self,
    ) -> Union[NvidiaDriverInfo, AmdDriverInfo, IntelDriverInfo]:
        return self.details


class AMDInfoPopulater(GPUInfoPopulater):
    # not implemented
    pass


class IntelInfoPopulater(GPUInfoPopulater):
    # not implemented
    pass


class NvidiaInfoPopulater(GPUInfoPopulater):
    NVIDIA_SMI_REGEX = r"CUDA Version: ([\d\.]+)"
    DRIVER_REGEX = r"Driver Version: (\d+\.\d+\.\d+)"
    NVIDIA_CTK_REGEX = r"NVIDIA Container Toolkit CLI version (\d+\.\d+\.\d+)"
    NVIDIA_CONTAINER_TOOLKIT_REGEX = (
        r"NVIDIA Container Runtime Hook version (\d+\.\d+\.\d+)"
    )
    KUBECTL_CTK_REGEX = r"nvcr.io/nvidia/k8s/container-toolkit:v(\d+\.\d+\.\d+).+"

    def __init__(self) -> None:
        super().__init__()
        self.details: NvidiaDriverInfo = NvidiaDriverInfo()
        self.collect_gpu_info()

    def collect_gpu_info(self):
        self.smi_get_cuda()
        self.get_ctk_version()
        self.get_nvidia_toolkit_version()

    def smi_get_cuda(self):
        """
        From nvidia-smi output, obtain CUDA version and driver version
        """
        nvidia_smi_out = cmd_stdout(["nvidia-smi"])
        if nvidia_smi_out is not None:
            # use regex to parse
            match = re.search(self.NVIDIA_SMI_REGEX, nvidia_smi_out)
        else:
            match = re.search(self.NVIDIA_SMI_REGEX, "")
            output = cmd_stdout(["kubectl", "get", "nodes", "-o", "json"])
            kubectl_labels = None
            if output is not None:
                kubectl_output = json.loads(output)
                # Extract labels from the node matching system hostname
                system_hostname = platform.uname().node.lower()
                for item in kubectl_output.get("items", []):
                    if item.get("metadata", {}).get("name", "").lower() == system_hostname:
                        kubectl_labels = item.get("metadata", {}).get("labels", {})
                        break
        if match is not None:
            self.details.cuda_version_from_nvidia_smi = match.group(1)
        else:
            if kubectl_labels is None:
                return
            cuda_version = kubectl_labels.get("nvidia.com/cuda.runtime-version.full")
            if cuda_version is not None:
                self.details.cuda_version_from_nvidia_smi = cuda_version
        if nvidia_smi_out is not None:
            match = re.search(self.DRIVER_REGEX, nvidia_smi_out)
        else:
            match = re.search(self.DRIVER_REGEX, "")
        if match is not None:
            self.details.driver_version = match.group(1)
        else:
            if kubectl_labels is None:
                return
            driver_version = kubectl_labels.get("nvidia.com/cuda.driver-version.full")
            if driver_version is not None:
                self.details.driver_version = driver_version

    def get_ctk_version(self):
        """
        Get Nvidia CTK version
        """
        # try nvidia-ctk
        ctk_version = self.nvidia_ctk_version()
        # if nvidia-ctk not found, try kubectl get node
        if ctk_version is None:
            ctk_version = self.kubectl_ctk_version()
        self.details.nvidia_ctk_version = ctk_version

    def get_nvidia_toolkit_version(self):
        """
        Populate Nvidia container toolkit version
        """
        self.details.nvidia_container_toolkit_version = (
            self.nvidia_container_toolkit_version()
        )

    def nvidia_ctk_version(self):
        """
        Use nvidia-ctk CLI tool to get CTK version
        """
        output = cmd_stdout(["nvidia-ctk", "--version"])
        if output is None:
            return None
        match = re.search(self.NVIDIA_CTK_REGEX, output.splitlines()[0])
        if match:
            return match.group(1)
        return None

    def nvidia_container_toolkit_version(self):
        """
        Use container runtime hook CLI tool to get version
        """
        output = cmd_stdout(["/usr/bin/nvidia-container-runtime-hook", "--version"])
        if output is None:
            return None
        match = re.search(self.NVIDIA_CONTAINER_TOOLKIT_REGEX, output.splitlines()[0])
        if match:
            return match.group(1)
        return None

    def kubectl_ctk_version(self):
        """
        Find Nvidia CTK version from node info
        """
        output = cmd_stdout(["kubectl", "get", "nodes", "-o", "json"])
        if output is None:
            return None
        match = re.search(self.KUBECTL_CTK_REGEX, output)
        if match:
            return match.group(1)
        return None


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
            output = cmd_stdout(["kubectl", "get", "nodes", "-o", "json"])
            kubectl_labels = None
            if output is not None:
                kubectl_output = json.loads(output)
                # Extract labels from the node matching system hostname
                system_hostname = platform.uname().node.lower()
                for item in kubectl_output.get("items", []):
                    print(item.get("metadata", {}).get("name", "").lower())
                    if item.get("metadata", {}).get("name", "").lower() == system_hostname:
                        kubectl_labels = item.get("metadata", {}).get("labels")
                        break
            print(kubectl_labels)
            if kubectl_labels is None:
                return
            for i in range(int(kubectl_labels.get("nvidia.com/gpu.count", 0))):
                gpu_info = GPUInfo(
                    vendor="NVIDIA",
                    index=i,
                    model=kubectl_labels.get("nvidia.com/gpu.product"),
                    driver_version=kubectl_labels.get("nvidia.com/cuda.driver-version.full"),
                    ram=int(kubectl_labels.get("nvidia.com/gpu.memory", 0)),
                    compute_cap=int(f"{kubectl_labels.get('nvidia.com/gpu.compute.major', 0)}{kubectl_labels.get('nvidia.com/gpu.compute.minor', 0)}"),
                )
                self.gpu_info.append(gpu_info)
                accelerator_info = AcceleratorInfo(
                    driver_version=kubectl_labels.get("nvidia.com/cuda.driver-version.full"), name=kubectl_labels.get("nvidia.com/gpu.product")
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


class GPUInfoGetter:
    """
    Collated GPU info getter that checks which GPU is present and returns the information for that GPU type
    """
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
        """
        Get GPU vendor type to define which type of output to return
        """
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
        """
        On the basis of vendor, return GPU and accelerator information
        """
        if "NVIDIA" in self.vendors:
            info_getter = NvidiaInfoGetter()
            gpus = info_getter.get_gpu_info()
            accelerators = info_getter.get_accelerator_info()
            return gpus, Accelerator.model_validate({"nvidia": accelerators})
        elif "AMD" in self.vendors:
            Printer.echo("AMD GPUs found, but not supported yet", level="warn")
            return [], Accelerator.model_validate({"amd": []})
        elif "INTEL" in self.vendors:
            Printer.echo("Intel GPUs found, but not supported yet", level="warn")
            return [], Accelerator.model_validate({"intel": []})
        else:
            Printer.echo("No GPUs found, not supported", level="warn")
            return [], Accelerator.model_validate({})

    def get_software_details(
        self,
    ) -> Dict[
        Literal["nvidia", "amd", "intel"],
        Union[NvidiaDriverInfo, AmdDriverInfo, IntelDriverInfo],
    ]:
        """
        Get software info according to vendor type
        """
        ret_dict: Dict[
            Literal["nvidia", "amd", "intel"],
            Union[NvidiaDriverInfo, AmdDriverInfo, IntelDriverInfo],
        ] = {}
        if "NVIDIA" in self.vendors:
            info_populater = NvidiaInfoPopulater()
            ret_dict["nvidia"] = info_populater.get_software_driver_info()
        elif "AMD" in self.vendors:
            pass # to be implemented later, warning has already been raised
        elif "INTEL" in self.vendors:
            pass # to be implemented later, warning has already been raised
        return ret_dict


def get_gpus_and_accelerator_info():
    """
    Aggregated getter for GPU and accelerator information. Returns a tuple of GPUInfo and Accelerator
    """
    return GPUInfoGetter().get_gpu_accelerator()


def get_driver_info():
    """
    Aggregated getter for driver information.
    """
    return GPUInfoGetter().get_software_details()


if __name__ == "__main__":  # pragma: no cover
    gpus, accelerators = get_gpus_and_accelerator_info()
    [print(gpu.model_dump_json(indent=2)) for gpu in gpus]
    print(accelerators.model_dump_json(indent=2))
    for vendor, driver_info in get_driver_info().items():
        print(f"{vendor}: {driver_info.model_dump_json(indent=2)}")
