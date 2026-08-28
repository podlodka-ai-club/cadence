---
name: retrospective
description: Work through the unprocessed Session records in the `Claude Code Sessions` xmemory instance and turn what they say into one atomic change — a pull request against CLAUDE.md or a skill, a draft rule in `Filter Rules`, or a GitHub issue — then stop. Records that need no change are closed with a one-line reason. Use when asked to run the retrospective, process session records, or when the user runs /retrospective. Takes an optional xmemory session id.
---

# retrospective

Session records are what `close-session` leaves behind: rules the person set, mistakes
that were corrected, things nobody classified. This skill reads the ones still marked
`unprocessed` for the `cadence` project and acts on them, one change per run.

The unit of work is **one change of the rules**. A rule change shifts how every later
session behaves and there is no evaluation yet that can compare old rules with new, so
a run never bundles unrelated changes: it works through the records in priority order,
closes the ones that need nothing, and stops at the first one that needs a change once
that change is made. If it reaches the end without making a change, that is a complete
run too.

## Argument

- **session id** — optional: an xmemory session id, `claude-<10 lowercase letters>`.
  When given, use it; when not, generate one. Pass it as `session_id` on every xmemory
  call.

## 1. Read the backlog

One read of `Claude Code Sessions`, in `xresponse` mode — the `identifier` on each
object is the xuid, the only handle that can update a record later, because `Session`
declares no primary key:

```
read(query="Every Session with project_name cadence and status unprocessed, all fields.",
     read_mode="xresponse")
```

Read them all. Counting similar records and judging age needs the whole backlog, even
though a run touches at most ten of them.

## 2. Order the records

Work through the backlog in this order; within a tier, older records first:

1. `with-human`, no `skill_name` — the person's feedback on working interactively.
   `rule` first, then `mistake`.
2. `with-human`, with `skill_name` — feedback on a particular skill. `rule`, then
   `mistake`.
3. `mixed` and `one-shot`, same sub-order.
4. `unknown` text type, from any session type — only when every record of the other
   types is already off the backlog.

## 3. Weigh each record

How much a record is trusted depends on who is behind it. `author` says so on newer
records; on older ones it is `Unknown` and has to be read off the message — *"the
person said"*, *"was corrected"* is `Human`; *"a subagent found"*, an observation about
a tool's behaviour is `LLM`; a `with-human` `rule` is the person's unless the text says
otherwise.

**`Human`** — high trust. The question is not whether the person was right but why they
had to say it: what in the process let it happen, and what change stops it from coming up
again. Act unless the repository already says it.

**`LLM`** — caution. Look for similar records across the backlog: more than three of
them is a pattern worth solving. A single record is acted on only when it is clearly
important to the process. A single record older than seven days, with no similar record
in those seven days and no clear importance, is closed.

**`unknown` text type** — first try to reclassify it as a rule or a mistake from its
text and treat it as that. If it does not reclassify, judge what it is and who wrote it
as above; if that is not clear either and nothing similar exists, close it as not
understood.

"The repository already says it" means: `CLAUDE.md`, the skill's `SKILL.md`, a README,
or — for a rule about how `filter-card` judges cards — a `Rule` in `Filter Rules`.
Check the relevant place before deciding; a record that restates what is already written
is closed, not acted on.

Similar records are handled together: one change, every record it rests on.

## 4. Act

Three channels. A change goes to exactly one of them, and one run makes one change.

**Pull request** — for a rule of the interactive process (`CLAUDE.md`) or of a skill
(its `SKILL.md`). Branch from a fresh `main` as `<type>/retro-<short-slug>`, where the
type is the Conventional Commits type of the change (`docs` for `CLAUDE.md`, `feat` or
`fix` for a skill). Make the edit — the rule as an instruction with its reason, in the
voice of the surrounding text — commit it, push, and open a **draft** PR. The PR body
lists every record that led to it: `date`, `text_type`, and the `message` verbatim.
The person merges it; until then the records stay `inprogress`.

**Draft rule** — for a rule about how `filter-card` judges cards. Read the existing
`Rule` rows in `Filter Rules` first and widen an existing one rather than add a
near-duplicate. Write the rule as the intent, with the record's example as an
illustration, status `Draft`:

```json
{"object_mutation": {"object_type": "Rule", "create": {
  "key": {}, "values": {"text": "…", "status": "Draft"}}}}
```

The person activates it; until then the records stay `inprogress`.

**Issue** — for a change to code or to a skill's mechanics that cannot be made by
editing text alone, or an open question the person raised. `gh issue create` in this
repository; title states the change, body carries the records that led to it, as for a
PR. An issue completes the record: it goes to `processed`, with the issue URL in the
resolution.

The commit and the PR follow `CLAUDE.md` — Conventional Commits, English only. Do not
edit `CHANGELOG.md` for a rule change; a `CHANGELOG` entry belongs to features.

## 5. Update the records

Every record touched gets one `update` in a single `write_async`, keyed by xuid:

```json
{"object_mutation": {"object_type": "Session", "update": {
  "key": {"xuid": "<identifier from the read>"},
  "values": {"status": "processed", "process_date": "<now, ISO 8601>",
             "resolution": "<one sentence>"}}}}
```

| Outcome | `status` | `resolution` |
|---|---|---|
| no change needed | `processed` | why — one plain sentence, two at most: *"Already stated in CLAUDE.md under Commits."*, *"Single LLM observation, 12 days old, nothing similar since."* |
| issue opened | `processed` | *"Issue opened: <url>"* |
| PR opened | `inprogress` | *"PR opened: <url>"* |
| draft rule written | `inprogress` | *"Draft rule written to Filter Rules: <first words of the rule>"* |
| could not be finished this run | `unprocessed` — untouched | — |

`process_date` is set whenever the status changes. A record the run looked at but did
not resolve is left exactly as it was.

## Limits

- At most **ten** records touched per run, counting closures.
- One change per run. Once a PR, a draft rule or an issue is out, update the records and
  go to the report — do not start a second change even if the next record is obvious.

## 6. Result

The skill is meant to run inside its own agent, so the final message *is* the result.
Print, in this order:

```
result: <change | no-change | nothing-to-do>
change: <PR url | issue url | "draft rule in Filter Rules"> — one line on what it says
processed: <n>
  - <date> <text_type> — <resolution>
inprogress: <n>
  - <date> <text_type> — <resolution>
left: <n> still unprocessed
```

`nothing-to-do` means the backlog was empty at the start. Link the `console_url` of the
write once. Then stop.
