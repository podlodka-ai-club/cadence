# memory

Writes posts into an xmemory instance, asks an observer how each of them landed, turns
what the observers complain about into a rule for whoever writes the next one, and decides
that rule by the marks before it and after it. One turn of that loop is what this module
does; the loop closes only because the last step writes its answer where the first step
reads it.

## What comes out

Marks, in the `observations` collection — one per card per memory, three of them: the
times the event is held, the event itself, the venue. And a rule, in the `rules`
collection, addressed to `memory`: a draft while it is only proposed, `active` or
`rejected` once two memories have been set against each other.

Nothing here writes an answer of its own into memory, and nothing marks a card by hand.

## Running it

From the repository root, with `.env` filled in as `storage` describes and `xmemcli`
holding a credential of its own.

**Write a set of cards into an instance.**

```
python -m memory.send SET INSTANCE_ID [--rules NAME,…] [--from N]
```

The cards go in the order the set holds them — a later post merging onto an earlier one is
part of what is being written — each in a wrapper naming the source, the post's number,
when it was published, and the city and offset its dates are to be read in. `--rules` puts
the text of memory rules into that wrapper, the same words on every card of the set: an
instruction given to all of it, so that what it does to a card it was not drawn from is
visible too. Writing is the cheap half of working with memory; reading is not.

**Ask the instance a question.**

```
python -m memory.ask INSTANCE_ID QUESTION [--read-mode MODE]
```

The question in the words a person would ask it. Nothing is stored: the answer goes to the
screen. It is the plainest measure of what memory can and cannot do, and the only one that
needs no explaining.

**Mark how the cards landed.**

```
python -m memory.observe SET SERVER INSTANCE_ID [--limit N] [--cards S/N,…]
                         [--seed N] [--model M] [--parallel N]
```

A session per card, carrying out the `observe-record` skill, allowed only to question the
instance and print the post. `SERVER` is the MCP server the instance answers on and
`INSTANCE_ID` the same instance by its id — the first is how the observer reaches it, the
second what the marks are filed under. `--limit` takes that many cards at random and
`--seed` makes the choice repeatable; `--cards` names them exactly, which is how the same
cards are observed in a second memory.

Two things to know before a run. The working tree has to be clean: each session reads this
repository's instructions like any other and stops to ask about an uncommitted change
instead of observing. And this is the expensive step — an observation is three questions to
memory, worth about forty writes.

**Draft a rule from what the observers complained about.**

```
python -m memory.propose INSTANCE_ID --name NAME [--set NAME] [--label AXIS/LABEL]
                         [--control S/N,…] [--text FILE] [--dry-run]
```

The label blamed on the most cards is the one drafted about — where observers who never
saw each other's work name the same fault, the fault is in how memory reads posts rather
than in one post. What they wrote about those cards goes to a session
carrying out the `propose-rule` skill, which words it as one instruction; the draft is
printed and written to `rules` with the cards it was drawn from. How a rule is worded is
the skill's, so that the part meant to improve improves as a skill rather than as a string
in a module — which is also why that session, like the observer's, wants a clean tree.
`--label` picks the fault instead of taking the commonest, and takes more than one for a
fault that shows itself under several labels. `--control` adds cards the rule was not drawn
from, so that the gate can see what the instruction costs where it was not needed.
`--text` takes the wording from a file instead of a model, for a rule a person words
better; everything else — the cards, the origin, the numbers — is drawn the same way.

The skill answers with one of two things, and they go to different collections because
they are applied in different ways. A **rule** rides in the wrapper of every post and is
written to `rules`. A **finding** that no instruction could have helped — the fault being
in the schema memory was given — is written to `schema_changes` as a draft, and waits
there for whoever runs the loop to say what to write instead.

**Say what to write into the schema instead.**

```
python -m memory.approve NAME FILE
```

The finding names the sentence at fault; the file holds the sentence that replaces it,
worded for the schema the next memory is created with. It goes on the draft as `change`.
Writing it is the decision — a person's, or a session's that was shown the finding — and
the draft stays a draft until a memory has been written under the changed schema and the
gate has judged it.

**Decide the rule.**

```
python -m memory.gate NAME --before INSTANCE_ID --after INSTANCE_ID [--schema] [--dry-run]
```

Two memories hold the same set, one written without the rule and one with it. On the
rule's own cards: a card is fixed when its three marks add up to more than they did, broken
when any one of the three came out lower. The rule passes when it fixed at least one and
broke none, and the numbers go on it either way.

`--schema` decides a draft from `schema_changes` instead — the same arithmetic on the same
kind of evidence, written to the other collection. There the two memories differ by the
schema they were created with rather than by anything in the wrapper, and only a change
already worded through `memory.approve` can be judged.

Neither `propose`, `approve` nor `gate` asks memory anything — they read marks already
paid for.

## One turn of the loop

```
xmemcli instance create …                        a memory with nothing in it
python -m memory.send SET INSTANCE               the set, no rules
python -m memory.ask INSTANCE "…"                a question a person would ask
python -m memory.observe SET SERVER INSTANCE     what came of each card
python -m memory.propose INSTANCE --name NAME    the complaint, worded as a rule
xmemcli instance create …                        a second memory, as empty as the first
python -m memory.send SET INSTANCE2 --rules NAME the same set, the rule in the wrapper
python -m memory.observe SET SERVER2 INSTANCE2 --cards …    the rule's cards, marked again
python -m memory.gate NAME --before INSTANCE --after INSTANCE2
python -m memory.ask INSTANCE2 "…"               the same question, asked again
```

The second memory is empty rather than the first one written over: a memory holding the
earlier attempt would answer partly from it, and nothing could be told apart. Observing the
rule's cards rather than the whole set is what makes the second half affordable.

## Files

| | |
| --- | --- |
| `send.py` | writes the cards of a set into an instance, the rules in their wrapper |
| `ask.py` | puts one question to an instance and prints the answer |
| `observe.py` | a session per card, and the marks it returns |
| `propose.py` | the commonest complaint, worded as a draft rule |
| `approve.py` | the change a draft schema change is to make, said |
| `gate.py` | decides the rule by the marks of two memories |
