# judge

Hands cards to the filter and keeps what it says, so that one run of the filter can be
measured — against the answers a person gave, or against another run.

The judge is `claude -p` carrying out the `filter-card` skill on a batch of cards.
Everything around it is plain Python: which cards, the batches, the calls in flight, the
writing, the counting. Nothing here decides anything about a card itself.

## What comes out

Verdicts, in the `verdicts` collection — one per card per run. A run is named on the
command line: `live` is the filter as it stands in production, one verdict per card and
rewritten each time the card is judged; any other name is an evaluation run, kept whole
so two of them can be compared.

A verdict never becomes an answer on its own. The eval set is `answers`, and only a
person writes there.

## Running it

Cards come from the `cards` collection, so put them there first. Then, from the
repository root:

```
python -m judge.run --run NAME [--rules SET] [--set NAME] [--answered] [--source S]
                    [--from DATE] [--to DATE] [--limit N] [--batch N] [--parallel N]
                    [--model M] [--dry-run]
```

- `--rules` — which rules from the `rules` collection the filter is given: `active`
  (the default), `none`, or names separated by commas. `active,NAME` is how a draft
  is put through the gate: the active rules plus the candidate. The set is recorded
  on the run, and a run cannot be resumed with a different one.
- `--set` — only the cards of a named set from the `sets` collection. A set is
  written once and never edited, so two runs over the same one are comparable.
- `--answered` — only cards that have an answer: the eval set.
- `--source`, `--from`, `--to` — one source, a span of posting days (`--to` exclusive).
- `--limit` — at most this many cards.
- `--batch`, `--parallel` — cards per call, calls in flight (default 10 and 5).
- `--model` — the model that judges (default `sonnet`). Verdicts from different
  models are not comparable, so every run of one comparison uses the same one.
- `--dry-run` — say which cards would be judged, and stop.

Start small — one day, one channel — before a run over everything:

```
python -m judge.run --run before --rules none --answered --source t.me/a_channel --from 2026-05-01 --to 2026-05-02
```

The rules go to the filter as one JSON file beside the cards — name, the reason each
lifts, and when. The filter reports on each verdict which of them lifted a reason off
the card. A rule name the filter was not given fails the batch, and so does a rule named
as applied while the reason it lifts is still on the card.

A card that already has a verdict in the run is skipped, so a run that stopped halfway
is finished by running it again with the same name. A batch whose reply cannot be read
is reported and nothing from it is written; the same rerun picks it up.

Ten cards take the judge about a minute and cost a few cents.

The judge is a Claude Code session in this repository and reads its instructions like
any other, including the one about a working tree with uncommitted changes: it stops and
asks instead of judging, and every batch fails with no JSON in the reply. Commit or stash
before a run, and do not edit the tree while one is on. A reply that could not be read is
kept under the working material, in `judge-failed/`, to be looked at.

## Measuring a run

```
python -m judge.report --run NAME [--base RUN] [--out FILE]
```

On its own, a run is measured against the answers: how many verdicts agree, and every
disagreement in full — the card, what the person said, what the filter said. A verdict
agrees when both sides accept, or both refuse and every reason the filter gave is one the
person gave too: the person ticks every reason that applies and the filter need not, but
it must not name one the person did not see.

Every report names the rules each run was given. With `--base`, two runs are set
against the answers side by side, and the cards on which they differ are listed as
*fixed* (base wrong, run right), *broken* (base right, run wrong) or *moved* (both
wrong, differently). That is how a candidate is judged: a better count than the base on
the same answers, and nothing broken that it was not worth.

`--list` names the runs there are.

## Deciding a rule

```
python -m judge.gate --rule NAME --run RUN --base BASE [--dry-run]
```

`RUN` was given the draft rule, `BASE` judged the same cards without it. The rule is
judged on the cards it fired on — the verdicts in `RUN` that name it — because two runs
of the same judge already differ on a few cards in every hundred, and a rule's effect
would drown in that. It passes when it fixed more of those cards than it broke and broke
none on `accept` itself; then it becomes `active`, otherwise `rejected`. The numbers are
written on the rule either way, and `--dry-run` shows them without deciding.

## Files

| | |
| --- | --- |
| `run.py` | selects the cards, batches them, asks the judge, writes the verdicts |
| `report.py` | counts and lists — against the answers, or against another run |
| `gate.py` | decides a draft rule from a run with it against a run without it |
