# KIAT Drone Detector Prototype

The local PC runs the virtual environment, CPU-only inference, and UART transfer to the iCE40 FPGA. Train models separately on the supercomputer GPU, then copy the exported model weights to this project for local inference.

## Local setup

```powershell
& 'C:\Users\이상민\AppData\Local\Programs\Python\Python311\python.exe' -m venv .venv --system-site-packages
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:YOLO_CONFIG_DIR = (Resolve-Path .runtime).Path
```

`YOLO_CONFIG_DIR` keeps Ultralytics settings inside the repository rather than the user profile. The verified local PyTorch installation is CPU-only; no CUDA or NVIDIA GPU is required for the simulator or inference.
