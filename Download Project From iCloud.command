#!/bin/bash
# Forces iCloud to bring every file in this folder back onto the Mac,
# then reports anything that is still cloud-only. Changes no file contents.
DIR="/Users/ghitab/Documents/Claude/Projects/Mission solicitor"
cd "$DIR" || { echo "Folder not found: $DIR"; read -n1; exit 1; }

echo "Asking iCloud to download Mission solicitor (this can take a few minutes)..."
brctl download "$DIR" >/dev/null 2>&1

# Reading each file makes macOS fetch it if it's still in the cloud.
fail=0
while IFS= read -r -d '' f; do
  if ! cat "$f" >/dev/null 2>&1; then
    echo "  still cloud-only: ${f#$DIR/}"; fail=$((fail+1))
  fi
done < <(find "$DIR" -type f -print0)

left=$(find "$DIR" -type f -size +0 -exec stat -f '%b' {} + 2>/dev/null | grep -c '^0$')
echo
echo "Files not readable: $fail   Files still without local data: $left"
if [ "$fail" -eq 0 ] && [ "$left" -eq 0 ]; then
  echo "All files are on this Mac."
  git -C "$DIR" fsck --connectivity-only >/dev/null 2>&1 && echo "Git repository OK." || echo "Git reported a problem: run 'git fsck' in the folder."
else
  echo "Some files did not download. Check iCloud in System Settings (signed in, sync not paused, storage not full), then run this again."
fi
echo; echo "Press any key to close."; read -n1
