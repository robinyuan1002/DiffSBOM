import re

with open("diff_output.txt") as f:
    lines = f.readlines()

filtered = []
recording = False
for line in lines:
    if re.match(r"^@@ .*@@", line):
        recording = True
        filtered.append(line)
    elif recording and (line.startswith('+') or line.startswith('-')):
        filtered.append(line)
    elif recording and line.strip() == '':
        continue
    else:
        recording = False

with open("filtered_diff.txt", "w") as out:
    out.writelines(filtered)
print("✅ Relevant diff sections saved to filtered_diff.txt")
