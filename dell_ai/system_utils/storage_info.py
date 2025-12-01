import json
from typing import List
from pydantic import BaseModel

from dell_ai.system_utils.helpers import cmd_stdout

class ChildrenBlockDevice(BaseModel):
    mountpoint: str

class BlockDevice(BaseModel):
    model : str
    name: str
    size: str
    type: str

class ParentBlockDevice(BlockDevice):
    children: List[BlockDevice] = []

class LsblkInfo(BaseModel):
    blockdevices: List[ParentBlockDevice]

class StorageInfo(BaseModel):
    lsblk: LsblkInfo
    
def get_storage_info():
    lsblk_output = cmd_stdout(["lsblk", "-o", "name,model,size,type,mountpoint", "--json"])
    if lsblk_output is None: 
        lsblk_output = '{"blockdevices": []}'
    lsblk_info = LsblkInfo.model_validate_json(lsblk_output)
    return StorageInfo(lsblk=lsblk_info)
    