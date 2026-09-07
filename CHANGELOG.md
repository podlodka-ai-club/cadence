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
- `filter-card` skill: decides whether a card is an event worth keeping and returns
  the verdict — accepted, or refused with reasons from a closed list.
- `storage`: the verdicts the filter gave, kept per run.
- `judge/`: runs the filter over cards in batches and measures a run — against
  the answers, or against another run.
- `admin/`: a third page for confirming the filter's verdicts, one press to agree.
- `storage/`: the `rules` collection — rules the filter is given, each withholding one
  refusal reason from a kind of card, and each draft, active or rejected — and the
  `runs` collection recording what each run of the judge went with.
- `filter-card` skill: takes a file of rules alongside the cards and names the ones it
  applied on each verdict.
- `judge.run`: `--rules` picks which rules the filter is given, active by default.
- `judge.gate`: decides a draft rule, active or rejected, from a run with it against a
  run without it.
- `telegram_live`: reads Telegram channels as they publish and keeps the posts
  as cards.
- `storage`: the sources being read, and where the reading got to in each.
- `storage`: a command that adds a source to read.
- a sink that puts the cards a parser built into the database.
- `observe-record` skill: marks how one post landed in memory — its schedule, its
  event and its place — and names what would keep the worst of it from happening again.
- `storage.show_card`: prints one card, by the source and number that address it.
- `storage`: the `sets` collection — a named set of cards to judge, written once and
  not edited afterwards.
- `judge.run`: `--set` narrows a run to the cards of a named set.
- `deploy/`: the service the online parser runs under, and the script that ships
  a new version to a machine already running it.
- `deploy/`: the sudoers rule letting the parser's account restart its own service.
- `storage`: the `observations` collection — how one post landed in one memory, marked
  by an observer.
- `memory/`: writes a set of cards into an xmemory instance, marks how each of them
  landed, drafts a rule from the complaints and decides it on two memories.
- `propose-rule` skill: words one instruction to whatever writes posts into memory,
  out of what the observers of a memory complained about.
- `storage`: the `schema_changes` collection — a change to the schema a memory was
  given, proposed where no rule could have helped, and where it stands.
- `memory.gate`: decides a schema change as well as a rule.
- `schema/`: the xmemory schema in force, kept in the repository.

### Changed

- The card carries the time of a post in UTC and refuses a date without a zone.
- `telegram_history`: reads the moment a post was made rather than the local
  time of whoever made the export.
- `telegram_history`: takes the source the cards carry, for an export whose
  directory is not named after it.
- `storage.setup`: takes the collections to bring up, for a database that holds
  only some of them.
- `storage`: a rule says who it is addressed to, the filter or memory.

### Fixed
