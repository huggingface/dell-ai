from typing import List

from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel


class AmdDriverInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.more_than_at_least_one(
            "cuda_version_from_rocm_smi",
            others,
            "CUDA version from ROCM SMI",
            level="error",
        )
        self.software_version_compare("driver_version", others, "Driver version")

    cuda_version_from_rocm_smi: str | None = None
    driver_version: str | None = None
