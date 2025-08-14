#!/usr/bin/env bash
set -euo pipefail

OLD_DIR=${1:?Usage: $0 <old_dir> <new_dir>}
NEW_DIR=${2:?Usage: $0 <old_dir> <new_dir>}

OLD=$(realpath "$OLD_DIR")
NEW=$(realpath "$NEW_DIR")

tmp_old_paths=$(mktemp)
tmp_new_paths=$(mktemp)
tmp_old_hashes=$(mktemp)
tmp_new_hashes=$(mktemp)

trap 'rm -f "$tmp_old_paths" "$tmp_new_paths" "$tmp_old_hashes" "$tmp_new_hashes"' EXIT

find "$OLD" -type f -printf '%P\n' \
  | grep -Ev '^\.git/' \
  | LC_ALL=C sort -u > "$tmp_old_paths"

find "$NEW" -type f -printf '%P\n' \
  | grep -Ev '^\.git/' \
  | LC_ALL=C sort -u > "$tmp_new_paths"

echo "=== added (in NEW not in OLD) ==="
comm -13 "$tmp_old_paths" "$tmp_new_paths"
echo

echo "=== removed (in OLD not in NEW) ==="
comm -23 "$tmp_old_paths" "$tmp_new_paths"

while IFS= read -r rel; do
  sha=$(sha256sum "$OLD/$rel" | awk '{print $1}')
  printf "%s\t%s\n" "$rel" "$sha"
done < <(comm -12 "$tmp_old_paths" "$tmp_new_paths") \
 | LC_ALL=C sort -u > "$tmp_old_hashes"

while IFS= read -r rel; do
  sha=$(sha256sum "$NEW/$rel" | awk '{print $1}')
  printf "%s\t%s\n" "$rel" "$sha"
done < <(comm -12 "$tmp_old_paths" "$tmp_new_paths") \
 | LC_ALL=C sort -u > "$tmp_new_hashes"

echo
echo "=== modified (present in both, content differs) ==="
join -t $'\t' -j 1 "$tmp_old_hashes" "$tmp_new_hashes" \
| awk -F'\t' '$2 != $3 { print $1 }' \
| grep -v '^$'
