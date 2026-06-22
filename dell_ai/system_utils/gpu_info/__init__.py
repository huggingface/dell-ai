from dell_ai.system_utils.gpu_info.accelerator import Accelerator, AcceleratorInfo
from dell_ai.system_utils.gpu_info.driver_info.amd_driver_info import AmdDriverInfo
from dell_ai.system_utils.gpu_info.driver_info.intel_driver_info import IntelDriverInfo
from dell_ai.system_utils.gpu_info.driver_info.nvidia_driver_info import (
    NvidiaDriverInfo,
)
from dell_ai.system_utils.gpu_info.gpu_info import GPUInfo
from dell_ai.system_utils.gpu_info.info_getter import GPUInfoGetter
from dell_ai.system_utils.gpu_info.info_populator.nvidia_info_populator import (
    NvidiaInfoPopulater,
)

__all__ = [
    "Accelerator",
    "AcceleratorInfo",
    "AmdDriverInfo",
    "GPUInfo",
    "GPUInfoGetter",
    "IntelDriverInfo",
    "NvidiaDriverInfo",
    "NvidiaInfoPopulater",
    "get_driver_info",
    "get_gpus_and_accelerator_info",
]


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
