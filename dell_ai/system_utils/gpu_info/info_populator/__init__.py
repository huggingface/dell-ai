from abc import abstractmethod
from typing import Union

from dell_ai.system_utils.gpu_info.driver_info.amd_driver_info import AmdDriverInfo
from dell_ai.system_utils.gpu_info.driver_info.intel_driver_info import IntelDriverInfo
from dell_ai.system_utils.gpu_info.driver_info.nvidia_driver_info import NvidiaDriverInfo


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