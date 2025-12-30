from typing import List

from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel

MEMINFO_PATH = "/proc/meminfo"


class MemInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.more_than_at_least_one("free_kb", others, "Free Memory KB", level="warn")
        self.more_than_at_least_one(
            "available_kb", others, "Available Memory KB", level="warn"
        )
        self.more_than_at_least_one(
            "hugepages_free_kb", others, "Hugepages Memory Free KB", level="warn"
        )

    free_kb: int | None = None
    available_kb: int | None = None
    hugepages_free_kb: int | None = None


def get_mem_info():
    with open(MEMINFO_PATH) as f:
        meminfo_output = f.read().split("\n")

    meminfo_parsed = {}
    for line in meminfo_output:
        if line == "":
            continue
        line = line.split(":")
        meminfo_parsed[line[0]] = int(line[1].split()[0])

    return MemInfo(
        free_kb=meminfo_parsed.get("MemFree"),
        available_kb=meminfo_parsed.get("MemAvailable"),
        hugepages_free_kb=meminfo_parsed.get("HugePages_Free"),
    )


if __name__ == "__main__":  # pragma: no cover
    print(get_mem_info().model_dump_json(indent=2))
