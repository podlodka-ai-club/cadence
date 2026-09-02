# cadence

## Conventions

**Every artifact is written in English.** Skills, documentation, code comments, commit
messages, identifiers, and anything else committed to this repository — English only,
regardless of the language the session was conducted in.

Conversation with a person is exempt: talk to them in whatever language they use.

**Examples are invented, not real.** A command, a path, or a sample record shown in
documentation is made up for the occasion — never a card or transcript copied out of an
actual run, and never a concrete path into the person's working material. Show the usage
form a script accepts, e.g. `command [PATH ...] [--out DIR]`, rather than the arguments
from a real invocation.

**A README documents its own module, not its surroundings.** The task it does, how to run
it, what comes out — short and plain. No sentences about the stages before or after it in
the wider pipeline: that framing goes stale as soon as the pipeline around the module
changes, while the module's own responsibility does not.

## Working material

`untracked/` is where the person drops material for a session to use — transcripts, logs,
exports, samples. Git ignores everything in it except the `.gitkeep` that holds the
directory in place. Look there when asked to work from something that was "handed over",
and put your own scratch output there rather than in the tree. Never commit anything from
it, and never make the project depend on a file there: a fresh clone gets an empty
directory.

## xmemory

At session start the harness may warn that the generic `plugin:xmemory:xmemory` and
`plugin:xmemory:xmemory-admin` servers need authentication. That warning is about the
account-wide connectors, not about this project's own instances — `Claude Code Sessions`,
`City Events & Places`, `Filter Rules`, bound in `.xmemory.json` — whose tools keep
working regardless. Do not read the warning as xmemory being unavailable; check whether
the instance a task actually needs is one of the bound ones before concluding otherwise.

## Session start

Check the working tree before doing anything else. If there are uncommitted changes, stop
and ask the person what to do with them — commit, stash, discard, or build on top. Do not
decide on their behalf, and do not start work that would bury them.

With no person to ask — a `one-shot` run — do not start at all. The one-shot process
defines what happens next; this rule only says the session does not proceed.

## Hardening

Harden the process against failures that actually happened, not ones anticipated in
advance. The `one-shot` → `close-session` → `retrospective` loop exists so that real
failures surface as session records and get fixed from there; propose a guard or a check
only once a record shows the failure occurred, not because it might.
## Design discussions

When the person opens a new feature or change by wanting to discuss it first, let them lay
out the whole idea — what they want and why — before responding. Do not jump to a design
proposal or a list of decision questions partway through; that reads as cutting them off.
Discussion, and any implementation, starts only once they say to move on.

## Branches

Never commit changes directly to `main`. When work starts and the checkout is on `main`,
create a branch and switch to it first — before the first edit, not before the commit.

Name the branch after the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
type the work will carry: `<type>/<short-kebab-description>`, e.g. `feat/close-session-skill`
or `fix/transcript-timestamp`. Same type vocabulary as the commits — `feat`, `fix`, `docs`,
`refactor`, `test`, `chore`, and the rest.

## Review

In a session with a person present, finishing a change and committing it are separate
steps, and the second one waits for them. Show what the change produced and let them
confirm it is what they expected before it lands in history — a commit is not a private
check passing on its own.

## Commits

- Keep each commit focused on a single task.
- The commit message describes the changes in that commit.
- Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):
  `<type>[optional scope][!]: <description>`, e.g. `feat(close-session): record subagent
  findings`. A breaking change is marked with `!` before the colon, or a
  `BREAKING CHANGE:` footer.
- A change that exists only to support another — a `CHANGELOG.md` entry, a new
  `.gitignore` rule, a placeholder file — rides in the commit of the change it supports,
  not as a commit of its own.

## Pull requests

- Rebase the branch on top of `main` before opening a PR.
- Draft PRs are welcome — open one early to get feedback and confirm the direction.
- If a PR introduces a user-observable change — a new protocol feature, a new
  configuration option, a new Prometheus metric, and so on — document it in
  `CHANGELOG.md` under the `[unreleased]` section.

## Changelog

A `CHANGELOG.md` entry names what appeared, in one line — not how it works. Leave out
field lists, data shapes, output locations, rules about what the code skips, and run
commands: whoever integrates the change reads the current shape of the project for
that, and a card of a hundred fields would otherwise drown the file. A later change to
the same feature gets its own entry when it happens, rather than growing the one that
introduced it.
