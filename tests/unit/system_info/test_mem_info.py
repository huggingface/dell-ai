from dell_ai.system_utils import mem_info


def test_mem_info(commandline_patches):
    meminfo = mem_info.get_mem_info()
    assert meminfo == mem_info.MemInfo(
        free_kb=1408361652, available_kb=1560040584, hugepages_free_kb=0
    )
