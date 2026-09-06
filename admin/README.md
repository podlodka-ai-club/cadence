# admin

Three pages for deciding about cards by hand. One shows a card that has no answer yet, a
person decides whether it is an event, and the decision is stored — the card and the
answer about it together. The second goes back over the answers already given, so a
decision made under one understanding can be revisited once that understanding has
moved on. The third goes over the cards the filter has judged and the person has not,
with the filter's verdict as the suggestion: agreeing is one press, disagreeing is a
tick and a press, and either way the answer written is the person's.

The answer is `accept`, or `reject` with the reasons it was refused. A card is written
at the moment it is answered, so what is stored is exactly the cards that have a
decision, and a refused card is stored just as an accepted one is.

On the first two pages nothing about the card is coloured in advance: no verdict from
anywhere else is shown next to it. The answer given here is the one to measure against,
so it has to be the person's own. The confirming page shows the verdict on purpose — a
suggestion is faster to check than a card is to decide from nothing — and a verdict
never becomes an answer until the person has gone past it.

## Running it

Say which cards a run works on. That is personal and changes between runs, so it lives
in `admin/config.json`, which git ignores — copy `admin/config.example.json` to it:

```json
{
  "cards": ["<a directory of card files>"],
  "port": 8765
}
```

`cards` lists card files or directories searched at any depth, absolute or relative to
the repository. Then, from the repository root:

```
python -m admin [--config PATH] [--db NAME] [--verdicts RUN]
```

It prints an address to open. Where answers are written comes from `.env`, the same as
everywhere else; `--db` overrides it for one run. `--verdicts` names the run whose
verdicts the confirming page goes over — `live` unless said otherwise.

The panel listens on the loopback address only — it writes to the database and asks
nobody who they are.

## Answering

| | |
| --- | --- |
| `a` | accept: an event |
| `1`–`6` | tick a reason |
| `r`, `Enter` | reject with the ticked reasons — at least one is needed |
| `s`, `n` | skip, or move on without changing an answer |
| `p` | back to the card before this one, going over answers or verdicts |
| `o` | open a card by name, going over answers or verdicts |

A ticked reason makes the card a refusal: `accept` is out of reach until the ticks are
cleared, and `reject` until at least one is set.

Skipping puts a card aside for this run and stores nothing; it comes back the next time
the panel starts. A card already answered is not shown again, so stopping and starting
picks up where it left off.

The other page is at `/review`, and each page links to the other. It walks the cards
that have an answer, oldest first, with that answer shown and its reasons already
ticked: changing one's mind is a tick away rather than a decision from nothing. Moving
on leaves the answer as it was; answering replaces it, and stepping back reaches the
card before — from the end of the walk as well, which is where a misplaced press tends
to be noticed. The list is taken when the walk
starts, so a card answered afterwards joins it the next time the panel is started.

A card can be opened by name — `t.me/a_channel/1234`, typed into the box at the top
(`o` puts the cursor there) or given in the address as `/review?card=t.me/a_channel/1234`,
which is what a link from a report does. The walk jumps there and carries on from that
card.

The third page is at `/confirm`. It walks the cards that have a verdict in the run named
by `--verdicts` and no answer yet, oldest first, with the verdict shown and its reasons
ticked. Moving on writes the verdict as the answer; answering writes the corrected one.
Stepping back and opening by name work as on the review page. The list is taken when
the walk starts, so a verdict written afterwards joins it the next time the panel is
started.

## Files

| | |
| --- | --- |
| `config.py` | which cards a run works on |
| `session.py` | the three walks — cards without an answer, answers already given, verdicts to confirm |
| `server.py` | the pages and the routes behind them |
| `page.html` | the page itself, which serves all three walks |
