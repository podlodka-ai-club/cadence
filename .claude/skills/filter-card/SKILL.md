---
name: filter-card
description: Decide whether a card describes an event a person could attend. A card that does is written to the `City Events & Places` xmemory instance as an Event; a card that does not is rejected, with the reason in the report. Under doubt the skill consults the rules stored in the `Filter Rules` instance. Use when asked to filter, triage or sort cards, or to turn cards into events, or when the user runs /filter-card. Takes the path to the card's JSON file as its argument, and optionally an xmemory session id.
---

# filter-card

A card is one post as it stood in its source. This skill answers one question about it:
**is this an event?** — and acts on the answer:

| Verdict | What happens |
|---|---|
| `pass` | the card is written to `City Events & Places` as an `Event` (and its `Place`, if named) |
| `reject` | nothing is written; the report says why |

The skill changes no code and no files in the tree.

## Arguments

- **the card** — required: the path to one card, a JSON file with `id`, `source`, `date`,
  `text`, `links` — the shape every parser produces (see `parsers/README.md`). Read it
  as it is; the skill does not care where the file lives. With no path, ask for one.
- **session id** — optional: an xmemory session id, `claude-<10 lowercase letters>`.
  When given, use it; when not, generate one. Either way pass it as `session_id` on
  every xmemory call.

Given several paths, run the steps below for each card in turn; the rules (§2) are read
once.

## 1. Judge the card by its own text

Read the card and decide: is this an event a person could attend — something with a
when and a where that a reader could plan to go to — or an informational post (news,
an announcement, a list, an ad, a note from the channel about itself) that should be
rejected?

Grade the decision: **sure** or **in doubt**. Sure means a reader would not argue with
it. Doubt is anything else.

## 2. When in doubt, ask xmemory

Read the rules from `Filter Rules` — once per run, on the first doubt, and keep them for
the rest of it:

```
read(query="List every Rule with status Active (text).", read_mode="raw-tables")
```

Only `Active` rules count; a `Draft` rule is one the person has not confirmed yet and is
not applied. Each `Rule` is a plain-text instruction to you. Apply them to the card; a rule wins over
your own reading. If they settle it, the verdict is sure, and the report says which rule
decided. If they do not, `reject`, and say in the reason that the doubt stayed.

## 3. `pass` — write the event

One `write_async` to `City Events & Places` per card, as free text: the instance
extracts the `Event` (and the `Place`, linked through `event_place`) from it. Give it
the card's text as it stands, and the context the text alone lacks:

```
Source post <source>/<id>, posted <card date>.
Create an Event from this post. Dates in the text are relative to the posting date;
store date_start and date_end in ISO 8601. If a venue is named, create or reuse the
Place and link it to the event.

<card text>

Links: <card links>
```

Do not read the instance to check whether the event is there already; `Event` is keyed
by `name`, and a second write of the same event updates the same record. Do not invent
what the card does not say — leave `price`, `age`, `date_end` unset rather than guessed.

## 4. `reject` — return the reason

Nothing is written. The reason goes into the report: one or two sentences, in English,
stating what made the card not an event — *"a list of museums open late; nothing is
scheduled"* — and, when a stored rule decided, which one.

## 5. Report

One line per card: `<source>/<id>` — verdict — the event name or the reject reason. Mark
a verdict decided by a stored rule and a reject where the doubt stayed. Link one
`console_url` when an event was written.
