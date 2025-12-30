from unittest.mock import call

from dell_ai.system_utils.base import Printer
from dell_ai.system_utils.os_info import (
    OSInfo,
    get_os_info,
    get_product_name,
    get_product_prefix,
)


def test_get_product_name(patched_platform):
    assert get_product_name() == "PowerEdge R760xa"


def test_no_product_name(fp):
    fp.register(["dmidecode", fp.any()], stdout="")
    assert get_product_name() == ""

    fp.register(["dmidecode", fp.any()], returncode=1)
    assert get_product_name() is None


def test_get_product_prefix():
    assert get_product_prefix("PowerEdge R760xa") == "r760xa"
    assert get_product_prefix("Some random name") is None
    assert get_product_prefix(None) is None


def test_get_os_info(patched_platform):
    assert get_os_info() == OSInfo(
        hostname="deh-r760xaL40-53",
        system="Linux",
        kernel="6.8.0-88-generic",
        linux_distro="ubuntu",
        linux_distro_version="24.04",
        is_linux=True,
        product_name="PowerEdge R760xa",
        product_prefix="r760xa",
    )


def test_os_info_compare_success(printer_echo_mock):
    success = OSInfo(
        hostname="node-01",
        system="Linux",
        kernel="6.8.0-42-generic",
        linux_distro="Ubuntu",
        linux_distro_version="22.04",
        is_linux=True,
        product_name="SomeProduct",
        product_prefix="SPX",
    )

    others = [
        OSInfo(
            hostname="node-02",
            system="Linux",
            kernel="6.8.0-42-generic",
            linux_distro="Ubuntu",
            linux_distro_version="22.04",
            is_linux=True,
            product_name="SomeProduct",
            product_prefix="SPX",
        ),
        OSInfo(
            hostname="node-03",
            system="Linux",
            kernel="6.5.0-15-generic",
            linux_distro="Ubuntu",
            linux_distro_version="24.04",
            is_linux=True,
            product_name="AnotherProduct",
            product_prefix="APX",
        ),
    ]

    success.compare(others)

    printer_echo_mock.assert_not_called()


def test_os_info_compare_failure(printer_echo_mock):
    failure = OSInfo(
        hostname="node-01",
        system="Linux",
        kernel="5.10.0-custom",
        linux_distro="Debian",
        linux_distro_version="11",
        is_linux=True,
        product_name="SomeProduct",
        product_prefix="SPX",
    )

    others = [
        OSInfo(
            hostname="node-02",
            system="Linux",
            kernel="6.8.0-42-generic",
            linux_distro="Ubuntu",
            linux_distro_version="22.04",
            is_linux=True,
            product_name="SomeProduct",
            product_prefix="SPX",
        ),
        OSInfo(
            hostname="node-03",
            system="Linux",
            kernel="6.5.0-15-generic",
            linux_distro="Fedora",
            linux_distro_version="40",
            is_linux=True,
            product_name="AnotherProduct",
            product_prefix="APX",
        ),
    ]

    failure.compare(others)

    calls = []
    for tag, attr_name, self_value, supported_values, level in [
        (
            "Kernel",
            "kernel",
            "5.10.0-custom",
            ["6.8.0-42-generic", "6.5.0-15-generic"],
            "warn",
        ),
        ("Linux Distro", "linux_distro", "Debian", ["Ubuntu", "Fedora"], "error"),
        ("Linux Distro Version", "linux_distro_version", "11", ["22.04", "40"], "info"),
    ]:
        if attr_name == "linux_distro_version":
            calls.append(
                call(
                    Printer.minimum_styled(
                        tag=tag,
                        attr_name=attr_name,
                        self_value=self_value,
                        supported_values=supported_values,
                    ),
                    level=level,
                )
            )
            continue
        calls.append(
            call(
                Printer.list_compare_styled(
                    tag=tag,
                    attr_name=attr_name,
                    self_value=self_value,
                    supported_values=supported_values,
                ),
                level=level,
            )
        )

    printer_echo_mock.assert_has_calls(calls=calls, any_order=True)
