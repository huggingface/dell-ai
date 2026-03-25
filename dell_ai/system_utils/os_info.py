import json
import logging
from pathlib import Path
import platform
from typing import List

from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel, cmd_stdout

logger = logging.getLogger(__name__)

DMI_FILE_PATH = "/sys/class/dmi/id/product_name"

class OSInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.simple_list_compare("kernel", others, "Kernel", level="warn")
        self.simple_list_compare("linux_distro", others, "Linux Distro", level="error")
        self.more_than_at_least_one(
            "linux_distro_version", others, "Linux Distro Version"
        )

    hostname: str | None = None
    system: str
    kernel: str
    linux_distro: str | None
    linux_distro_version: str | None
    is_linux: bool
    product_name: str | None
    product_prefix: str | None


def get_product_name_from_hostnamectl():
    """
    Get the product name from hostnamectl
    """
    hostnamectl_output = cmd_stdout(["hostnamectl", "--json", "short"])
    if hostnamectl_output is not None:
        hardware_model = json.loads(hostnamectl_output).get("HardwareModel")
        if hardware_model is not None:
            return hardware_model.strip()


def get_product_name_from_dmi():
    """
    Get the product name from dmidecode
    """
    prod_name = cmd_stdout(["dmidecode", "-s", "system-product-name"])
    if prod_name is not None:
        return prod_name.strip()
    else:
        logger.warning(
            "dell-ai utils describe-system/check-system works without sudo, "
            "but elevated privileges may improve hardware identification on some systems."
        )


def get_product_name_from_dmi_file():
    """
    Get the product name from dmi file
    """
    try:
        path = Path(DMI_FILE_PATH)
        if path.exists():
            info = path.read_text().strip()
            if info:
                return info
    except Exception as e:
        logger.info(f"Failed to get product name from dmi file: {e}")
        return None


def get_product_name() -> str | None:
    """Get the product name of the system"""
    sources = [
        get_product_name_from_dmi_file,
        get_product_name_from_hostnamectl,
        get_product_name_from_dmi,
    ]
    for source in sources:
        prod_name = source()
        if prod_name is not None:
            return prod_name.strip()
    return None


def get_product_prefix(prod_name: str | None) -> str | None:
    """
    Get the product prefix of the system
    Format of prod_name should be 'PowerEdge <systemname>'
    """
    if prod_name is None:
        return None
    if prod_name.startswith("PowerEdge"):
        return prod_name.removeprefix("PowerEdge").strip().lower()
    return None


def get_os_info():
    """Get the OS information of the system"""
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
