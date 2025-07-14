#!/usr/bin/env python3

import sys
import os
import json
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, sudo=False):
    if sudo:
        cmd = ["sudo"] + cmd
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def install_syft():
    print("[INFO] Installing syft...")
    cmd = "curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin"
    subprocess.run(cmd, shell=True, check=False)

def check_and_install():
    if shutil.which("syft") is None:
        install_syft()
        if shutil.which("syft") is None:
            print("[ERROR] syft installation failed.")
            sys.exit(1)

def is_source_file(path):
    return path.endswith(('.c', '.cpp', '.h', '.hpp'))

def run_diffoscope(old_file, new_file):
    try:
        result = subprocess.run(
            ["diffoscope", str(old_file), str(new_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        return result.stdout.splitlines()
    except Exception as e:
        return [f"[ERROR] Failed to run diffoscope: {e}"]

def compare_directories(old_dir, new_dir):
    old_files = {f.relative_to(old_dir) for f in Path(old_dir).rglob('*') if f.is_file() and is_source_file(str(f))}
    new_files = {f.relative_to(new_dir) for f in Path(new_dir).rglob('*') if f.is_file() and is_source_file(str(f))}

    added = new_files - old_files
    removed = old_files - new_files
    common = old_files & new_files

    changes = {
        "New file": sorted([str((Path(new_dir) / f).resolve()) for f in added]),
        "Deleted file": sorted([str((Path(old_dir) / f).resolve()) for f in removed]),
        "Modified file": []
    }

    for f in sorted(common):
        old_path = (Path(old_dir) / f).resolve()
        new_path = (Path(new_dir) / f).resolve()
        with open(old_path, 'r') as f1, open(new_path, 'r') as f2:
            old_lines = f1.readlines()
            new_lines = f2.readlines()
            if old_lines != new_lines:
                diff_output = run_diffoscope(old_path, new_path)
                changes["Modified file"].append({
                    "file": str(new_path),
                    "change": diff_output
                })

    return {"upgrade": {"file_changes": changes}}

def compare_files(old_file, new_file):
    old_file = Path(old_file).resolve()
    new_file = Path(new_file).resolve()
    if not (is_source_file(str(old_file)) and is_source_file(str(new_file))):
        return {"upgrade": {"file_changes": {"New file": [], "Deleted file": [], "Modified file": []}}}

    with open(old_file, 'r') as f1, open(new_file, 'r') as f2:
        old_lines = f1.readlines()
        new_lines = f2.readlines()

    if old_lines != new_lines:
        diff_output = run_diffoscope(old_file, new_file)
        return {
            "upgrade": {
                "file_changes": {
                    "New file": [],
                    "Deleted file": [],
                    "Modified file": [
                        {"file": str(new_file), "change": diff_output}
                    ]
                }
            }
        }
    else:
        return {
            "upgrade": {
                "file_changes": {
                    "New file": [],
                    "Deleted file": [],
                    "Modified file": []
                }
            }
        }

def generate_sbom_with_upgrade(format, target_path, upgrade_data):
    sbom_file = os.path.join(os.getcwd(), f"sbom.{format}_with_upgrade.json")
    if format == "cdx":
        result = subprocess.run(["syft", target_path, "-o", "cyclonedx-json"], capture_output=True, text=True)
    elif format == "spdx":
        result = subprocess.run(["syft", target_path, "-o", "spdx-json"], capture_output=True, text=True)
    else:
        print("[ERROR] Unknown SBOM format. Use 'cdx' or 'spdx'")
        sys.exit(1)

    try:
        sbom = json.loads(result.stdout)
        sbom["upgrade"] = upgrade_data["upgrade"]
        with open(sbom_file, "w") as f:
            json.dump(sbom, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Saved: {sbom_file}")
    except Exception as e:
        print(f"[ERROR] Failed to parse SBOM JSON: {e}")
        sys.exit(1)

def main():
    check_and_install()

    if len(sys.argv) < 5:
        print("Usage:\n  DiffSBOM.py user <cdx|spdx> <old_path> <new_path>\n  DiffSBOM.py diff <cdx|spdx> <old_path> <new_path>")
        sys.exit(1)

    mode, format, old_path, new_path = sys.argv[1:5]

    if mode == "diff":
        if os.path.isdir(old_path) and os.path.isdir(new_path):
            upgrade = compare_directories(old_path, new_path)
        elif os.path.isfile(old_path) and os.path.isfile(new_path):
            upgrade = compare_files(old_path, new_path)
        else:
            print("[ERROR] Both paths must be either files or directories.")
            sys.exit(1)

        generate_sbom_with_upgrade(format, new_path, upgrade)

    elif mode == "user":
        upgrade_path = os.path.join(os.path.dirname(new_path), "version_upgrade.txt")
        with open(upgrade_path, 'r') as f:
            upgrade = json.load(f)
        generate_sbom_with_upgrade(format, new_path, {"upgrade": upgrade})

    else:
        print("[ERROR] Unknown mode. Use 'user' or 'diff'.")
        sys.exit(1)

if __name__ == "__main__":
    main()
