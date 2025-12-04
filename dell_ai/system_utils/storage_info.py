from typing import List

from typing_extensions import Self

from dell_ai.system_utils.base import cmd_stdout, ComparableBaseModel
from pydantic import BaseModel


class ChildrenBlockDevice(BaseModel):
    mountpoint: str


class BlockDevice(ComparableBaseModel):
    def compare(self, other: Self):
        pass

    name: str
    size: str
    type: str

class BlockDeviceWithModel(BlockDevice):
    model: str


class ParentBlockDevice(BlockDeviceWithModel):
    children: List[BlockDevice] = []


class LsblkInfo(ComparableBaseModel):
    def compare(self, other: Self):
        pass

    blockdevices: List[ParentBlockDevice]


class StorageInfo(ComparableBaseModel):
    def compare(self, other: Self):
        pass

    lsblk: LsblkInfo


def get_storage_info():
    lsblk_output = cmd_stdout(
        ["lsblk", "-o", "name,model,size,type,mountpoint", "--json"]
    )
    if lsblk_output is None:
        lsblk_output = '{"blockdevices": []}'
    lsblk_info = LsblkInfo.model_validate_json(lsblk_output)
    return StorageInfo(lsblk=lsblk_info)


if __name__ == "__main__":  # pragma: no cover
    print(get_storage_info().model_dump_json(indent=2))