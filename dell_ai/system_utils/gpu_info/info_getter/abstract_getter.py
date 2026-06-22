from abc import ABC, abstractmethod
from typing import List

from dell_ai.system_utils.gpu_info.accelerator import AcceleratorInfo
from dell_ai.system_utils.gpu_info.gpu_info import GPUInfo


class GetterClass(ABC):
    vendor = None

    def __init__(self):
        super().__init__()
        self.gpu_info: List[GPUInfo] = []
        self.accelerator_info: List[AcceleratorInfo] = []
        self.collect_gpu_info()

    @abstractmethod
    def collect_gpu_info(self):
        raise NotImplementedError()

    def get_gpu_info(self) -> List[GPUInfo]:
        return self.gpu_info

    def get_accelerator_info(self) -> List[AcceleratorInfo]:
        return self.accelerator_info

    @abstractmethod
    def collect_gpu_info_from_kubectl(self):
        pass
