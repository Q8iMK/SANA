#!/usr/bin/env bash
# ============================================================================
# SANA Setup Script (POSIX) — primary SANA-named entry point.
# Developed by Q8iDevAI.
# ============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/setup-hermes.sh" "$@"
