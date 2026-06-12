#!/usr/bin/env bash
# Exit on error, undefined variable, or pipe failure
set -euo pipefail

# Use uv if available, fallback to pip
if command -v uv &> /dev/null; then
    uv sync
    uv run pytest --cov=app --cov-report=term-missing "$@"
else
    # Activate the virtual environment if it exists
    if [ -f "./venv/bin/activate" ]; then
        # shellcheck source=/dev/null
        source ./venv/bin/activate
    fi
    pip install -r requirements.txt
    pytest --cov=app --cov-report=term-missing "$@"
fi
