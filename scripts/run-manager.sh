#!/usr/bin/env bash
#
# Launch the manager skill on one task, unattended.
#
# Usage: run-manager.sh <name> <task>
#
#   name   identifies the job: it names the log file and the lock
#   task   the task, in plain words, handed to the manager skill
#
# Everything the run prints goes to untracked/logs/<name>-<timestamp>.log.
# Meant to be called by a wrapper in this directory, from cron.
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "usage: $(basename "$0") <name> <task>" >&2
    exit 2
fi

NAME="$1"
TASK="$2"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKTREES="$(dirname "$REPO")/$(basename "$REPO")-worktrees"
LOG_DIR="$REPO/untracked/logs"

# One log per run, timestamped; one lock per job, not per run — the same file across
# every run of this job is what makes it a lock at all.
LOG="$LOG_DIR/$NAME-$(date -u +%Y-%m-%dT%H%M%SZ).log"
LOCK="$LOG_DIR/$NAME.lock"

CLAUDE_BIN="${CLAUDE_BIN:-claude}"
LOG_RETENTION_DAYS="${LOG_RETENTION_DAYS:-14}"
WORKTREE_RETENTION_HOURS="${WORKTREE_RETENTION_HOURS:-24}"

# untracked/ is empty in a fresh clone — nothing here may assume the directory exists.
mkdir -p "$LOG_DIR"
exec >>"$LOG" 2>&1

echo "=== $NAME — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "task: $TASK"
echo "repo: $REPO"

# One run of a job at a time. Two runs on the same backlog would both claim the same
# records and both open a change for them; cron overlaps by default, so this is the
# normal case, not the rare one.
exec 9>"$LOCK"
if ! flock -n 9; then
    echo "skipped: another $NAME run holds the lock"
    exit 0
fi

# Runs that die before their own cleanup leave a worktree behind, and nobody else is
# in a position to remove it: a live parallel run looks exactly like a dead one for
# its first seconds. Only age tells them apart, and only a launcher knows the age is
# safe to act on — the manager skill itself must never touch another run's worktree.
sweep_worktrees() {
    [ -d "$WORKTREES" ] || return 0
    git -C "$REPO" worktree prune

    local worktree
    while IFS= read -r -d '' worktree; do
        if [ -n "$(git -C "$worktree" status --porcelain 2>/dev/null)" ]; then
            echo "worktree kept, uncommitted changes: $worktree"
        elif [ -n "$(git -C "$worktree" log --oneline HEAD --not --remotes 2>/dev/null)" ]; then
            echo "worktree kept, commits that reached no remote: $worktree"
        elif git -C "$REPO" worktree remove "$worktree"; then
            echo "worktree removed: $worktree"
        else
            echo "worktree could not be removed: $worktree"
        fi
    done < <(find "$WORKTREES" -mindepth 1 -maxdepth 1 -type d \
        -mmin "+$((WORKTREE_RETENTION_HOURS * 60))" -print0)
}
sweep_worktrees

cd "$REPO"

status=0
"$CLAUDE_BIN" -p "Run the manager skill with this task: $TASK" \
    --verbose --dangerously-skip-permissions || status=$?

echo "=== $NAME finished with status $status — $(date -u +%Y-%m-%dT%H:%M:%SZ)"

find "$LOG_DIR" -maxdepth 1 -type f -name '*.log' -mtime "+$LOG_RETENTION_DAYS" -delete

exit "$status"
