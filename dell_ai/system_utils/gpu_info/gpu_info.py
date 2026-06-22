from typing import List, Literal

from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel, Printer


class GPUInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        other_vendors = list(
            {other.vendor for other in others if other.vendor is not None}
        )
        relevant_others = [other for other in others if other.vendor == self.vendor]
        if not relevant_others:
            Printer.echo(
                f"Found no supported vendor configuration for vendor {self.vendor}, supported {other_vendors}",
                level="error",
            )
            return
        self.simple_list_compare("model", relevant_others, "Model", level="info")
        self.more_than_at_least_one("ram", relevant_others, "GPU RAM", level="warn")
        self.software_version_compare(
            "driver_version", relevant_others, "Driver Version"
        )
        self.more_than_at_least_one(
            "compute_cap", relevant_others, "Compute Cap", level="error"
        )

    vendor: Literal["NVIDIA", "AMD", "INTEL"] | None = None
    model: str | None = None
    # count: int | None = None
    ram: int | None = None
    driver_version: str | None = None
    compute_cap: int | None = None
    index: int | None = None
