import argparse, re

def extract_diff(file: str, compressed: bool):
    with open(file) as f:
        lines = f.readlines()

    recording = False

    filtered = []
    pending = []
    for line in lines:
        if not compressed and re.match(r'^(-|\+){3}', line):
            filtered.append(line)
        elif re.match(r'^│ @@ .+ @@$', line):
            if compressed and len(pending) > 0:
                filtered.append(''.join(pending))
                pending = []
                filtered.append(line)
                recording = True
            elif not compressed:
                filtered.append(line)
                recording = True
        elif re.match(r'^│   -{3} ', line):
            recording = False
            pending.append(line.replace('│   ', '', 1))
        elif re.match(r'├── \+{3} ', line):
            pending.append(line.replace('├── ', '', 1))
        elif line == '│┄ Files identical despite different names\n':
            pending = []
        elif recording:
            filtered.append(line)

    with open("filtered_diff.txt", "w") as out:
        out.writelines(filtered)
    print("✅ Relevant diff sections saved to filtered_diff.txt")

def main():
    """Main function to extract differences from diffoscope output."""
    parser = argparse.ArgumentParser(
        description="Generate a list of differences.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "target_path",
        nargs="?",
        help="The path to the diffoscope output file to analyze. Default is `diff_output.txt`",
        default="diff_output.txt"
    )
    parser.add_argument(
        "-c", "--compressed",
        action='store_true',
        help="Is the diffoscope output is generated from a compressed archive?"
    )

    args = parser.parse_args()
    extract_diff(args.target_path, args.compressed)

if __name__ == "__main__":
    main()
