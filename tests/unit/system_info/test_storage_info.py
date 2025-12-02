from dell_ai.system_utils.storage_info import get_storage_info


def test_get_storage_info(commandline_patches):
    assert get_storage_info().model_dump() == {
        "lsblk": {
            "blockdevices": [
                {
                    "name": "nvme0n1",
                    "size": "894.2G",
                    "type": "disk",
                    "model": "Dell BOSS-N1",
                    "children": [
                        {"name": "nvme0n1p1", "size": "200G", "type": "part"},
                        {"name": "nvme0n1p2", "size": "20G", "type": "part"},
                        {"name": "nvme0n1p3", "size": "12G", "type": "part"},
                        {"name": "nvme0n1p4", "size": "662.2G", "type": "part"},
                    ],
                },
                {
                    "name": "nvme1n1",
                    "size": "1.7T",
                    "type": "disk",
                    "model": "Dell Ent NVMe CM6 RI 1.92TB",
                    "children": [{"name": "nvme1n1p1", "size": "1.7T", "type": "part"}],
                },
                {
                    "name": "nvme2n1",
                    "size": "1.7T",
                    "type": "disk",
                    "model": "Dell Ent NVMe CM6 RI 1.92TB",
                    "children": [],
                },
            ]
        }
    }
