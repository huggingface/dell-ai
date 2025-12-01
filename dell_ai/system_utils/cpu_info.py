import json

from dell_ai.system_utils.helpers import cmd_stdout
from pydantic import BaseModel


class CPUInfo(BaseModel):
    cores_per_socket: int | None = None
    threads_per_core: int | None = None
    sockets: int | None = None
    cpu_num: int | None = None
    vendor: str | None = None


def get_cpu_info() -> CPUInfo | None:
    output = cmd_stdout(["lscpu", "--json"])
    if output is None:
        return output
    lscpu_output = json.loads(output)
    lscpu_parsed = {item["field"]: item["data"] for item in lscpu_output["lscpu"]}
    return CPUInfo(
        cores_per_socket=lscpu_parsed.get("Core(s) per socket:"),
        threads_per_core=lscpu_parsed.get("Thread(s) per core:"),
        sockets=lscpu_parsed.get("Socket(s):"),
        cpu_num=lscpu_parsed.get("CPU(s):"),
        vendor=lscpu_parsed.get("Vendor ID:"),
    )


if __name__ == "__main__":
    try:
        cpu_info_dict = get_cpu_info()
        if cpu_info_dict is not None:
            print(cpu_info_dict.model_dump_json(indent=2))
        else:
            print("Linux CPU info is None")
    except Exception as e:
        print(f"Failed to get Linux CPU info: {e}")
