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

## Working material

`untracked/` is where the person drops material for a session to use — transcripts, logs,
exports, samples. Git ignores everything in it except the `.gitkeep` that holds the
directory in place. Look there when asked to work from something that was "handed over",
and put your own scratch output there rather than in the tree. Never commit anything from
it, and never make the project depend on a file there: a fresh clone gets an empty
directory.

When material a task needs is not in `untracked/`, ask the person for it rather than
going looking — never search the person's other local projects or directories for it.
Material this session was not handed is not this session's to use.

## Session start

Check the working tree before doing anything else. If there are uncommitted changes, stop
and ask the person what to do with them — commit, stash, discard, or build on top. Do not
decide on their behalf, and do not start work that would bury them.

With no person to ask — a `one-shot` run — do not start at all. The one-shot process
defines what happens next; this rule only says the session does not proceed.

## Branches

Never commit changes directly to `main`. When work starts and the checkout is on `main`,
create a branch and switch to it first — before the first edit, not before the commit.

Name the branch after the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
type the work will carry: `<type>/<short-kebab-description>`, e.g. `feat/close-session-skill`
or `fix/transcript-timestamp`. Same type vocabulary as the commits — `feat`, `fix`, `docs`,
`refactor`, `test`, `chore`, and the rest.

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
