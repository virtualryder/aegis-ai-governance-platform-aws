#!/usr/bin/env bash
# Pre-stage the platform_core Lambda layer BEFORE `sam build`. Run from this folder.
# Populates layer/python/platform_core with the dependency-free (stdlib-only)
# REVIEWED governance engine, so `sam build` needs no `make` and no repo-relative
# build paths (works identically on Linux, macOS, Windows, and CI). Mirrors the
# slg/hcls golden-path pattern. There is ONE source of truth — ../../platform_core —
# and this copies it verbatim, so the deployed layer cannot drift from the reviewed,
# offline-tested engine.
set -euo pipefail
cd "$(dirname "$0")"
REPO="../.."
rm -rf layer/python
mkdir -p layer/python/platform_core
# Copy the engine modules (exclude tests, caches, packaging metadata — the layer
# ships the runtime engine, not the test suite).
( cd "$REPO/platform_core" && \
  find . -name '*.py' -not -path './tests/*' -not -path '*/__pycache__/*' -print0 \
  | while IFS= read -r -d '' f; do
      mkdir -p "$OLDPWD/layer/python/platform_core/$(dirname "$f")"
      cp "$f" "$OLDPWD/layer/python/platform_core/$f"
    done )
echo "layer staged from single source of truth ($REPO/platform_core):"
echo "  $(find layer/python/platform_core -name '*.py' | wc -l | tr -d ' ') modules, $(du -sh layer/python 2>/dev/null | cut -f1)"
