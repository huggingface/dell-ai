import json
from typing import List

from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel, cmd_stdout


class CPUInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.more_than_at_least_one("cores_per_socket", others, "Cores Per Socket")
        self.more_than_at_least_one("threads_per_core", others, "Threads Per Core")
        self.more_than_at_least_one("sockets", others, "Sockets")
        self.more_than_at_least_one("cpu_num", others, "Number of CPUs")

    cores_per_socket: int | None = None
    threads_per_core: int | None = None
    sockets: int | None = None
    cpu_num: int | None = None
    vendor: str | None = None


def _recursive_parse_lscpu_out(item_list: List, parsed_dict):
    """
    Recursively parse the lscpu output and return a dictionary containing the parsed data.

    The item list is list of dictionary of the following format:
        {
            "field": "field_name",
            "data": "data",
            "children": [{"field": "child_field", "data": "child_data"}],
        }
    
    Parameters:
    item_list (List): A list of dictionaries containing lscpu output data.
    parsed_dict (dict): A dictionary to store the parsed data.

    Returns:
    dict: A dictionary containing the parsed lscpu output data.
    """
    
    for item in item_list:
        parsed_dict[item["field"]] = item["data"]
        parsed_dict = _recursive_parse_lscpu_out(
            item_list=item.get("children", []), parsed_dict=parsed_dict
        )
    return parsed_dict


def get_cpu_info() -> CPUInfo | None:
    """
    Returns the CPU information of the system. The returned information includes the number of cores per socket, threads per core, sockets, CPU number, and vendor.

    Returns:
    CPUInfo | None: The CPU information of the system, or None if the information cannot be retrieved.
    """
    
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
