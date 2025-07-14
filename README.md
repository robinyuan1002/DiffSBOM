# DiffSBOM

**DiffSBOM** is a lightweight Python-based tool that enhances standard Software Bill of Materials (SBOM) by embedding structured source-level upgrade information. It helps developers, auditors, and security teams trace software evolution by capturing file-level and line-level changes in source code across versions.

The tool compares two versions of a project—either as source files or directories—and outputs an SPDX or CycloneDX SBOM with an additional `upgrade` section. This section classifies files into `New file`, `Deleted file`, and `Modified file`, and attaches `diffoscope` output for each modified source file to improve traceability and review.

---

## Usage

DiffSBOM supports two modes: `diff` (automated comparison) and `user` (manual input).

### `diff` and `user` Modes

```bash
python3 DiffSBOM.py <mode> <cdx|spdx> <old_path> <new_path>


