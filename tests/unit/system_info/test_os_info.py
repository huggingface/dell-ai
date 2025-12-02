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
