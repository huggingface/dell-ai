import json
import platform
from abc import abstractmethod
from typing import Union, Dict

from dell_ai.system_utils.base import cmd_stdout

from dell_ai.system_utils.gpu_info.driver_info.amd_driver_info import AmdDriverInfo
from dell_ai.system_utils.gpu_info.driver_info.intel_driver_info import IntelDriverInfo
from dell_ai.system_utils.gpu_info.driver_info.nvidia_driver_info import (
    NvidiaDriverInfo,
)


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

    @staticmethod
    def get_kubectl_label_for_node() -> Dict[str, str]:
        output = cmd_stdout(["kubectl", "get", "nodes", "-o", "json"])
        if output is not None:
            kubectl_output = json.loads(output)
            # Extract labels from the node matching system hostname
            system_hostname = platform.uname().node.lower()
            for item in kubectl_output.get("items", []):
                if item.get("metadata", {}).get("name", "").lower() == system_hostname:
                    kubectl_labels = item.get("metadata", {}).get("labels", {})
                    return kubectl_labels
        return {}
