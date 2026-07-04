#!/bin/bash
cd "/Users/ghitab/Documents/Claude/Projects/Mission solicitor"

# Remove any stale git lock files
rm -f .git/HEAD.lock .git/index.lock

# Add and push the two updated files
git add SQE1_COLP_Revision.html colp_progress.php
git commit -m "Auto-sync COLP revision progress with Hostinger DB — no manual steps needed"
git push origin main

echo ""
echo "✅ Done — COLP progress fix is live on GitHub Pages."
read -p "Press Enter to close..."
