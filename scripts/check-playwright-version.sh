#!/usr/bin/env bash
# Fails if @playwright/test npm version doesn't match the Docker image tag.
set -euo pipefail

npm_version=$(grep '"@playwright/test"' ui/package.json | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
docker_version=$(grep 'playwright:v' docker-compose.test.yml | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | sed 's/v//')

if [ -z "$npm_version" ] || [ -z "$docker_version" ]; then
  echo "ERROR: could not extract Playwright version from package.json or docker-compose.test.yml"
  exit 1
fi

if [ "$npm_version" != "$docker_version" ]; then
  echo "ERROR: Playwright version drift detected"
  echo "  @playwright/test (ui/package.json):       $npm_version"
  echo "  Docker image (docker-compose.test.yml):    $docker_version"
  echo ""
  echo "Fix: update docker-compose.test.yml to use mcr.microsoft.com/playwright:v${npm_version}-jammy"
  exit 1
fi

echo "OK: Playwright versions in sync ($npm_version)"
