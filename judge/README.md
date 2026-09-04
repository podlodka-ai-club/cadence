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
python -m judge.run --run NAME [--answered] [--source S] [--from DATE] [--to DATE]
                    [--limit N] [--batch N] [--parallel N] [--model M] [--dry-run]
```

- `--answered` — only cards that have an answer: the eval set.
- `--source`, `--from`, `--to` — one source, a span of posting days (`--to` exclusive).
- `--limit` — at most this many cards.
- `--batch`, `--parallel` — cards per call, calls in flight (default 10 and 5).
- `--model` — the model that judges (default `sonnet`). Verdicts from different
  models are not comparable, so every run of one comparison uses the same one.
- `--dry-run` — say which cards would be judged, and stop.

Start small — one day, one channel — before a run over everything:

```
python -m judge.run --run before --answered --source t.me/a_channel --from 2026-05-01 --to 2026-05-02
```

A card that already has a verdict in the run is skipped, so a run that stopped halfway
is finished by running it again with the same name. A batch whose reply cannot be read
is reported and nothing from it is written; the same rerun picks it up.

Ten cards take the judge about a minute and cost a few cents.

## Measuring a run

```
python -m judge.report --run NAME [--base RUN] [--out FILE]
```

On its own, a run is measured against the answers: how many verdicts agree on `accept`,
how many on the reasons too, and every disagreement in full — the card, what the person
said, what the filter said.

With `--base`, two runs are set against the answers side by side, and the cards on
which they differ are listed as *fixed* (base wrong, run right), *broken* (base right,
run wrong) or *moved* (both wrong, differently). That is how a candidate is judged: a
better count than the base on the same answers, and nothing broken that it was not
worth.

`--list` names the runs there are.

## Files

| | |
| --- | --- |
| `run.py` | selects the cards, batches them, asks the judge, writes the verdicts |
| `report.py` | counts and lists — against the answers, or against another run |
