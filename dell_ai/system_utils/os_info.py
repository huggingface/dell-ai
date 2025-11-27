import platform

from pydantic import BaseModel


class OSInfo(BaseModel):
    hostname: str
    system: str
    kernel: str
    linux_distro: str | None
    linux_distro_version: str | None
    is_linux: bool


def get_os_info():
    uname = platform.uname()
    try:
        os_release = platform.freedesktop_os_release()
    except:
        os_release = {}
    return OSInfo(
        hostname=uname.node,
        system=uname.system,
        kernel=uname.release,
        linux_distro=os_release.get("ID"),
        linux_distro_version=os_release.get("VERSION_ID"),
        is_linux=uname.system == "Linux",
    )


if __name__ == "__main__":
    print(get_os_info().model_dump_json(indent=2))
