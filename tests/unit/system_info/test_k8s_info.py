from unittest.mock import call

from dell_ai.system_utils.base import Printer
from dell_ai.system_utils.k8s_info import K8SInfo, get_kube_info


def test_get_kube_info(commandline_patches):
    k8s_info = get_kube_info()
    assert k8s_info.server_platform == "linux/amd64"
    assert k8s_info.server_version == "v1.32.9"
    assert k8s_info.node_kubelet_version == ["v1.32.9"]


def test_kubectl_not_found(fp):
    fp.register(
        ["kubectl", fp.any()],
        stdout="kubectl: command not found",
        returncode=1,
        occurrences=2,
    )
    kubeinfo = get_kube_info()
    assert kubeinfo == K8SInfo(
        server_version=None, server_platform=None, node_kubelet_version=[]
    )


def test_k8s_info_compare_success(printer_echo_mock):
    success = K8SInfo(
        server_version="v1.29.3",
        server_platform="linux/amd64",
        node_kubelet_version=["v1.29.3", "v1.28.1"],
    )
    others = [
        K8SInfo(
            server_version="v1.29.3",
            server_platform="linux/amd64",
            node_kubelet_version=["v1.29.3"],
        ),
        K8SInfo(
            server_version="v1.28.1",
            server_platform="linux/arm64",
            node_kubelet_version=["v1.28.1", "v1.29.3"],
        ),
    ]

    success.compare(others)

    printer_echo_mock.assert_not_called()


def test_k8s_info_compare_failure(printer_echo_mock):
    failure = K8SInfo(
        server_version="v1.30.0",
        server_platform="linux/ppc64le",
        node_kubelet_version=["v1.27.5"],
    )

    others = [
        K8SInfo(
            server_version="v1.28.1",
            server_platform="linux/amd64",
            node_kubelet_version=["v1.28.1"],
        ),
        K8SInfo(
            server_version="v1.29.3",
            server_platform="linux/arm64",
            node_kubelet_version=["v1.29.3"],
        ),
    ]

    failure.compare(others)

    expected_simple_compare_calls = [
        call(
            Printer.list_compare_styled(tag="Kubernetes Server Version", attr_name="server_version", self_value="v1.30.0", supported_values=["v1.28.1", "v1.29.3"]), level="info"
        ),
        call(
            Printer.list_compare_styled(tag="Kubernetes Platform Version", attr_name="server_platform", self_value="linux/ppc64le", supported_values=["linux/amd64", "linux/arm64"]), level="info"
        )
    ]

    assert printer_echo_mock.call_count >= 3

    printer_echo_mock.assert_has_calls(expected_simple_compare_calls, any_order=True)

    kubelet_call_found = False
    for c in printer_echo_mock.call_args_list:
        msg = c.args[0]
        if (
            "v1.27.5" in msg  # self list content
            and "v1.28.1" in msg  # others content
            and "v1.29.3" in msg  # others content
        ):
            kubelet_call_found = True
            break

    assert kubelet_call_found
