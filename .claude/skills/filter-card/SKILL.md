---
name: filter-card
description: Decide whether a card is an event worth keeping, and return the verdict — accepted, or refused with reasons from a closed list. Use when asked to filter, triage or sort cards, to judge whether posts are events, or when the user runs /filter-card. Takes cards as paths to card JSON files, or as text pasted as it stands, and optionally a file of rules to judge by.
---

# filter-card

A card is one post as it stood in its source. This skill answers one question about it —
**is this an event a person could go to?** — and returns the answer as JSON.

It writes nothing anywhere, reads nothing but the cards and the rules it was given, and
changes no file in the tree. The answer is what the caller does something with.

## Arguments

Cards, in either form, one or several:

- **a path** to a card JSON file — `id`, `source`, `date`, `text`, `links`. Read it as
  it is; the skill does not care where the file lives.
- **the text** of a card, pasted as it stands. Then there is no identity and no posting
  date, and the text is judged on its own.

With no card given, ask for one.

Rules, optionally — **a path** to a JSON file holding an array of objects with `name`,
`reason` and `text`, or rules written out in the request the same way. A rule is of one
form: *if the text says such-and-such, do not give this reason* — `reason` is the one it
lifts, from the table below, and `text` says when. The skill does not know or care where
a rule stands with whoever wrote it; every rule it is given is in force. Given no rules,
the cards are judged by section 1 alone.

## 1. Judge the card

An event a person could go to has a when and a where: a reader could decide to be there.
A card that carries one is accepted. Anything else is refused, with every reason below
that applies to it — often more than one, as a roundup of undated events is both a
roundup and undated.

| Reason | What it means |
|---|---|
| `missing_event` | no event in the text: news, a photograph, a thought, the channel about itself |
| `missing_time` | an event, but no date or time |
| `missing_place` | an event, but no venue, or none a reader could find |
| `multiple_events` | a roundup: several events, none of them the subject of the card |
| `not_visit_worthy` | something happening in the city rather than an event to attend: a closed bridge, a jam, roadworks |
| `unknown` | none of the above fits, or the card cannot be read with confidence — `note` says what stopped you |

Reach for a named reason first. When none of them fits the card, or the card leaves you
unsure what it even is, refuse it as `unknown` and write in `note` what you could not
settle — one or two sentences, plainly. An honest `unknown` is worth more than the
nearest label forced onto a card it does not describe: it shows where the list falls
short, while a wrong label hides it. `unknown` can stand alone, or beside the reasons
that do fit.

Judge the card by what it says. A date given relative to the posting date — *"tomorrow at
seven"* — is a date, and a venue the card names is a venue whether or not you know the
place. But nothing is supplied from outside the card: an event whose venue is only
implied by the channel it was posted in has no venue.

## 2. Lift a reason by the rules

Rules come in after the judgement, and only for a card section 1 refused. Judge every
card first, without them. Then, for each refused card, take the rules whose `reason` is
among the card's reasons — no other rule is consulted for it — and ask of each whether
the card's text says what the rule's `text` describes. Where it does, lift that reason
and put the rule's `name` into the verdict's `rules`. A card left with no reason is
accepted.

A rule lifts its own reason and nothing else. It does not add a reason, does not touch
the other reasons the card carries, and does not reopen the judgement of section 1: a
card that was refused for two reasons and meets a rule for one of them stays refused
for the other. An accepted card is not looked at again.

## 3. Return the verdict

One JSON array, in a fenced `json` block, one object per card in the order the cards were
given, and nothing else in the reply:

```json
[
  {"source": "t.me/a_channel", "externalId": "1234", "accept": true, "reasons": [], "rules": []},
  {"source": "t.me/a_channel", "externalId": "1235", "accept": false, "reasons": ["missing_time", "missing_place"], "rules": []},
  {"source": "t.me/a_channel", "externalId": "1236", "accept": false, "reasons": ["unknown"], "rules": [], "note": "a rehearsal open to anyone who asks the door — no listed reason covers a standing invitation with no occasion"},
  {"source": "t.me/a_channel", "externalId": "1237", "accept": false, "reasons": ["missing_place"], "rules": ["open-daily-is-a-time"]}
]
```

| Field | |
|---|---|
| `source` | the card's `source`, as the file gives it |
| `externalId` | the card's `id`, as a string |
| `accept` | whether the card is an event worth keeping |
| `reasons` | why it was refused, after the rules; `[]` when it was accepted |
| `rules` | the `name` of every rule that lifted a reason off the card; `[]` when none did or none were given |
| `note` | what could not be settled; only with `unknown`, left out otherwise |

A card given as text has no identity: leave `source` and `externalId` out of its object
rather than inventing them.
