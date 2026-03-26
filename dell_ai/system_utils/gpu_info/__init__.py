import logging
from typing import List, Literal

from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel, Printer
from dell_ai.system_utils.gpu_info.info_getter import GPUInfoGetter

logger = logging.getLogger(__name__)





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
