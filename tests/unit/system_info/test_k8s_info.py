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
