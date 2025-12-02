from dell_ai.system_utils.cpu_info import (
    CPUInfo,
    _recursive_parse_lscpu_out,
    get_cpu_info,
)


def test_recursive_parse_lscpu_out():
    item_list = [
        {"field": "key1", "data": "val1"},
        {
            "field": "key2",
            "data": "val2",
            "children": [{"field": "ckey3", "data": "val3"}],
        },
        {
            "field": "key4",
            "data": None,
            "children": [
                {"field": "ckey5", "data": "val5"},
                {
                    "field": "ckey6",
                    "data": "val6",
                    "children": [
                        {"field": "cckey7", "data": "val7"},
                        {
                            "field": "cckey8",
                            "data": "val8",
                            "children": [{"field": "ccckey9", "data": "val9"}],
                        },
                    ],
                },
            ],
        },
    ]
    expected_response = {
        "key1": "val1",
        "key2": "val2",
        "ckey3": "val3",
        "key4": None,
        "ckey5": "val5",
        "ckey6": "val6",
        "cckey7": "val7",
        "cckey8": "val8",
        "ccckey9": "val9",
    }
    assert expected_response == _recursive_parse_lscpu_out(
        item_list=item_list, parsed_dict={}
    ), "Response does not match"


def test_get_cpu_info_success(commandline_patches):
    cpu_info: CPUInfo | None = get_cpu_info()
    assert cpu_info == CPUInfo(
        cores_per_socket=32,
        threads_per_core=1,
        sockets=2,
        cpu_num=64,
        vendor="GenuineIntel",
    )
