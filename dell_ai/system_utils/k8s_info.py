import json
from typing import List, Set

from pydantic_extra_types.semantic_version import SemanticVersion
from typing_extensions import Self

from dell_ai.system_utils.base import ComparableBaseModel, Printer, cmd_stdout


class K8SInfo(ComparableBaseModel):
    def compare(self, others: List[Self]):
        self.software_version_compare(
            "server_version", others, "Kubernetes Server Version"
        )
        self.simple_list_compare(
            "server_platform", others, "Kubernetes Platform Version", level="error"
        )
        other_kubelet_versions: Set[str] = set()
        try:
            for other in others:
                for kubelet_version in other.node_kubelet_version:
                    other_kubelet_versions.add(
                        str(SemanticVersion.parse(kubelet_version.removeprefix("v")))
                    )
            min_kubelet_version = min(other_kubelet_versions)
            max_kubelet_version = max(other_kubelet_versions)
            for node_version in set(self.node_kubelet_version):
                parsed_node_version = SemanticVersion.parse(
                    node_version.removeprefix("v")
                )
                if parsed_node_version < min_kubelet_version:
                    Printer.echo(
                        f"Node Kubelet version {node_version} is lower than minimum supported kubelet version {min_kubelet_version}",
                        level="error",
                    )
                elif parsed_node_version > max_kubelet_version:
                    Printer.echo(
                        f"Node Kubelet version {node_version} is higher than maximum supported kubelet version {max_kubelet_version}",
                        level="warn",
                    )
        except ValueError as e:
            Printer.echo(f"Failed to parse kubelet version: {e}", level="error")

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
