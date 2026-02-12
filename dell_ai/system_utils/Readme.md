# System Checks

This module focuses on adding modules that can obtain the system information where the user is running the CLI tool. Commonly available shell tools are used to populate the information.

## Structure

Each of these modules roughly follow the following structure of code

```python
# import all required modules
import ...

# Declare all schema objects
class CPU(ComparableBaseModel): # subclass of pydantic BaseModel
    ...

    def compare(self, others: List[Self]):
        # compare method to compare against other schema objects
        ...

# Helper functions to populate schema objects
def get_cpu_info():
    ...

# basic module level testing
if __name__ == "__main__":
    ...
```

## Modules

The following are the list of modules and what features they are targeted towards.

- [cpu_info.py](./cpu_info.py): CPU information

    Obtain the CPU information, like threads per core, cores per socket, sockets.
- [gpu_info.py](./gpu_info.py): GPU information

    Obtain the GPU information, like GPU driver version, GPU model, GPU memory, etc. This module is currently under development with complete implementation for Nvidia Drivers.

- [storage_info.py](./storage_info.py): Storage information

    Obtain the storage information like lsblk.

- [os_info.py](./os_info.py): OS information

    Obtain the OS information like OS version, kernel version, etc.

- [mem_info.py](./mem_info.py): Memory information

    Obtain the memory information like memory usage, swap usage, etc.

- [k8s_info.py](./k8s_info.py): Kubernetes information

    Obtain the Kubernetes information like Kubernetes version, node kubelet version.

- [system_info.py](./system_info.py): System information

    Aggregated class to compile schema objects from all the above modules.

- [base.py](./base.py): Base class for all modules

    Contains the implementation of the ComparableBaseModel, logging helpers, and comparison methods.

## CLI tools required for this module

1. **System Tools**: Tools that should be available in linux systems by default
    - `lscpu`
    - `lspci`
    - `lsblk`
    - `dmidecode`

2. **GPU specific tools**: Tools that should be available after GPU specific drivers are installed.
    - Nvidia Tools
        - `nvidia-smi`
        - `nvidia-ctk`
        - `/usr/bin/nvidia-container-runtime-hook`
    > AMD and intel systems are not implemented. Once they are, this section will be updated

3. **Kubernetes specific tools**: Tools that should be available after Kubernetes is installed
    - `kubectl`
    > Ensure that you are passing the setting the right Kubernetes config by setting the `KUBECONFIG` environment variable, for eg. `export KUBECONFIG=${HOME}/.kube/config`. This is useful if you are managing multiple clusters from the same machine. 
