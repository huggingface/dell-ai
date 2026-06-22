import logging
from typing import Dict, List, Literal

from pydantic import RootModel
from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel, Printer

logger = logging.getLogger(__name__)


class AcceleratorInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.software_version_compare("driver_version", others, "Driver version")

    driver_version: str | None = None
    name: str | None = None


class Accelerator(RootModel):
    root: Dict[Literal["nvidia", "amd", "intel"], List[AcceleratorInfo]]

    def __iter__(self):
        return iter(self.root.items())

    def __getitem__(self, item):
        return self.root[item]

    def __contains__(self, item):
        return item in self.root.keys()

    def compare(self, others: List[Self]):
        """
        Compare against others by filtering against the root key, so that nvidia accelerator is
        only compared against other nvidia accelerator infos.

        Params:
            others (List): Other Accelerator objects
        """
        if len(self.root.keys()) > 1:
            logger.error(f"Found more than one root key {list(self.root.keys())}")
        else:
            _main_key = list(self.root.keys())[0]
            vals = []
            other_keys = []
            for other in others:
                for key in other.root:
                    if key not in other_keys:
                        other_keys.append(key)
                if _main_key in other.root:
                    val = other.root[_main_key]
                    vals.extend(val)
            if _main_key not in other_keys:
                Printer.echo(
                    Printer.list_compare_styled(
                        tag="Accelerator",
                        self_value=_main_key,
                        supported_values=other_keys,
                        attr_name="info",
                    ),
                    level="error",
                )
                return
            for accel_info in self.root.values():
                for accel in accel_info:
                    accel.compare(vals)
