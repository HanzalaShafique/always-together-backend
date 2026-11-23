#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# deploy.sh — Push the Always Together backend to Hugging Face Spaces
#
# Prerequisites:
#   export HF_TOKEN=hf_YOUR_TOKEN
#
# Usage (run from the repo root, NOT from inside backend/):
#   cd /path/to/project
#   bash backend/deploy.sh
# ---------------------------------------------------------------------------

set -euo pipefail

SPACE_ID="hanzala1000/always-together-backend"
DEPLOY_DIR="hf_deploy"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "❌  HF_TOKEN is not set. Export it first:"
  echo "    export HF_TOKEN=hf_..."
  exit 1
fi

echo "🚀  Deploying to Hugging Face Space: $SPACE_ID"

# Clean up any previous deploy directory
rm -rf "$DEPLOY_DIR"
mkdir "$DEPLOY_DIR"

# Initialise a fresh git repo pointing at the HF Space
cd "$DEPLOY_DIR"
git init
git config user.email "deploy-bot@alwaystogether.app"
git config user.name  "Always Together Deploy Bot"

HF_REMOTE="https://hanzala1000:${HF_TOKEN}@huggingface.co/spaces/${SPACE_ID}"
git remote add space "$HF_REMOTE"

# Copy backend files into the deploy dir
# (We are currently inside hf_deploy/, so ../backend/ is the source)
cp -r ../backend/. .

# Stage, commit, and force-push
git add -A
git commit -m "Deploy Always Together Backend — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
git push space main --force

cd ..
rm -rf "$DEPLOY_DIR"

echo "✅  Deployment complete!"
echo "    Space URL: https://hanzala1000-always-together-backend.hf.space"
