import platform
from typing import List

from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel, cmd_stdout


class OSInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.simple_list_compare("kernel", others, "Kernel", level="warn")
        self.simple_list_compare("linux_distro", others, "Linux Distro", level="error")
        self.more_than_at_least_one(
            "linux_distro_version", others, "Linux Distro Version"
        )

    hostname: str
    system: str
    kernel: str
    linux_distro: str | None
    linux_distro_version: str | None
    is_linux: bool
    product_name: str | None
    product_prefix: str | None


def get_product_name() -> str | None:
    # TODO: Mention in notes, please install dmidecode
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
