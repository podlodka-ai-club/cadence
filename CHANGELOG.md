# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

### Added

- `parsers/`: parsers that read different sources of posts and build cards.
- `storage/`: the evaluation set in MongoDB — the cards and the answers about
  them — with the commands that create the database and fill it.
- `admin/`: a local page for answering cards by hand, one at a time.
- `admin/`: a second page for going back over the answers already given.
- `telegram_history`: builds cards from a Telegram Desktop channel export.
- `close-session` skill: reads the session transcript and records the rules the
  person set, the corrections they made, and what subagents found as `Session`
  entries in xmemory.
- `filter-card` skill: decides whether a card is an event worth keeping and returns
  the verdict — accepted, or refused with reasons from a closed list.
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

- The card carries the time of a post in UTC and refuses a date without a zone.
- `telegram_history`: reads the moment a post was made rather than the local
  time of whoever made the export.
- `close-session` skill: records who a fact came from (`author`).
- `retrospective` skill: takes the task to run as its argument — `process` for new
  records, `sync` to resolve the ones an earlier run left open.

### Fixed
