import json
import logging

from dell_ai.system_utils.base import cmd_stdout
from dell_ai.system_utils.gpu_info.accelerator import AcceleratorInfo
from dell_ai.system_utils.gpu_info.gpu_info import GPUInfo
from dell_ai.system_utils.gpu_info.info_getter.abstract_getter import GetterClass
from dell_ai.system_utils.gpu_info.info_populator import GPUInfoPopulater

logger = logging.getLogger(__name__)


class AmdInfoGetter(GetterClass):
    vendor = "AMD"

    def _parse_amd_smi_output(self, gpus_output):
        """Parse amd-smi JSON output with fallback handling."""
        try:
            return json.loads(gpus_output)
        except json.JSONDecodeError as e:
            logger.warning(f"Cannot decode amd-smi output. Error: {e}")
            return self._try_fallback_json_parse(gpus_output)

    @staticmethod
    def _try_fallback_json_parse(gpus_output):
        """Try to extract JSON from output by filtering irrelevant lines."""
        relevant_lines = ""
        starting_braces_found = False

        for line in gpus_output.split("\n"):
            if not line.startswith("{") and not starting_braces_found:
                continue
            else:
                starting_braces_found = True
                relevant_lines += line

        try:
            return json.loads(relevant_lines)
        except json.JSONDecodeError:
            logger.warning(
                "Cannot decode after trying irrelevant lines as well, trying kubectl"
            )
            return None

    @staticmethod
    def _extract_vram_size(vram_data):
        """Extract VRAM size from VRAM data."""
        if vram_data == "N/A":
            return None
        return int(vram_data.get("value"))

    def _process_gpu_item(self, gpu_item, index):
        """Process a single GPU item and create GPU and accelerator info objects."""
        compute_units = gpu_item.get("asic", {}).get("num_compute_units")
        vram_size = self._extract_vram_size(gpu_item.get("vram", {}).get("size", {}))
        market_name = gpu_item.get("asic", {}).get("market_name")
        driver_version = gpu_item.get("driver", {}).get("version")

        gpu_info = GPUInfo(
            vendor=self.vendor,
            index=gpu_item.get("gpu", index),
            model=market_name if market_name != "N/A" else "",
            driver_version=driver_version if driver_version != "N/A" else None,
            ram=vram_size,
            compute_cap=int(compute_units) if compute_units not in ("N/A", None) else 0,
        )

        accelerator_info = AcceleratorInfo(
            driver_version=driver_version
            if driver_version not in ("N/A", None)
            else "N/A",
            name=market_name if market_name not in ("N/A", None) else "N/A",
        )

        return gpu_info, accelerator_info

    @staticmethod
    def _parse_gpu_memory(gpu_memory):
        """Parse GPU memory string to integer value in MB."""
        return (
            int(gpu_memory.removesuffix("G")) * 1024
            if gpu_memory.endswith("G")
            else int(gpu_memory.removesuffix("M"))
        )

    @staticmethod
    def _get_gpu_name_from_labels(kubectl_labels):
        """Get GPU name from kubectl labels."""
        return kubectl_labels.get("amd.com/gpu.product-name", "").replace("_", " ")

    @staticmethod
    def _get_gpu_driver_version_from_labels(kubectl_labels):
        """Get GPU driver version from kubectl labels."""
        return kubectl_labels.get("amd.com/gpu.driver-version")

    def _update_gpu_info_from_labels(self, gpu_info, kubectl_labels, gpu_memory_int):
        """Update existing GPU info from kubectl labels."""
        kubectl_name = self._get_gpu_name_from_labels(kubectl_labels)
        if gpu_info.model in (None, "N/A", "") and kubectl_name:
            gpu_info.model = kubectl_name

        kubectl_driver_version = self._get_gpu_driver_version_from_labels(
            kubectl_labels
        )
        if gpu_info.driver_version in (None, "N/A") and kubectl_driver_version:
            gpu_info.driver_version = kubectl_driver_version

        if gpu_info.ram in (None, "N/A") and gpu_memory_int:
            gpu_info.ram = gpu_memory_int

        kubectl_compute_cap = int(kubectl_labels.get("amd.com/gpu.cu-count", 0))
        if gpu_info.compute_cap in (None, 0) and kubectl_compute_cap:
            gpu_info.compute_cap = kubectl_compute_cap

    def _update_accelerator_info_from_labels(self, accelerator_info, kubectl_labels):
        """Update existing accelerator info from kubectl labels."""
        kubectl_driver_version = self._get_gpu_driver_version_from_labels(
            kubectl_labels
        )
        if accelerator_info.driver_version in (None, "N/A") and kubectl_driver_version:
            accelerator_info.driver_version = kubectl_driver_version

        kubectl_name = self._get_gpu_name_from_labels(kubectl_labels)
        if accelerator_info.name in (None, "N/A") and kubectl_name:
            accelerator_info.name = kubectl_name

    def _create_gpu_info_from_labels(self, index, kubectl_labels, gpu_memory_int):
        """Create new GPU info from kubectl labels."""
        return GPUInfo(
            vendor=self.vendor,
            index=index,
            model=self._get_gpu_name_from_labels(kubectl_labels),
            driver_version=self._get_gpu_driver_version_from_labels(kubectl_labels),
            ram=gpu_memory_int,
            compute_cap=int(kubectl_labels.get("amd.com/gpu.cu-count", 0)),
        )

    def _create_accelerator_info_from_labels(self, kubectl_labels):
        """Create new accelerator info from kubectl labels."""
        return AcceleratorInfo(
            driver_version=self._get_gpu_driver_version_from_labels(kubectl_labels),
            name=self._get_gpu_name_from_labels(kubectl_labels),
        )

    def collect_gpu_info(self):
        gpus = cmd_stdout(["amd-smi", "static", "--json"])
        if gpus is None:
            self.collect_gpu_info_from_kubectl()
            return

        gpus_parsed = self._parse_amd_smi_output(gpus)
        if gpus_parsed is None:
            self.collect_gpu_info_from_kubectl()
            return

        for i, gpu_item in enumerate(gpus_parsed.get("gpu_data", [])):
            gpu_info, accelerator_info = self._process_gpu_item(gpu_item, i)
            self.gpu_info.append(gpu_info)
            self.accelerator_info.append(accelerator_info)

        self.collect_gpu_info_from_kubectl()

    def collect_gpu_info_from_kubectl(self):
        kubectl_labels = GPUInfoPopulater.get_kubectl_label_for_node()
        if kubectl_labels is None:
            return

        gpu_memory = kubectl_labels.get("amd.com/gpu.vram")
        if gpu_memory is not None:
            gpu_memory_int = self._parse_gpu_memory(gpu_memory)
        else:
            gpu_memory_int = None
        allocatable = GPUInfoPopulater.get_kubectl_allocatable_for_node()
        gpu_count = allocatable.get("amd.com/gpu", 0)

        if self.gpu_info and self.accelerator_info:
            self._update_existing_gpu_info(kubectl_labels, gpu_memory_int)
        else:
            self._create_new_gpu_info(gpu_count, kubectl_labels, gpu_memory_int)

    def _update_existing_gpu_info(self, kubectl_labels, gpu_memory_int):
        """Update existing GPU and accelerator info from kubectl labels."""
        for gpu_info in self.gpu_info:
            self._update_gpu_info_from_labels(gpu_info, kubectl_labels, gpu_memory_int)

        for accelerator_info in self.accelerator_info:
            self._update_accelerator_info_from_labels(accelerator_info, kubectl_labels)

    def _create_new_gpu_info(self, gpu_count, kubectl_labels, gpu_memory_int):
        """Create new GPU and accelerator info from kubectl labels."""
        for i in range(int(gpu_count)):
            gpu_info = self._create_gpu_info_from_labels(
                i, kubectl_labels, gpu_memory_int
            )
            self.gpu_info.append(gpu_info)

            accelerator_info = self._create_accelerator_info_from_labels(kubectl_labels)
            self.accelerator_info.append(accelerator_info)
