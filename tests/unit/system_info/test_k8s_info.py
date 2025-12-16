from unittest.mock import call
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


def test_k8s_info_compare_success(typer_echo_mock):
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

    typer_echo_mock.assert_not_called()


def test_k8s_info_compare_failure(typer_echo_mock):
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
            "Expected Kubernetes Server Version 'v1.30.0' not found in server_version: Supported ['v1.28.1', 'v1.29.3']"
        ),
        call(
            "Expected Kubernetes Platform Version 'linux/ppc64le' not found in server_platform: Supported ['linux/amd64', 'linux/arm64']"
        ),
    ]

    assert typer_echo_mock.call_count >= 3

    typer_echo_mock.assert_has_calls(expected_simple_compare_calls, any_order=True)

    kubelet_call_found = False
    for c in typer_echo_mock.call_args_list:
        msg = c.args[0]
        if (
            "Found no matching node_kubelet_version" in msg
            and "v1.27.5" in msg  # self list content
            and "v1.28.1" in msg  # others content
            and "v1.29.3" in msg  # others content
        ):
            kubelet_call_found = True
            break

    assert kubelet_call_found, (
        "Expected a kubelet version mismatch message containing "
        "'Found no matching node_kubelet_version', self ['v1.27.5'], "
        "and supported versions ['v1.28.1', 'v1.29.3']"
    )
