# cadence

Posts about what is happening in a city are published faster than anyone can read them.
This project takes them as they come, decides which of them announce something a person
could go to, writes those into a memory that can be asked questions, and then checks its
own work: what it wrote is marked against what the post said, and what the marks complain
about is turned into a rule for the next write.

Everything here is a command run from this directory, and every part keeps what it
produces in MongoDB, so that any step can be repeated and two runs of it compared.

## The parts

| | |
| --- | --- |
| [`parsers/`](parsers/) | reads a source of posts and builds a card per post |
| [`storage/`](storage/) | the database: cards, answers, verdicts, rules, sets, observations |
| [`admin/`](admin/) | pages for answering cards by hand, one at a time |
| [`judge/`](judge/) | hands cards to the filter and measures what it said |
| [`memory/`](memory/) | writes cards into memory, marks how they landed, drafts and decides rules |
| [`scripts/`](scripts/), [`deploy/`](deploy/) | unattended launchers, and the service the parser runs under |

And the skills — the parts carried out by a model rather than by code, each with its own
instructions in `.claude/skills/`:

| | |
| --- | --- |
| `filter-card` | decides whether a card is an event worth keeping |
| `observe-record` | marks how one post landed in memory, and says what would keep the worst of it from happening again |
| `propose-rule` | words one instruction out of what the observers complained about — or says the fault is in the schema and a person must decide |
| `close-session`, `retrospective`, `manager` | the same loop applied to this repository's own work |

## The two loops

They are the same shape, and each is closed by a gate that decides on numbers rather than
on an opinion.

**The filter.** Cards are judged against answers a person gave; where the judge and the
person disagree, a rule is drafted; a run with the rule is set against a run without it,
and the rule becomes `active` or `rejected` — see [`judge/`](judge/).

**Memory.** Cards are written into an xmemory instance; an observer marks each against the
post it came from; the commonest complaint becomes a rule; the same cards are written into
a second instance with the rule in hand, marked again, and the two sets of marks decide it
— see [`memory/`](memory/).

Where the memory loop finds that no rule could help — the fault being in the schema memory
was given rather than in how it was read — it says so and stops, and a person decides.

## Getting started

Python, MongoDB, and `.env` at the root with `MONGO_URI` and `MONGO_DB`:

```
pip install -r requirements.txt
python -m storage.setup
```

Then the part you need: [`parsers/`](parsers/) to collect posts, [`judge/`](judge/) to
measure the filter, [`memory/`](memory/) to run the memory loop end to end.

`untracked/` is where working material goes — exports, logs, samples. Git keeps none of it.
