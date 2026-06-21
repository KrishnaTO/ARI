#!/usr/bin/env bash
# Pull the latest of the tracked branch and restart the app so the newest
# version of the data populates. Branch comes from GITHUB_BASE_BRANCH in .env
# (the "setting"); falls back to the working branch.
set -euo pipefail
REPO=/opt/ari/repo
cd "$REPO"
BRANCH="$(grep -E '^GITHUB_BASE_BRANCH=' metadata-manager_v2/.env 2>/dev/null | cut -d= -f2-)"
BRANCH="${BRANCH:-feature/metadata-manager_v2/ARI}"
before="$(git rev-parse HEAD 2>/dev/null || echo none)"
git fetch --quiet origin "$BRANCH"
git checkout --quiet "$BRANCH"
git reset --hard --quiet "origin/$BRANCH"
after="$(git rev-parse HEAD)"
if [ "$before" != "$after" ]; then
  sudo systemctl restart ari-mm           # only restart when the branch actually changed
  echo "Updated to origin/$BRANCH @ $(git rev-parse --short HEAD); restarted."
else
  echo "Already up to date (@ $(git rev-parse --short HEAD)); no restart."
fi
