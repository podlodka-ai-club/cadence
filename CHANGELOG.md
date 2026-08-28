# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

### Added

- `parsers/`: parsers that read different sources of posts and build cards.
- `telegram_history`: builds cards from a Telegram Desktop channel export.
- `close-session` skill: reads the session transcript and records the rules the
  person set, the corrections they made, and what subagents found as `Session`
  entries in xmemory.
- `filter-card` skill: keeps the cards that are events and writes them to xmemory,
  consulting stored rules when in doubt.
- `retrospective` skill: turns unprocessed session records into one change — a pull
  request, a draft filter rule, or an issue — and closes the rest with a reason.

### Changed

- `close-session` skill: records who a fact came from (`author`).
- `filter-card` skill: applies only `Active` filter rules; drafts are ignored.
- `retrospective` skill: takes the task to run as its argument — `process` for new
  records, `sync` to resolve the ones an earlier run left open.

### Fixed
