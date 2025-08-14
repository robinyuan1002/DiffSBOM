import sys
import os
import json
import subprocess
import shutil
from pathlib import Path

def run_command_capture(cmd, timeout=120):
    try:
        r = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        return r.stdout, r.stderr, r.returncode
    except Exception as e:
        return "", str(e), 1

def ensure_tool_exists(tool):
    if shutil.which(tool) is None:
        print(f"[ERROR] Required tool not found on PATH: {tool}")
        sys.exit(1)

def is_source_file(path):
    return path.endswith((
        '.c', '.h',
        '.cpp', '.cc', '.cxx', '.hpp', '.hxx',
        '.py',
        '.java',
        '.go',
        '.rs',
        '.cs'
    ))

def run_diffoscope(old_file, new_file):
    if shutil.which("diffoscope") is None:
        return [f"[WARN] diffoscope not found; raw change recorded for {old_file} -> {new_file}"]
    try:
        result = subprocess.run(
            ["diffoscope", str(old_file), str(new_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60
        )
        with open("diff_output.txt", "a", encoding="utf-8", errors="replace") as f:
            f.write(result.stdout)
            if not result.stdout.endswith("\n"):
                f.write("\n")
        return result.stdout.splitlines()
    except Exception as e:
        return [f"[ERROR] Failed to run diffoscope: {e}"]

def _parse_dir_diff_output(stdout: str):
    sections = {"added": [], "removed": [], "modified": []}
    state = None
    for raw in stdout.splitlines():
        line = raw.rstrip("\n")
        if line.startswith("=== added"):
            state = "added";   continue
        if line.startswith("=== removed"):
            state = "removed"; continue
        if line.startswith("=== modified"):
            state = "modified"; continue
        if state and line.strip():
            sections[state].append(line.strip())
    return sections

def compare_directories(old_dir, new_dir, diff_script="./filediff.sh", filter_source=True):
    old_dir = Path(old_dir).resolve()
    new_dir = Path(new_dir).resolve()

    if not Path(diff_script).exists():
        raise FileNotFoundError(f"diff script not found: {diff_script}")
    if not os.access(diff_script, os.X_OK):
        raise PermissionError(f"diff script is not executable: {diff_script}")

    proc = subprocess.run(
        [diff_script, str(old_dir), str(new_dir)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"dir diff script failed (rc={proc.returncode}).\nSTDERR:\n{proc.stderr}"
        )

    parts = _parse_dir_diff_output(proc.stdout)

    def _maybe_filter(paths):
        if not filter_source:
            return paths
        return [p for p in paths if is_source_file(p)]

    added_rel = _maybe_filter(parts["added"])
    removed_rel = _maybe_filter(parts["removed"])
    modified_rel = _maybe_filter(parts["modified"])

    changes = {
        "old_version": str(old_dir),
        "New file": sorted([str((new_dir / rel).resolve()) for rel in added_rel]),
        "Deleted file": sorted([str((old_dir / rel).resolve()) for rel in removed_rel]),
        "Modified file": []
    }

    for rel in sorted(modified_rel):
        old_path = (old_dir / rel).resolve()
        new_path = (new_dir / rel).resolve()
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
        return {"upgrade": {"file_changes": {"old_version": str(old_file.parent), "New file": [], "Deleted file": [], "Modified file": []}}}

    with open(old_file, 'r', errors='replace') as f1, open(new_file, 'r', errors='replace') as f2:
        if f1.read() != f2.read():
            diff_output = run_diffoscope(old_file, new_file)
            return {
                "upgrade": {
                    "file_changes": {
                        "old_version": str(old_file.parent),
                        "New file": [],
                        "Deleted file": [],
                        "Modified file": [
                            {
                                "file": str(new_file),
                                "change": diff_output
                            }
                        ]
                    }
                }
            }
        else:
            return {
                "upgrade": {
                    "file_changes": {
                        "old_version": str(old_file.parent),
                        "New file": [],
                        "Deleted file": [],
                        "Modified file": []
                    }
                }
            }

def build_sbom_command(tool, fmt, target_path):
    if tool == "syft":
        if fmt == "cdx":
            return ["syft", target_path, "-o", "cyclonedx-json"]
        elif fmt == "spdx":
            return ["syft", target_path, "-o", "spdx-json"]
        else:
            print("[ERROR] Unknown SBOM format. Use 'cdx' or 'spdx'")
            sys.exit(1)

    elif tool == "trivy":
        if fmt == "cdx":
            return ["trivy", "fs", "--format", "cyclonedx", "--quiet", target_path]
        elif fmt == "spdx":
            return ["trivy", "fs", "--format", "spdx-json", "--quiet", target_path]
        else:
            print("[ERROR] Unknown SBOM format. Use 'cdx' or 'spdx'")
            sys.exit(1)

    else:
        print("[ERROR] Unknown tool. Use 'syft' or 'trivy'")
        sys.exit(1)

def generate_sbom_with_upgrade(fmt, target_path, upgrade_data, tool):
    sbom_file = os.path.join(os.getcwd(), f"sbom.{fmt}_with_upgrade.json")

    cmd = build_sbom_command(tool, fmt, target_path)
    stdout, stderr, rc = run_command_capture(cmd, timeout=600)
    if rc != 0:
        print(f"[ERROR] SBOM generation failed with {tool}. rc={rc}\nSTDERR:\n{stderr}")
        sys.exit(1)

    try:
        sbom = json.loads(stdout)
    except json.JSONDecodeError as e:
        head = stdout.strip()[:200]
        print("[ERROR] Failed to parse SBOM JSON. "
              "The tool may have produced non-JSON output (e.g., XML). "
              f"First 200 chars: {head}\nDetail: {e}")
        sys.exit(1)

    sbom["upgrade"] = upgrade_data["upgrade"]
    try:
        with open(sbom_file, "w", encoding="utf-8") as f:
            json.dump(sbom, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Saved: {sbom_file}")
    except Exception as e:
        print(f"[ERROR] Failed to write SBOM file: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 6:
        print("Usage:\n"
              "  DiffSBOM.py user <cdx|spdx> <old_path> <new_path> <syft|trivy>\n"
              "  DiffSBOM.py diff <cdx|spdx> <old_path> <new_path> <syft|trivy>")
        sys.exit(1)

    mode, fmt, old_path, new_path, tool = sys.argv[1:6]
    fmt = fmt.lower()
    tool = tool.lower()

    ensure_tool_exists(tool)

    if mode == "diff":
        if os.path.isdir(old_path) and os.path.isdir(new_path):
            upgrade = compare_directories(old_path, new_path)
        elif os.path.isfile(old_path) and os.path.isfile(new_path):
            upgrade = compare_files(old_path, new_path)
        else:
            print("[ERROR] Both paths must be either files or directories.")
            sys.exit(1)

        generate_sbom_with_upgrade(fmt, new_path, upgrade, tool)

    elif mode == "user":
        upgrade_path = os.path.join(os.path.dirname(new_path), "version_upgrade.txt")
        try:
            with open(upgrade_path, 'r', encoding='utf-8') as f:
                upgrade = json.load(f)
                if "upgrade" not in upgrade:
                    upgrade = {"upgrade": upgrade}
        except Exception as e:
            print(f"[ERROR] Failed to read user upgrade file '{upgrade_path}': {e}")
            sys.exit(1)

        generate_sbom_with_upgrade(fmt, new_path, upgrade, tool)

    else:
        print("[ERROR] Unknown mode. Use 'user' or 'diff'.")
        sys.exit(1)

if __name__ == "__main__":
    main()