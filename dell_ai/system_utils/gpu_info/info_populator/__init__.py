import json
import platform
from abc import abstractmethod, ABC
from typing import Union, Dict

from dell_ai.system_utils.base import cmd_stdout
from dell_ai.system_utils.gpu_info.driver_info.amd_driver_info import AmdDriverInfo
from dell_ai.system_utils.gpu_info.driver_info.intel_driver_info import IntelDriverInfo
from dell_ai.system_utils.gpu_info.driver_info.nvidia_driver_info import (
    NvidiaDriverInfo,
)


class GPUInfoPopulater(ABC):
    """
    Abstract class for populating GPU info in the details property
    """
    vendor = "NVIDIA"

    def __init__(self) -> None:
        self.details: Union[NvidiaDriverInfo, AmdDriverInfo, IntelDriverInfo, None] = None
        if self.vendor == "NVIDIA":
            self.details = NvidiaDriverInfo()
        elif self.vendor == "AMD":
            self.details = AmdDriverInfo()
        elif self.vendor == "INTEL":
            self.details = IntelDriverInfo()
        self.collect_gpu_info()

    @abstractmethod
    def collect_gpu_info(self):
        raise NotImplementedError()

    def get_software_driver_info(
        self,
    ) -> Union[NvidiaDriverInfo, AmdDriverInfo, IntelDriverInfo]:
        return self.details

    @staticmethod
    def _get_kubectl_node() -> Dict:
        output = cmd_stdout(["kubectl", "get", "nodes", "-o", "json"])
        if output is not None:
            kubectl_output = json.loads(output)
            system_hostname = platform.uname().node.lower()
            for item in kubectl_output.get("items", []):
                if item.get("metadata", {}).get("name", "").lower() == system_hostname:
                    return item
        return {}

    @staticmethod
    def get_kubectl_label_for_node() -> Dict[str, str]:
        node = GPUInfoPopulater._get_kubectl_node()
        return node.get("metadata", {}).get("labels", {})

    @staticmethod
    def get_kubectl_allocatable_for_node() -> Dict[str, str]:
        node = GPUInfoPopulater._get_kubectl_node()
        return node.get("status", {}).get("allocatable", {})
