from dell_ai.system_utils.gpu_info.driver_info.amd_driver_info import AmdDriverInfo
from dell_ai.system_utils.gpu_info.info_populator import GPUInfoPopulater


class AMDInfoPopulater(GPUInfoPopulater):
    def __init__(self) -> None:
        super().__init__()
        self.details: AmdDriverInfo = AmdDriverInfo()
        self.collect_gpu_info()

    def collect_gpu_info(self):
        self.smi_get_cuda()
        if (
            self.details.driver_version is None
            or self.details.cuda_version_from_rocm_smi is None
        ):
            self.kubectl_get_cuda()

    def smi_get_cuda(self):
        pass

    def kubectl_get_cuda(self):
        kubectl_labels = self.get_kubectl_label_for_node()

        self.details.cuda_version_from_rocm_smi = kubectl_labels.get()