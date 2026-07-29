#!/bin/bash
# Quick commit script for comfyui-wizdroid-tools
# Usage: ./quick-commit.sh "your commit message"

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: $0 \"your commit message\""
    echo "Example: $0 \"feat: add LLM prompt generator node\""
    exit 1
fi

MESSAGE="$1"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Working in: $REPO_DIR"
cd "$REPO_DIR"

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "==> No git repo found. Initializing..."
    git init
    git remote add origin https://github.com/wizdroid/comfyui-wizdroid-tools.git 2>/dev/null || true
fi

echo "==> Staging all changes..."
git add -A

echo "==> Status:"
git status --short

echo ""
echo "==> Committing with message: $MESSAGE"
git commit -m "$MESSAGE"

echo ""
echo "==> Pushing to origin/main..."
git push -u origin main 2>/dev/null || git push origin main

echo ""
echo "==> Done!"
