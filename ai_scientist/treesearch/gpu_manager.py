"""
GPU discovery and simple process-level allocation utilities.

Notes:
- Avoids importing torch; uses nvidia-smi or CUDA_VISIBLE_DEVICES as fallback
- Provides a minimal manager to reserve/release GPUs per process id
"""

import os
import subprocess
from typing import Dict, Set


class GPUManager:
    """Manages GPU allocation across processes."""

    def __init__(self, num_gpus: int):
        self.num_gpus = num_gpus
        self.available_gpus: Set[int] = set(range(num_gpus))
        self.gpu_assignments: Dict[str, int] = {}

    def acquire_gpu(self, process_id: str) -> int:
        """Assign a GPU to a process, returning the GPU id."""
        if not self.available_gpus:
            raise RuntimeError("No GPUs available")
        gpu_id = min(self.available_gpus)
        self.available_gpus.remove(gpu_id)
        self.gpu_assignments[process_id] = gpu_id
        return gpu_id

    def release_gpu(self, process_id: str) -> None:
        """Release a GPU previously assigned to a process."""
        if process_id in self.gpu_assignments:
            gpu_id = self.gpu_assignments[process_id]
            self.available_gpus.add(gpu_id)
            del self.gpu_assignments[process_id]


def get_gpu_count() -> int:
    """Return number of available NVIDIA GPUs without importing torch."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=gpu_name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=True,
        )
        gpus = result.stdout.strip().split("\n")
        return len(gpus) if gpus != [""] else 0
    except (subprocess.SubprocessError, FileNotFoundError):
        # Fallback to environment variable used by many schedulers/launchers
        cuda_visible_devices = os.environ.get("CUDA_VISIBLE_DEVICES")
        if cuda_visible_devices:
            devices = [d for d in cuda_visible_devices.split(",") if d and d != "-1"]
            return len(devices)
        return 0
