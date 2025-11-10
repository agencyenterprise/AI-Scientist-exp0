# AE-Scientist


## Setup (Local)

1. Clone repository and cd into it
```bash
git clone https://github.com/agencyenterprise/AE-Scientist.git
cd AE-Scientist
```

2. Install dependencies
```bash
uv sync --extra gpu
```

3. Activate the virtual environment
```bash
source .venv/bin/activate
```

## Setup (RunPod)

1. Clone repository and cd into it
```bash
git clone https://github.com/agencyenterprise/AE-Scientist.git
cd AE-Scientist
```

2. Create a new virtual environment with access to system-wide packages
```bash
uv venv --system-site-packages
```

This is important because RunPod provides images with pytorch and other gpu-related packages, 
some of these packages may conflict with the packages listed in pyproject.toml.

In order to use the pre-installed packages, we need to create a virtual environment with access to system-wide packages.

3. Activate the virtual environment
```bash
source .venv/bin/activate
```

4. Install dependencies
```bash
uv sync
```

