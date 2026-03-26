from unittest.mock import call

from dell_ai.system_utils.base import Printer
from dell_ai.system_utils.os_info import (
    OSInfo,
    get_os_info,
    get_product_name,
    get_product_prefix,
)
from dell_ai.system_utils import os_info



def test_get_product_name(patched_platform):
    """
    Test product name with patched dmidecode output
    """
    assert get_product_name() == "PowerEdge R760xa"


def test_no_product_name(fp, tmp_path, monkeypatch):
    """
    Test no output when dmidecode output is empty or dmidecode errors
    """
    dmi_file = tmp_path / "product_name"
    monkeypatch.setattr(os_info, "Path", lambda p: dmi_file if "product_name" in p else tmp_path / p)
    fp.register(["hostnamectl", fp.any()], returncode=1)

    fp.register(["dmidecode", fp.any()], stdout="")
    assert get_product_name() == ""

    fp.register(["dmidecode", fp.any()], returncode=1)
    assert get_product_name() is None


def test_get_product_name_fallback_to_dmi_file(fp, tmp_path, monkeypatch):
    """
    Test fallback to dmi file when dmidecode fails
    """
    fp.register(["dmidecode", fp.any()], returncode=1)
    fp.register(["hostnamectl", fp.any()], returncode=1)

    dmi_file = tmp_path / "product_name"
    dmi_file.write_text("PowerEdge R760xa\n")

    monkeypatch.setattr(os_info, "Path", lambda p: dmi_file if "product_name" in p else tmp_path / p)

    assert get_product_name() == "PowerEdge R760xa"


def test_get_product_name_fallback_to_hostnamectl(fp, tmp_path, monkeypatch):
    """
    Test fallback to hostnamectl when dmidecode and dmi file fail
    """
    import json

    fp.register(["dmidecode", fp.any()], returncode=1)
    fp.register(
        ["hostnamectl", "--json", "short"],
        stdout=json.dumps({"HardwareModel": "PowerEdge XE9680"})
    )

    dmi_file = tmp_path / "product_name"
    monkeypatch.setattr(os_info, "Path", lambda p: dmi_file if "product_name" in p else tmp_path / p)

    assert get_product_name() == "PowerEdge XE9680"


def test_get_product_name_all_sources_fail(fp, tmp_path, monkeypatch):
    """
    Test None returned when all sources fail
    """
    fp.register(["dmidecode", fp.any()], returncode=1)
    fp.register(["hostnamectl", fp.any()], returncode=1)

    dmi_file = tmp_path / "product_name"
    monkeypatch.setattr(os_info, "Path", lambda p: dmi_file if "product_name" in p else tmp_path / p)

    assert get_product_name() is None


def test_get_product_prefix():
    """
    Test prefix name computation based on input
    """
    assert get_product_prefix("PowerEdge R760xa") == "r760xa"
    assert get_product_prefix("Some random name") is None
    assert get_product_prefix(None) is None


def test_get_os_info(patched_platform):
    """
    Test passing os info getter
    """
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
    """
    Test OSInfo comparison success case, when all versions and platform info are tested
    """
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
    """
    Test failing comparison attributes are not in tested list
    """
    failure = OSInfo(
        hostname="node-01",
        system="Linux",
        kernel="5.10.0-custom", # different kernel
        linux_distro="Debian", # different distro
        linux_distro_version="11", # different version
        is_linux=True,
        product_name="PowerEdge XE9680",
        product_prefix="xe9680",
    )

    others = [
        OSInfo(
            system="Linux",
            kernel="6.8.0-42-generic",
            linux_distro="Ubuntu",
            linux_distro_version="22.04",
            is_linux=True,
            product_name="PowerEdge XE9680",
            product_prefix="xe9680",
        ),
        OSInfo(
            system="Linux",
            kernel="6.5.0-15-generic",
            linux_distro="Fedora",
            linux_distro_version="40",
            is_linux=True,
            product_name="PowerEdge XE9680",
            product_prefix="xe9680",
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
