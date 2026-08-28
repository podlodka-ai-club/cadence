#!/usr/bin/env bash
#
# Turn the unprocessed session records into one change. Runs the manager, which
# routes the task to the retrospective skill.
set -euo pipefail

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run-manager.sh" \
    retrospective-process \
    "process the unprocessed records from Claude Code Sessions"
