import re

from dell_ai.system_utils.base import cmd_stdout
from dell_ai.system_utils.gpu_info.driver_info.nvidia_driver_info import (
    NvidiaDriverInfo,
)
from dell_ai.system_utils.gpu_info.info_populator import GPUInfoPopulater


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
        if (
            self.details.cuda_version_from_nvidia_smi is None
            or self.details.driver_version is None
        ):
            self.kubectl_get_cuda()
        self.get_ctk_version()
        self.get_nvidia_toolkit_version()

    def kubectl_get_cuda(self):
        kubectl_labels = self.get_kubectl_label_for_node()
        self.details.cuda_version_from_nvidia_smi = kubectl_labels.get(
            "nvidia.com/cuda.runtime-version.full"
        )
        self.details.driver_version = kubectl_labels.get(
            "nvidia.com/cuda.driver-version.full"
        )

    def smi_get_cuda(self):
        """
        From nvidia-smi output, obtain CUDA version and driver version
        """
        nvidia_smi_out = cmd_stdout(["nvidia-smi"])
        if nvidia_smi_out is not None:
            # use regex to parse
            smi_match = re.search(self.NVIDIA_SMI_REGEX, nvidia_smi_out)
            driver_match = re.search(self.DRIVER_REGEX, nvidia_smi_out)
        else:
            smi_match = re.search(self.NVIDIA_SMI_REGEX, "")
            driver_match = re.search(self.DRIVER_REGEX, "")
        if smi_match is not None:
            self.details.cuda_version_from_nvidia_smi = smi_match.group(1)
        if driver_match is not None:
            self.details.driver_version = driver_match.group(1)

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
