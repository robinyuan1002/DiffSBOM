import re

def parse_functions(diff_lines):
    added, removed, modified = set(), set(), set()
    current_func = None
    current_changes = []

    for line in diff_lines:
        if line.startswith("@@"):
            match = re.search(r"@@.*@@\s*(def\s+[a-zA-Z0-9_]+)", line)
            if match:
                if current_func and current_changes:
                    classify(current_func, current_changes, added, removed, modified)
                current_func = match.group(1)
                current_changes = []
        elif line.startswith('+') or line.startswith('-'):
            current_changes.append(line)

    if current_func and current_changes:
        classify(current_func, current_changes, added, removed, modified)

    return added, removed, modified

def classify(func, changes, added, removed, modified):
    add = any(line.startswith('+') for line in changes)
    rem = any(line.startswith('-') for line in changes)
    if add and not rem:
        added.add(func)
    elif rem and not add:
        removed.add(func)
    else:
        modified.add(func)

# Main
with open("filtered_diff.txt") as f:
    lines = f.readlines()

a, r, m = parse_functions(lines)

with open("added_functions.txt", "w") as f:
    f.writelines(func + "\n" for func in sorted(a))
with open("removed_functions.txt", "w") as f:
    f.writelines(func + "\n" for func in sorted(r))
with open("modified_functions.txt", "w") as f:
    f.writelines(func + "\n" for func in sorted(m))

print("Function-level reports created.")
