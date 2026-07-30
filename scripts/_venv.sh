#!/usr/bin/env bash
# Shared helper: activate the local .venv if present and not already active.
# Meant to be sourced (not executed) from the repo root by other scripts.

if [ -z "$VIRTUAL_ENV" ] && [ -f ".venv/bin/activate" ]; then
    echo "Note: venv not active in this shell — activating it for this script only."
    echo "Run 'source .venv/bin/activate' yourself to keep it active afterwards."
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi
