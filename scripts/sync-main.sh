#!/usr/bin/env bash
#
# Move this checkout's main forward, so the runs launched from it follow the current
# skills instead of whatever was here when it was cloned.
#
# Usage: sync-main.sh
#
# Meant for the checkout cron runs from — one nobody edits by hand. It needs no Claude
# and does none of a run's work; give it its own cron schedule.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$REPO/untracked/logs"

# untracked/ is empty in a fresh clone — nothing here may assume the directory exists.
mkdir -p "$LOG_DIR"

# Appended to a single file, and only when something happened: a run that changed
# nothing is the normal case at this interval, and a line for each of those buries the
# ones that matter. A file per attempt would be tens of thousands of them a year.
log() {
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >>"$LOG_DIR/sync-main.log"
}

cd "$REPO"

# Both checks name a checkout somebody works in rather than the one cron runs from.
# Nothing here is destructive, but a skip that says why beats git's own complaint.
if [ "$(git branch --show-current)" != "main" ]; then
    log "skipped: not on main"
    exit 0
fi

if [ -n "$(git status --porcelain)" ]; then
    log "skipped: uncommitted changes"
    exit 0
fi

before="$(git rev-parse --short HEAD)"

# --ff-only: a checkout nobody commits to can only ever fast-forward. Anything else is
# a state to report, not to merge past.
if ! output="$(git pull --ff-only 2>&1)"; then
    log "failed: $(echo "$output" | tr '\n' ' ')"
    exit 1
fi

after="$(git rev-parse --short HEAD)"

if [ "$before" != "$after" ]; then
    log "$before -> $after"
fi
