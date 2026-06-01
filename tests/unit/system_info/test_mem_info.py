from unittest.mock import call

from dell_ai.system_utils import mem_info
from dell_ai.system_utils.base import Printer
from dell_ai.system_utils.mem_info import MemInfo


def test_mem_info(commandline_patches):
    """
    Test mem info object population
    """
    meminfo = mem_info.get_mem_info()
    assert meminfo == mem_info.MemInfo(
        free_kb=1408361652, available_kb=1560040584, hugepages_free_kb=0
    )


def test_mem_info_compare_success(printer_echo_mock):
    """
    Test compare success case
    """
    success = MemInfo(
        free_kb=800_000,
        available_kb=1_600_000,
        hugepages_free_kb=4096,
    )

    others = [
        MemInfo(free_kb=700_000, available_kb=1_500_000, hugepages_free_kb=2048),
        MemInfo(free_kb=900_000, available_kb=1_700_000, hugepages_free_kb=1024),
    ]

    success.compare(others)

    printer_echo_mock.assert_not_called()


def test_mem_info_compare_failure(printer_echo_mock):
    """
    Test compare failure case
    """
    failure = MemInfo(
        free_kb=600_000,
        available_kb=1_400_000,
        hugepages_free_kb=512,
    )

    others = [
        MemInfo(free_kb=700_000, available_kb=1_500_000, hugepages_free_kb=1024),
        MemInfo(free_kb=900_000, available_kb=1_700_000, hugepages_free_kb=2048),
    ]

    failure.compare(others)

    calls = []
    for tag, attr_name, self_value, supported_values in [
        ("Free Memory KB", "free_kb", 600000, [700000, 900000]),
        ("Available Memory KB", "available_kb", 1400000, [1500000, 1700000]),
        ("Hugepages Memory Free KB", "hugepages_free_kb", 512, [1024, 2048]),
    ]:
        calls.append(
            call(
                Printer.minimum_styled(
                    tag=tag,
                    attr_name=attr_name,
                    self_value=self_value,
                    supported_values=supported_values,
                ),
                level="warn",
            )
        )

    printer_echo_mock.assert_has_calls(calls=calls, any_order=True)
