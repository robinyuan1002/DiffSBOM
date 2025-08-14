# DiffSBOM Automation Script

This script automates **SBOM (Software Bill of Materials)** generation and diff analysis between two versions of a project, supporting **Syft** and **Trivy** as SBOM generation tools.  
It can run in two modes:
- `diff` mode: Automatically detect file changes between two versions and merge them into a new SBOM.
- `user` mode: Use a user-provided `version_upgrade.txt` JSON file describing changes.

---

## Features
- Supports **two SBOM formats**:  
  - `spdx` (SPDX JSON format)  
  - `cdx` (CycloneDX JSON format)
- Supports **two tools** for SBOM generation:  
  - [Syft](https://github.com/anchore/syft)  
  - [Trivy](https://github.com/aquasecurity/trivy)  
- Automatically installs the chosen SBOM tool if not present.  
- Delegates actual diff logic to [`DiffSBOM.py`](./DiffSBOM.py), which performs detailed analysis using `diffoscope` for modified files.

---

## Requirements
The following tools are required depending on the mode and tool selection:
- **Bash** (Unix/Linux/Mac environment)
- **Python 3** (for `DiffSBOM.py`)
- **curl** (for installing `syft` or `trivy`)
- **diffoscope** (for detailed file diff in `DiffSBOM.py`)

---

## Usage

```bash
./gensbomwithdiff.sh <mode> <sbom_format> <old_project_path> <new_project_path> <tool>



