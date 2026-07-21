#!/bin/zsh

set -u

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR" || {
  echo "Could not open the XPS fitting workbench folder."
  read "?Press Return to close."
  exit 1
}

if ! command -v uv >/dev/null 2>&1; then
  echo "The 'uv' program is not installed."
  echo "Install it from: https://docs.astral.sh/uv/getting-started/installation/"
  read "?Press Return to close."
  exit 1
fi

echo "Preparing the XPS fitting environment..."
if ! uv sync --python 3.13; then
  echo "Setup failed. Check the messages above and docs/troubleshooting.md."
  read "?Press Return to close."
  exit 1
fi

uv run xps-fit wizard
STATUS=$?

if (( STATUS != 0 )); then
  echo "The workflow stopped with an error. Read the message above."
fi
read "?Press Return to close."
exit "$STATUS"
