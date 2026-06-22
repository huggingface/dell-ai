from typing import Dict, List, Literal, Tuple, Union

from dell_ai.system_utils.base import Printer, cmd_stdout
from dell_ai.system_utils.gpu_info.accelerator import Accelerator
from dell_ai.system_utils.gpu_info.driver_info.amd_driver_info import AmdDriverInfo
from dell_ai.system_utils.gpu_info.driver_info.intel_driver_info import IntelDriverInfo
from dell_ai.system_utils.gpu_info.driver_info.nvidia_driver_info import (
    NvidiaDriverInfo,
)
from dell_ai.system_utils.gpu_info.gpu_info import GPUInfo
from dell_ai.system_utils.gpu_info.info_getter.nvidia_info_getter import (
    NvidiaInfoGetter,
)
from dell_ai.system_utils.gpu_info.info_populator.nvidia_info_populator import (
    NvidiaInfoPopulater,
)


class GPUInfoGetter:
    """
    Collated GPU info getter that checks which GPU is present and returns the information for that GPU type
    """

    VENDOR_MAP = {
        "10de": "NVIDIA",
        "1002": "AMD",
        "8086": "INTEL",
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
            pass  # to be implemented later, warning has already been raised
        elif "INTEL" in self.vendors:
            pass  # to be implemented later, warning has already been raised
        return ret_dict
