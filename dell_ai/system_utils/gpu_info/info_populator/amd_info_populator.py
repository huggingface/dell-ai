import json
import logging
import re

from dell_ai.system_utils.base import cmd_stdout
from dell_ai.system_utils.gpu_info.info_populator import GPUInfoPopulater

logger = logging.getLogger(__name__)


class AMDInfoPopulater(GPUInfoPopulater):
    vendor = "AMD"
    AMD_CTK_REGEX = r"Version: v(\d+\.\d+\.\d+)"

    def __init__(self) -> None:
        super().__init__()

    def collect_gpu_info(self):
        self.smi_get_cuda()
        if self.details.driver_version is None:
            self.kubectl_get_cuda()
        self.get_ctk_version()

    def smi_get_cuda(self):
        amd_smi_version = cmd_stdout(["amd-smi", "version", "--json"])
        try:
            amd_smi_version_dict = json.loads(amd_smi_version)[0]
        except (json.JSONDecodeError, TypeError, IndexError):
            logger.warning(f"Could not decode amd_smi_version {amd_smi_version}")
            return

        self.details.cuda_version_from_rocm_smi = amd_smi_version_dict["rocm_version"]
        if "error" not in amd_smi_version_dict["amdgpu_version"].lower():
            self.details.driver_version = amd_smi_version_dict["amdgpu_version"]

    def kubectl_get_cuda(self):
        kubectl_labels = self.get_kubectl_label_for_node()

        self.details.driver_version = kubectl_labels.get("amd.com/gpu.driver-version")

    def get_ctk_version(self):
        amd_ctk_version = cmd_stdout(["amd-ctk", "version"])
        if amd_ctk_version is not None:
            match = re.search(self.AMD_CTK_REGEX, amd_ctk_version.splitlines()[0])
            if match:
                self.details.amd_ctk_version = match.group(1)
