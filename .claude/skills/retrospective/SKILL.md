---
name: retrospective
description: Run one task over the Session records in the `Claude Code Sessions` xmemory instance, named explicitly at the start. `process` turns unprocessed records into one atomic change — a pull request against CLAUDE.md or a skill, a draft rule in `Filter Rules`, or a GitHub issue — and closes the records that need none. `sync` resolves the records an earlier run left `inprogress`, once the person has merged or closed the pull request or ruled on the draft rule. Use when asked to run the retrospective, process session records, or close out what an earlier run left open, or when the user runs /retrospective.
---

# retrospective

Session records are what `close-session` leaves behind: rules the person set, mistakes
that were corrected, things nobody classified. This skill works on the records of the
`cadence` project, and does one of two tasks per run — the one named in its argument.

## Arguments

- **task** — required, one of:

| Value | What the run does |
|---|---|
| `process` | works through the `unprocessed` records and makes at most one change |
| `sync` | resolves the records an earlier `process` run left `inprogress` |

  A run does one of them and never both: a `process` run does not also close out what an
  earlier run left open, and a `sync` run makes no change of its own. If the argument is
  missing, ask which task it is; with nobody to ask, do nothing and say so — never pick a
  task on your own.

  The two tasks do not depend on each other. A change that the person turned down closes
  its records for good rather than returning them to the backlog, so `process` never needs
  a `sync` to have run first.

- **session id** — optional: an xmemory session id, `claude-<10 lowercase letters>`.
  When given, use it; when not, generate one. Pass it as `session_id` on every xmemory
  call.

# Task `process`

The unit of work is **one change of the rules**. A rule change shifts how every later
session behaves and there is no evaluation yet that can compare old rules with new, so
a run never bundles unrelated changes: it works through the records in priority order,
closes the ones that need nothing, and stops at the first one that needs a change once
that change is made. If it reaches the end without making a change, that is a complete
run too.

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

A record reporting that a `process` run itself ended in `no-change` is clearly important
on its own, without waiting for a pattern to accumulate: this skill's job is to drain the
backlog, so a run of it that cannot is a defect in the process, not noise to wait out.

**`unknown` text type** — first try to reclassify it as a rule or a mistake from its
text and treat it as that. If it does not reclassify, judge what it is and who wrote it
as above; if that is not clear either and nothing similar exists, close it as not
understood.

"The repository already says it" means: `CLAUDE.md`, the skill's `SKILL.md`, a README,
or — for a rule about how `filter-card` judges cards — a `Rule` in `Filter Rules`.
Check the relevant place before deciding; a record that restates what is already written
is closed, not acted on.

The same check covers work already out for review: before treating a record as needing a
change, check the open pull requests (`gh pr list --state open`) for one that already
makes it. A record whose change is already an open, unmerged pull request is not acted on
again — it is not left `unprocessed` either, since nothing will ever pick it up a second
time and call it done. Treat it as if this run had opened that pull request: `inprogress`,
with resolution `"PR opened: <url>"` pointing at the existing PR. Linking a record to a
pull request already out for review is bookkeeping, not this run's one change, so weighing
continues afterward and a later record can still be the one the run acts on.

Similar records are handled together: one change, every record it rests on.

## 4. Act

Three channels. A change goes to exactly one of them, and one run makes one change.

A pull request this run itself opens is not part of the process until the person merges
it: the run must not turn around and act on another record in the same run as if the
rule it just proposed were already in effect. A run that opens a PR adding a policy does
not get to use that policy before it is merged — the next run, once it has, is what gets
to rely on it.

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
| draft rule written | `inprogress` | *"Draft rule written to Filter Rules: <the rule's text, in full>"* |
| could not be finished this run | `unprocessed` — untouched | — |

The rule's text goes into the resolution whole, not shortened: it is the `Rule` primary
key, and a later `sync` has nothing else to match the record against.

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
  - <xuid> <date> <text_type> — <resolution>
inprogress: <n>
  - <xuid> <date> <text_type> — <resolution>
left: <n> still unprocessed
```

`nothing-to-do` means the backlog was empty at the start. The `xuid` is there because
`close-session` stamps every record of one session with the same `date`, so a report
that named records by `date` alone could not tell two of them apart; the `xuid` always
can. Link the `console_url` of the write once. Then stop.

# Task `sync`

A `process` run that opens a pull request or writes a draft rule leaves its records
`inprogress`: the change is out, but the person has not ruled on it yet. `sync` finds out
what they decided and finishes those records. It changes no rule, no file and no code of
its own — the ten-record limit does not apply, and every open record is looked at.

## 1. Read the open records

```
read(query="Every Session with project_name cadence and status inprogress, all fields.",
     read_mode="xresponse")
```

Nothing there — report `nothing-to-do` and stop.

## 2. Find out what the person decided

The `resolution` says which channel the record went out through.

**`PR opened: <url>`** — group the records by url; one call per url, not per record:

```bash
gh pr view <url> --json state,mergedAt,closedAt,comments
```

**`Draft rule written to Filter Rules: <text>`** — one read of `Filter Rules` for all of
them, matched on the rule text carried in the resolution:

```
read(query="Every Rule with its text and status.", read_mode="raw-tables")
```

## 3. Resolve

Every record that went out on the same change gets the same outcome — the person ruled on
the change, not on the records.

| What happened | `status` | `resolution` | `process_date` |
|---|---|---|---|
| PR merged | `processed` | *"PR merged: <url>"* | `mergedAt` |
| PR closed without merging | `processed` | *"PR closed without merging: <url>"*, plus why if the closing comment says — one sentence, two at most in total | `closedAt` |
| draft rule now `Active` | `processed` | *"Draft rule activated: <the rule's text>"* | now |
| draft rule gone from `Filter Rules` | `processed` | *"Draft rule dropped from Filter Rules: <the rule's text>"* | now |
| PR still open, rule still `Draft` | `inprogress` — untouched | — | — |
| the change cannot be found — `gh` fails, the url does not resolve | `inprogress` — untouched | — | — |

A change the person turned down is settled, not undone: its records close as `processed`
and do not return to the backlog. Re-proposing what was already refused would cost a whole
`process` run and land the same answer. If the lesson still deserves a different change,
the person says so and the record goes back to `unprocessed` by hand.

Everything the run resolves goes out as `update` mutations in a single `write_async`,
keyed by xuid, exactly as in `process`.

## 4. Result

```
result: <resolved | nothing-to-do>
merged: <n records over n changes>
  - <url> — <n records> — <resolution>
declined: <n records over n changes>
  - <url> — <n records> — <resolution>
open: <n records still inprogress>
  - <url or rule> — <n records>
unreachable: <n records still inprogress>
  - <url> — what failed
```

`nothing-to-do` means nothing was `inprogress` at the start. Link the `console_url` of
the write once. Then stop.
