from unittest.mock import call
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
    assert get_product_name() == None


def test_get_product_prefix():
    assert get_product_prefix("PowerEdge R760xa") == "r760xa"
    assert get_product_prefix("Some random name") == None
    assert get_product_prefix(None) == None


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

def test_os_info_compare_success(typer_echo_mock):
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

    typer_echo_mock.assert_not_called()


def test_os_info_compare_failure(typer_echo_mock):
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
    for tag, attr_name, self_value, supported_values in [
        ("Kernel", "kernel", "5.10.0-custom", ["6.8.0-42-generic", "6.5.0-15-generic"]),
        ("Linux Distro", "linux_distro", "Debian", ["Ubuntu", "Fedora"]),
        ("Linux Distro Version", "linux_distro_version", "11", ["22.04", "40"]),
    ]:
        calls.append(
            call(
                f"Expected {tag} '{self_value}' not found in {attr_name}: Supported {supported_values}"
            )
        )

    typer_echo_mock.assert_has_calls(calls=calls, any_order=True)
