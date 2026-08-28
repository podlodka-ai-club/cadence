# scripts

Unattended launchers. Each one starts a Claude Code run on a single task, with no person
in the loop, and leaves a log behind. They exist so cron has something to call.

## What is here

| Script | Task it runs |
|---|---|
| `retrospective-process.sh` | turn the unprocessed session records into one change |
| `retrospective-sync.sh` | close out the records an earlier run left open |
| `run-manager.sh` | the launcher both wrappers call; not run by hand |

A wrapper names a job and states its task in plain words. `run-manager.sh` hands that task
to the `manager` skill, which decides which skill owns it — the wrappers name no skill
themselves.

## Running one

```
scripts/retrospective-process.sh
```

Takes no arguments. From cron, give the absolute path and a `PATH` that reaches the
`claude` binary — cron's own is short:

```cron
PATH=/usr/local/bin:/usr/bin:/bin

30 4 * * *  /path/to/cadence/scripts/retrospective-process.sh
30 5 * * *  /path/to/cadence/scripts/retrospective-sync.sh
```

Or point `CLAUDE_BIN` at the binary instead of fixing `PATH`.

| Variable | Default | Meaning |
|---|---|---|
| `CLAUDE_BIN` | `claude` | the binary to launch |
| `LOG_RETENTION_DAYS` | `14` | logs older than this are deleted at the end of a run |
| `WORKTREE_RETENTION_HOURS` | `24` | how old a leftover worktree must be to be swept |

## What comes out

A log per run, in `untracked/logs/`:

```
untracked/logs/retrospective-process-2026-01-31T043000Z.log
```

It holds the task, the run's own progress, and a last line with the exit status, which the
script also returns — so a failed run is visible both in the log and to cron. A run that
starts while another run of the same job is still going writes a two-line log saying it was
skipped, and exits `0`: cron overlapping itself is expected, not a failure.

The directory is created on the first run. Nothing here depends on it existing — a fresh
clone has an empty `untracked/`.

## Two things the launcher does before starting the run

**One run of a job at a time**, held on a lock file next to the logs. Two runs over the
same backlog would claim the same records and open a change for each of them twice.

**Sweeping worktrees left by dead runs.** A run that dies before its own cleanup leaves a
worktree behind. Nothing running can safely remove it — for its first seconds a live
parallel run is indistinguishable from a dead one — so only age separates them, and only a
launcher is in a position to use age. A worktree is swept when it is older than
`WORKTREE_RETENTION_HOURS`, has no uncommitted changes, and holds no commit that never
reached a remote; otherwise it is kept and named in the log.
