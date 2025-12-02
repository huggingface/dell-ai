import json
from pathlib import Path

from dell_ai.system_utils.system_info import get_system_info


   
def test_get_system_info(commandline_patches):
    resource_path = Path(__file__).parent / "resources"

    with open(resource_path / "system_info_expected.json", "r") as fp:
        expected = json.load(fp)
    info = get_system_info()
    assert info is not None
    assert info.model_dump() == expected