from typing import List

from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel


class IntelDriverInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.more_than_at_least_one(
            "driver_version", others, "Driver version", level="error"
        )

    driver_version: str | None = None