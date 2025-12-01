import json
from typing import List

from dell_ai.system_utils.helpers import cmd_stdout
from pydantic import BaseModel


class K8SInfo(BaseModel):
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


if __name__ == "__main__":
    print(get_kube_info().model_dump_json(indent=2))
