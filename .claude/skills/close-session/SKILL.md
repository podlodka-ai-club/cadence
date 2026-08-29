---
name: close-session
description: Wrap up a Claude Code session — pull out the rules the person set, the corrections they made, and the defects validation subagents found, then record each one in xmemory as a Session record. Use when the user asks to close, finish or wrap up the session, or runs /close-session. Takes the session type as its argument.
---

# close-session

Turn a finished session into durable memory. Everything worth carrying into the next
session gets written to the `Claude Code Sessions` xmemory instance, one record per fact,
as `unprocessed` — a later pass decides what to do with them.

This skill only reads the session and writes memory. It changes no code. It runs in the
top-level agent only, never in a subagent. The `manager` skill runs it as the last step of
a one-shot run; no other skill invokes it.

## Argument — session type

Required, one of:

| Value | Meaning |
|---|---|
| `one-shot` | ran without a human, on an automated flow |
| `with-human` | interactive session with a person |
| `mixed` | ran as `one-shot`, but a person reviewed and commented on the result at the end |

If the argument is missing, ask which one it was. If nobody can answer (non-interactive
run), use `one-shot` and say so in the report — never guess between the other two.

## 1. Gather the material

```bash
python3 "$CLAUDE_PROJECT_DIR/.claude/skills/close-session/scripts/session_material.py"
```

It prints JSON: `started_at`, `project_name`, `human_messages`, and `agent_activity`
(`agent-launch` with the prompt, `agent-report` with what came back). Read it from the
transcript rather than from memory — the transcript survives compaction and is the only
place the real session start time lives. Pass `--max-chars 0` if a report looks cut short
and the detail matters, or `--transcript <path>` to read a session other than this one.

Two things the script already handles, worth knowing when reading its output: subagents
run asynchronously, so an agent's answer arrives as a `<task-notification>` in an ordinary
user record — it is an `agent-report`, never something the person said — and the
`tool_result` of the launch itself is a receipt that must not be quoted. An `agent-report`
whose text says the agent terminated early is a finding in its own right.

Use your own recollection of the session as a second pass over the same ground, not as a
replacement: it catches nuance the extractor flattens.

## 2. What to pull out

**`rule`** — how work should be done here, stated by the person: constraints,
conventions, preferences, process decisions, where things live. Count rules dropped in
passing, not just ones announced as rules.

**`mistake`** — what went wrong and had to be corrected:
- the person corrected you — you did X, they said do Y instead
- a validation subagent found a defect in your work or in another subagent's work
- something you got wrong and redid

**`unknown`** — genuinely useful for future runs but neither of the above: an
environment quirk, a command that had to be run a particular way, a dead end worth not
repeating.

Writing each `message`:

- One fact per record. Self-contained — a future session reads it with no access to this
  transcript, so name the thing rather than referring to "it" or "the above".
- State it as an instruction or a finding, not as narration. *"Bind xmemory at project
  scope so `.xmemory.json` is committed"*, not *"we talked about bindings"*.
- Include the reason when the person gave one. A rule without its why gets misapplied.
- State what was actually observed; check a cause before naming it, never guess one. A
  stored record is what the retrospective later acts on — a guessed cause can send it to
  fix code that was never broken.
- A couple of sentences at most.
- Write it in English, whatever language the session was conducted in — a stored
  record is an artifact. Quote the person's own wording only where the exact phrasing
  is the point.

Leave out: the task content itself, chatter, and anything already recorded in the repo
(README, `CLAUDE.md`, code, git history) — a session lesson is what the repo does *not*
already say. If the person never stated it, it is not a rule; do not infer one from a
single instance of doing something.

If nothing qualifies, write nothing and say so. An empty close is a normal outcome — most
runs should close empty. Do not write a record to avoid an empty close; a record earns its
place by teaching a lesson a later session would otherwise repeat, not by being the first
thing that comes to mind. Hold this bar especially high for facts about running
close-session or the runs that call it: an environment quirk hit once tends to recur as
the same near-identical record run after run, and a backlog fed by its own retrospective
process is a backlog nobody asked for.

## 3. Fields

| Field | Value |
|---|---|
| `project_name` | `project_name` from the script |
| `message` | the fact, per the rules above |
| `session_type` | the argument |
| `date` | `started_at` from the script — session **launch** time, ISO 8601, identical on every record from this session |
| `text_type` | `rule` / `mistake` / `unknown` |
| `skill_name` | the skill the fact concerns, when it concerns one; otherwise omit |
| `author` | `Human` when the fact comes from something the person said or did — a rule they stated, a correction they made; `LLM` when it comes from a subagent's finding or your own observation; `Unknown` only when it genuinely cannot be told |
| `status` | `unprocessed` |
| `process_date` | omit |
| `resolution` | omit |

## 4. Write

One `write_async` carrying every fact as `structured_mutations` — exact edits, no
extraction step between you and the stored row.

Do not read the instance first and do not try to deduplicate. `Session` declares no
primary key, so every create appends, and a rule restated across sessions lands as
several rows on purpose — sorting that out is a separate process, not this skill's job.

```json
{
  "session_id": "claude-<10 lowercase letters>",
  "structured_mutations": [
    {"object_mutation": {"object_type": "Session", "create": {
      "key": {},
      "values": {
        "project_name": "cadence",
        "message": "…",
        "session_type": "with-human",
        "date": "2026-08-24T08:52:43.262Z",
        "text_type": "rule",
        "author": "Human",
        "status": "unprocessed"
      }
    }}}
  ]
}
```

`"key": {}` is correct here and only because the schema declares `"primary_key": []`.

If the call fails, inspect what landed before resending — a keyless batch can apply in
part, and a blind retry duplicates whatever already went in.

## 5. Report

One line per record — `text_type`, `author` and the message — grouped rule / mistake / unknown, plus
the session type and the launch date stamped on all of them. Link the write's
`console_url` once. Then stop: closing a session ends the work, it does not start more.
