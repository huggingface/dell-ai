from dell_ai.system_utils.system_info import get_system_info


def test_get_system_info(commandline_patches, mock_sys_info):
    """
    Test system info parsing from subprocess patches
    """
    info = get_system_info()
    assert info is not None
    assert info.model_dump() == mock_sys_info
