#!/usr/bin/env bash
# One-shot Docker install for a fresh Ubuntu EC2 instance (AWS / any VPS).
# Run AFTER cloning the repo:  bash scripts/aws-setup.sh
set -euo pipefail

echo "==> Installing Docker..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"

echo ""
echo "==> Docker installed."
echo "    Log out and back in (or run: newgrp docker), then:"
echo "      cp .env.example .env && nano .env"
echo "      docker compose up -d --build"
echo ""
echo "    See docs/DEPLOY_AWS.md for the full AWS walkthrough."
