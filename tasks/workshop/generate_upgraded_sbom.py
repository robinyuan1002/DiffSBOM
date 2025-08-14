#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys

# --- Script Configuration ---
# The name of the new section to be added to the SBOM.
UPGRADE_SECTION_NAME = "upgrade"
# The name of the final output file.
OUTPUT_FILENAME = "sbom_with_upgrade.json"


def validate_inputs(target_path, sbom_format, upgrade_file_path):
    """
    Validates the user-provided arguments.

    Returns:
        A dictionary with the parsed JSON data from the upgrade file.
        Exits the script with an error message if validation fails.
    """
    print("Step 1: Validating inputs...")

    # 1. Validate target path exists
    if not os.path.exists(target_path):
        print(f"❌ ERROR: The specified target path does not exist: {target_path}")
        sys.exit(1)
    print(f"✅ Target path '{target_path}' found.")

    # 2. SBOM format is already validated by argparse choices.
    print(f"✅ SBOM format '{sbom_format}' is valid.")

    # 3. Validate upgrade file exists
    if not os.path.exists(upgrade_file_path):
        print(f"❌ ERROR: The upgrade file does not exist: {upgrade_file_path}")
        sys.exit(1)

    # 4. Validate upgrade file is correctly formatted JSON
    try:
        with open(upgrade_file_path, 'r') as f:
            upgrade_data = json.load(f)
        print(f"✅ Upgrade file '{upgrade_file_path}' is valid JSON.")
        return upgrade_data
    except json.JSONDecodeError:
        print(f"❌ ERROR: The upgrade file '{upgrade_file_path}' is not a valid JSON file.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Could not read the upgrade file: {e}")
        sys.exit(1)


def generate_base_sbom(target_path, sbom_format):
    """
    Uses syft to generate a fresh SBOM from the target.

    Returns:
        A dictionary containing the parsed JSON of the generated SBOM.
        Exits the script if syft is not installed or fails.
    """
    print("\nStep 2: Generating fresh SBOM with syft...")

    # Syft requires the format string to be like 'cyclonedx-json' or 'spdx-json'
    syft_format_string = "cyclonedx-json" if sbom_format == "cdx" else "spdx-json"
    command = ["syft", "scan", target_path, "-o", syft_format_string]

    try:
        # Execute the syft command
        print(f"▶️  Running command: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True  # This will raise an exception if syft returns a non-zero exit code
        )
        print("✅ Syft execution successful.")
        # Parse the JSON output from syft's stdout
        return json.loads(result.stdout)

    except FileNotFoundError:
        print("❌ ERROR: 'syft' command not found.")
        print("Please ensure syft is installed and in your system's PATH.")
        print("Installation instructions: https://github.com/anchore/syft")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("❌ ERROR: Syft failed to generate the SBOM.")
        print(f"Syft stderr:\n{e.stderr}")
        sys.exit(1)


def merge_and_save_sbom(base_sbom_data, upgrade_data):
    """
    Inserts the upgrade data into the SBOM and saves it to a new file.
    """
    print("\nStep 3: Merging upgrade data into the SBOM...")

    # Insert the upgrade data as a new top-level section
    base_sbom_data[UPGRADE_SECTION_NAME] = upgrade_data
    print(f"✅ Upgrade data inserted under the '{UPGRADE_SECTION_NAME}' key.")

    try:
        with open(OUTPUT_FILENAME, 'w') as f:
            json.dump(base_sbom_data, f, indent=2)
        print(f"\n🎉 Success! New SBOM saved as '{OUTPUT_FILENAME}'")
    except Exception as e:
        print(f"❌ ERROR: Could not write the final SBOM file: {e}")
        sys.exit(1)


def main():
    """Main function to orchestrate the SBOM generation and merging process."""
    parser = argparse.ArgumentParser(
        description="Generate a new SBOM with a custom 'upgrade' section.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "target_path",
        help="The path to the file, directory, or container image to analyze (e.g., '.', 'Dockerfile', 'python:3.9-slim')."
    )
    parser.add_argument(
        "sbom_format",
        choices=["cdx", "spdx"],
        help="The desired SBOM format (cdx for CycloneDX, spdx for SPDX)."
    )
    parser.add_argument(
        "upgrade_file",
        help="The path to the JSON file containing the upgrade information (e.g., 'version_upgrade.txt')."
    )

    args = parser.parse_args()

    # Step 1: Validate all inputs and get upgrade data
    upgrade_data = validate_inputs(args.target_path, args.sbom_format, args.upgrade_file)

    # Step 2: Generate the base SBOM using syft
    base_sbom_data = generate_base_sbom(args.target_path, args.sbom_format)

    # Step 3: Merge the upgrade data and save the new SBOM
    merge_and_save_sbom(base_sbom_data, upgrade_data)


if __name__ == "__main__":
    main()

