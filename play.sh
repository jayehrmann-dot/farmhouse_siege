#!/usr/bin/env bash
# Launch Farmhouse Siege in the current terminal.
cd "$(dirname "$0")" || exit 1
exec python3 -m farmhouse_siege "$@"
