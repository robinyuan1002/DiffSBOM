#!/bin/bash

if [ "$#" -ne 5 ]; then
    echo "Usage: $0 <mode: user|diff> <sbom_format: spdx|cdx> <old_project_path> <new_project_path> <tool: syft|trivy>"
    exit 1
fi

mode="$1"
format="$2"
old_path="$3"
new_path="$4"
tool="$5"

case "$mode" in
    user|diff) ;;
    *) echo "Error: mode must be 'user' or 'diff'."; exit 1 ;;
esac

if [ ! -d "$old_path" ]; then
    echo "Error: Old project path '$old_path' does not exist or is not a directory."
    exit 1
fi

if [ ! -d "$new_path" ]; then
    echo "Error: New project path '$new_path' does not exist or is not a directory."
    exit 1
fi

if [ "$format" != "spdx" ] && [ "$format" != "cdx" ]; then
    echo "Error: SBOM format must be either 'spdx' or 'cdx'."
    exit 1
fi

case "$tool" in
    syft|trivy) ;;
    *) echo "Error: SBOM generation tool must be 'syft' or 'trivy'."; exit 1 ;;
esac

if [ "$mode" = "user" ]; then
    if ! command -v jq >/dev/null 2>&1; then
        echo "Error: 'jq' is required but not installed."
        exit 1
    fi

    json_file="version_upgrade.txt"
    upgrade_file="$new_path/$json_file"

    if [ ! -f "$upgrade_file" ]; then
        echo "Error: Required file '$upgrade_file' not found."
        exit 1
    fi

    if ! jq -e empty "$upgrade_file" >/dev/null 2>&1; then
        echo "Error: '$upgrade_file' is not valid JSON."
        exit 1
    else
        echo "Success: '$upgrade_file' contains valid JSON."
    fi
fi

if [ "$tool" = "syft" ]; then
    echo "[INFO] Installing Syft..."
    curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
elif [ "$tool" = "trivy" ]; then
    echo "[INFO] Installing Trivy..."
    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin
fi

echo "[INFO] Running SBOM diff analysis with $tool..."
python3 DiffSBOM.py "$mode" "$format" "$old_path" "$new_path" "$tool"