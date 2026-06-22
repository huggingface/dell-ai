from typing import List

from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel


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
