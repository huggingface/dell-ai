import platform

from typing_extensions import Self

from dell_ai.system_utils.base import cmd_stdout, ComparableBaseModel


class OSInfo(ComparableBaseModel):
    def compare(self, other: Self):
        pass

    hostname: str
    system: str
    kernel: str
    linux_distro: str | None
    linux_distro_version: str | None
    is_linux: bool
    product_name: str | None
    product_prefix: str | None


def get_product_name() -> str | None:
    prod_name = cmd_stdout(["dmidecode", "-s", "system-product-name"])
    if prod_name is not None:
        return prod_name.strip()
    return None


def get_product_prefix(prod_name: str | None) -> str | None:
    if prod_name is None:
        return None
    if prod_name.startswith("PowerEdge"):
        return prod_name.removeprefix("PowerEdge").strip().lower()
    return None


def get_os_info():
    uname = platform.uname()
    try:
        os_release = platform.freedesktop_os_release()
    except:
        os_release = {}
    product_name = get_product_name()
    product_prefix = get_product_prefix(product_name)

    return OSInfo(
        hostname=uname.node,
        system=uname.system,
        kernel=uname.release,
        linux_distro=os_release.get("ID"),
        linux_distro_version=os_release.get("VERSION_ID"),
        is_linux=uname.system == "Linux",
        product_name=product_name,
        product_prefix=product_prefix,
    )


if __name__ == "__main__":  # pragma: no cover
    print(get_os_info().model_dump_json(indent=2))
