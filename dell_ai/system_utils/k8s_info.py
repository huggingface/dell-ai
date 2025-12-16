import json
from typing import List, Set

import typer
from typing_extensions import Self

from dell_ai.system_utils.base import cmd_stdout, ComparableBaseModel


class K8SInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.simple_list_compare("server_version", others, "Kubernetes Server Version")
        self.simple_list_compare(
            "server_platform", others, "Kubernetes Platform Version"
        )
        other_kubelet_versions: Set[str] = set()
        for other in others:
            for kubelet_version in other.node_kubelet_version:
                other_kubelet_versions.add(kubelet_version)
        if not len(
            set(self.node_kubelet_version).intersection(other_kubelet_versions)
        ):
            typer.echo(
                f"Found no matching node_kubelet_version {list(set(self.node_kubelet_version))} for supported {list(set(other_kubelet_versions))}"
            )

    server_version: str | None = None
    server_platform: str | None = None
    node_kubelet_version: List[str] = []


def get_kube_info() -> K8SInfo:
    kubelet_server_info = cmd_stdout(["kubectl", "version", "-o", "json"]) or "{}"
    kubelet_server_info_parsed = json.loads(kubelet_server_info).get(
        "serverVersion", {}
    )

    kubelet_info = cmd_stdout(["kubectl", "get", "nodes", "-o", "json"]) or "{}"
    kubelet_info_parsed = json.loads(kubelet_info).get("items", [])
    kubelet_versions = {
        node["status"]["nodeInfo"]["kubeletVersion"] for node in kubelet_info_parsed
    }
    return K8SInfo(
        server_version=kubelet_server_info_parsed.get("gitVersion"),
        server_platform=kubelet_server_info_parsed.get("platform"),
        node_kubelet_version=sorted(list(kubelet_versions)),
    )


if __name__ == "__main__":  # pragma: no cover
    print(get_kube_info().model_dump_json(indent=2))
