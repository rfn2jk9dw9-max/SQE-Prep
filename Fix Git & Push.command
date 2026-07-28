#!/bin/bash
# Recovery for the 8.10 + 8.11 expansion.
# The working file already contains origin's latest questions PLUS the expanded
# chapters. This clears stale git locks, points the branch at origin, commits the
# working file as one clean commit, and pushes.
cd "/Users/ghitab/Documents/Claude/Projects/Mission solicitor" || exit 1

echo "1) Clearing stale git locks..."
rm -f .git/index.lock .git/HEAD.lock .git/ORIG_HEAD.lock
rm -rf .git/rebase-merge .git/rebase-apply

echo "2) Fetching origin..."
git fetch origin || { echo "fetch failed"; exit 1; }

echo "3) Pointing local branch at origin/main (keeps your working files)..."
git reset --soft origin/main

echo "4) Staging and committing the expanded revision guide..."
git add SQE1_HighYield_Standalone.html
git commit -m "Expand DISP High-Yield chapters vs SLK manual: 8.2 Building a Claim, 8.3 Pre-Action (Churchill), 8.10 Evidence, 8.11 Disclosure, 8.12 E-Disclosure, 8.13 Privilege, 8.14 Trial, 8.15 Costs, 8.16 Part 36, 8.17 Appeals & Enforcement; fix case-field rendering (8.5, 8.10)"

echo "5) Pushing..."
git push && echo "✓ Pushed. Site will update at https://rfn2jk9dw9-max.github.io/SQE-Prep/"
