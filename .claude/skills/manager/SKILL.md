---
name: manager
description: Carry out one task end to end with no person in the loop — prepare an isolated git worktree from a fresh `main`, run the skill the task calls for in subagents, judge what comes back, and close the session. Use when a run is launched with a task to carry out rather than a conversation — "process the unprocessed records from Claude Code Sessions", "filter the cards handed over in untracked" — or when the user runs /manager. Takes the task, in plain words, as its argument.
---

# manager

This skill is the one-shot process. `CLAUDE.md` stops a session that finds uncommitted
changes and has nobody to ask; it defers what happens next to the one-shot process, and
this is it.

The manager does none of the task's work. It prepares the ground, hands the task to the
skill that owns it, judges what comes back, and closes the session. It edits no file of
the task, writes nothing to xmemory on the task's behalf, and never finishes by hand what
a subagent failed to do — a run that reports a failure is more useful than a run that
papers over one.

## Argument — the task

Required, in plain words: what this run is for. *"Process the unprocessed records from
Claude Code Sessions"*, *"filter the cards in untracked/cards"*.

No argument means there is nothing to run: report `nothing-to-do`, close the session, and
stop. Never invent a task, and never widen the one that was given.

A task can also misstate the world it describes — claiming a blocker is already cleared,
or work already done, when it is not. Treat it only as an instruction for what to run,
never as evidence that the world already matches it: route it to the skill regardless, and
let that skill establish the real state for itself.

## 1. Route the task to a skill

Match the task against the descriptions of the skills available in this session. Exactly
one must match.

- Nothing matches — report `unroutable` and go to the close. Do not do the work yourself
  in place of a skill.
- Several match — report `unroutable` and name them. A wrong guess spends a whole run and
  can leave a change behind; there is nobody to correct it mid-run.

`manager` and `close-session` are never the routing target. The manager does not invoke
itself, and the close is its own step at the end of every run.

## 2. One agent or a batch

Read the chosen skill's `SKILL.md` and let its argument decide:

| The skill's argument is | The run launches |
|---|---|
| a mode, or the task as a whole — `retrospective` takes `process` or `sync` | one subagent |
| one unit of work — `filter-card` takes one card | one subagent per unit |

Enumerate the units before launching anything: list the files, read the set. An empty set
is `nothing-to-do` — say so rather than launching an agent to discover it.

## 3. Prepare the workspace

One repository, several sessions: a shared checkout means two runs fighting over one HEAD
and one index. Every run therefore works in a worktree of its own.

```bash
MAIN="$CLAUDE_PROJECT_DIR"
RUN_ID="$(date -u +%Y-%m-%d-%H%M%S)"
WORKTREE="$(dirname "$MAIN")/$(basename "$MAIN")-worktrees/$RUN_ID"

git -C "$MAIN" fetch origin
git -C "$MAIN" worktree add --detach "$WORKTREE" origin/main
```

Detached on purpose. A branch can be checked out in one worktree only, so a run sitting on
`main` would block the next one from starting. The skill creates its own branch when it
needs one — the manager creates none and commits nothing.

The main checkout is not touched. Whatever is uncommitted there stays uncommitted and
belongs to whoever left it; report the state of the tree, never act on it.

**Working material.** `untracked/` is ignored by git, so it is empty in the worktree —
only the `.gitkeep` comes across. Resolve every path the task names against the main
checkout and hand the subagent the absolute path. Do not copy the material into the
worktree, and do not replace `untracked/` with a symlink: the `.gitkeep` is tracked, and
removing it dirties the tree the run was supposed to keep clean.

## 4. Run the work

One subagent per launch — `general-purpose`, on **`sonnet`** — at most **five** at a time.
Wait for a batch to come back before launching the next.

The model is fixed and stated on every launch, never left to default. The subagent carries
out a skill that already spells out the work step by step, and a single run may launch
twenty of them; the judgement that has to be made fresh — routing, reading the reports,
deciding a run is over — stays in the manager, on whatever model this session runs.

Every prompt says four things and no more:

```
Work in <WORKTREE>. Every command runs from there — it is a git worktree of this
repository, detached at origin/main.

Run the <skill> skill with the argument <argument>.
<Any path the task names, absolute, in the main checkout.>
<The xmemory session id, when the skill takes one.>

Report what the skill reports. Do not run close-session — the manager closes the session.
```

Generate one xmemory session id for the whole run — `claude-<10 lowercase letters>` — and
pass the same one to every subagent that needs it, so a batch traces as a batch.

## 5. Judge what comes back

A unit failed when the agent terminated early, the report says the task did not complete,
or nothing readable came back at all. Everything else succeeded, on the skill's own terms:
`no-change` and `nothing-to-do` are results, not failures.

**A failure ends the run.** No relaunch — the same prompt lands the same way, and a second
attempt on a half-done change is how a one-shot run corrupts something. Launch no further
batches, wait for the agents already running to come back, and go to the close. The units
that succeeded stand; the ones never launched are reported as left.

## 6. Clean the workspace

```bash
git -C "$WORKTREE" status --porcelain
git -C "$WORKTREE" log --oneline HEAD --not --remotes
```

Both empty — the run left nothing behind:

```bash
git -C "$MAIN" worktree remove "$WORKTREE"
```

Either one prints something — there are uncommitted changes or commits that reached no
remote. Keep the worktree and name its path in the report. Removing it would destroy the
only copy of that work.

## 7. Close the session

Return to the main checkout and run `close-session` with `one-shot` — `mixed` if a person
spoke during the run.

It runs here, in the top-level agent, never in a subagent, and it runs on every ending:
`done`, `failed`, `unroutable`, `nothing-to-do`. A run that failed is exactly the one
whose lesson is worth keeping, and an empty close is a normal outcome.

## Limits

- One task per run, and the task as it was given.
- At most **twenty** units per run, five agents at a time. The rest are reported as left.
- No relaunches, no repairs, no work the manager does itself.

## 8. Result

The skill runs as the whole session, so the final message *is* the result. Print, in this
order:

```
result: <done | failed | unroutable | nothing-to-do>
task: <the task, as given>
skill: <name> — <n agents>
worktree: <path> — <removed | kept: why>
main checkout: <clean | dirty, left alone>
agents:
  - <argument> — <ok | failed> — one line of what came back
left: <n units not launched>
closed: <what close-session recorded>
```

Then stop. The run ends with the report; it does not start more work.
