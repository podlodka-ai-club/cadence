# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

### Added

- `parsers/`: parsers that read different sources of posts and build cards.
- `storage/`: the evaluation set in MongoDB — the cards and the answers about
  them — with the commands that create the database and fill it.
- `telegram_history`: builds cards from a Telegram Desktop channel export.
- `close-session` skill: reads the session transcript and records the rules the
  person set, the corrections they made, and what subagents found as `Session`
  entries in xmemory.
- `filter-card` skill: keeps the cards that are events and writes them to xmemory,
  consulting stored rules when in doubt.
- `retrospective` skill: turns unprocessed session records into one change — a pull
  request, a draft filter rule, or an issue — and closes the rest with a reason.
- `manager` skill: carries out one task with no person in the loop — prepares an
  isolated worktree, hands the work to the skill that owns it, and closes the
  session.
- `scripts/`: unattended launchers that run the manager on the retrospective's two
  tasks, one run of a job at a time, logging each run.
- `scripts/sync-main.sh`: fast-forwards the checkout cron runs from, so a run
  follows the current skills rather than the ones it was cloned with.

### Changed

- `close-session` skill: records who a fact came from (`author`).
- `filter-card` skill: applies only `Active` filter rules; drafts are ignored.
- `retrospective` skill: takes the task to run as its argument — `process` for new
  records, `sync` to resolve the ones an earlier run left open.

### Fixed
