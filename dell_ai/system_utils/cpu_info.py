import json
from typing import List

from typing_extensions import Self

from dell_ai.system_utils.base import cmd_stdout, ComparableBaseModel


class CPUInfo(ComparableBaseModel):
    def compare(self, other: Self):
        pass

    cores_per_socket: int | None = None
    threads_per_core: int | None = None
    sockets: int | None = None
    cpu_num: int | None = None
    vendor: str | None = None


def _recursive_parse_lscpu_out(item_list: List, parsed_dict):
    for item in item_list:
        parsed_dict[item["field"]] = item["data"]
        parsed_dict = _recursive_parse_lscpu_out(item_list=item.get("children", []), parsed_dict=parsed_dict)
    return parsed_dict


def get_cpu_info() -> CPUInfo | None:
    output = cmd_stdout(["lscpu", "--json"])
    if output is None:
        return output
    lscpu_output = json.loads(output)
    lscpu_parsed = _recursive_parse_lscpu_out(lscpu_output["lscpu"], {})
    return CPUInfo(
        cores_per_socket=lscpu_parsed.get("Core(s) per socket:"),
        threads_per_core=lscpu_parsed.get("Thread(s) per core:"),
        sockets=lscpu_parsed.get("Socket(s):"),
        cpu_num=lscpu_parsed.get("CPU(s):"),
        vendor=lscpu_parsed.get("Vendor ID:"),
    )


if __name__ == "__main__":  # pragma: no cover
    try:
        cpu_info_dict = get_cpu_info()
        if cpu_info_dict is not None:
            print(cpu_info_dict.model_dump_json(indent=2))
        else:
            print("Linux CPU info is None")
    except Exception as e:
        print(f"Failed to get Linux CPU info: {e}")
