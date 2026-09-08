# cadence

## What we are doing

Personal agents are multiplying, and each of them knows its person better than the last.
People bring them everything, weekends included — *what is worth going to on Saturday?* —
and that is where an agent gets stuck. What is on in the city is scattered across a hundred
channels, written as prose meant for a reader, stale by Monday, and there is nothing to
query.

The answer is a place the agent can come to: ask in plain words, say what its person likes
and what they would rather avoid, and get back the events that fit — each with its time and
its place.

Building that takes five components:

1. **Collecting** the posts.
2. **Filtering** out what is not an event, and what is unsafe to take in.
3. **Parsing** each post into an event, its times and its places.
4. **Storing** all of it.
5. **A way in**, and the program that answers the questions.

Three of them — 2, 3 and 5 — are carried out by an LLM. That is why the project also needs
an internal process of its own:

- building an eval,
- marking how the LLM did, and proposing what would improve it,
- putting each proposal through the eval, and taking it or throwing it away.

## 1. Collecting

There can be any number of parsers, each reading a source of its own. What they have in
common is what comes out of them: a card written into the database, carrying

- an id unique within that source,
- the date of the post,
- what the post says, in the form it says it,

and whatever else is worth keeping.

Two are built:

- posts from Telegram channels as they are published,
- historical posts from Telegram channels, out of a JSON export of one.

Those sources were chosen because what they carry is about as undetermined as information
gets — far more so than a scraped website or an RSS feed — which makes them the right
material to tune the system as a whole on.

## 2. Filtering

What arrives from outside may be no event at all, may be something happening in the city
rather than something to attend — a closed road — may carry too little to act on, and may
carry a prompt injection. Every card goes to an agent, which returns a verdict.

The agent decides one thing, and decides it by the rules its skill lays down: does the card
go on to be parsed, or is it filtered out, and for which reason.

The filter is run through [`judge`](judge/), and the same command runs the eval — it is the arguments
that differ.

The reasons it can refuse for are a closed list. Extending it, or changing how the filter
judges, goes through the learning process below rather than through an edit made on the
spot.

### The eval of that agent

It starts with **the reference set**: cards a person has ruled on themselves. It grows out
of the filter's own work — the verdicts are opened in a UI of its own, [`admin`](admin/),
where the person goes through them one at a time and either agrees with what the filter
said or puts down their own answer instead. Every card they pass is one more card that
later comparisons stand on.

The filter judges by the rules its skill lays down,
[`filter-card`](.claude/skills/filter-card/SKILL.md). It is meant for a cheap or a local
model: one post, one decision, calling for neither much context nor much cleverness. At
launch it is handed rules out of the database on top of the skill, which is what makes a
comparison easy to set up — the rules in force, a candidate, or both.

Setting what came back against the reference set is a script's work and is done
deterministically: a verdict has a fixed shape — take or drop, with reasons from a closed
list — so agreement is counted rather than judged.

Where this stands. The runs so far have used a strong model, and against the reference set
it differs on some 2.5% of the take-or-drop decisions. The loop that would go from those
disagreements to a rule proposed on its own and put through the eval is not finished.

## 3. Parsing

The parsing and the storing are an outside system's: <https://xmemory.ai/>. Cards go to it
as they stand, with neither place nor time pulled out on our side, and what it holds is
read back by asking in words rather than in a query language. The schema those records are
kept under is in [Storage](#4-storage); how they are read, in [The way in](#5-the-way-in).

xmemory takes the extraction on itself, and it is a black box while it does so. Its work
therefore has to be watched: the faults found, and corrected where correcting them is
possible.

### The eval of that agent

Because xmemory is somebody else's system, what judges it is an observer — the skill
[`observe-record`](.claude/skills/observe-record/SKILL.md). It reads a record out of
xmemory and holds it against the card that record was made from. Knowing what the post
said, it marks how the parsing went in three planes: how much of the place came through,
how much of the event, and how much of the times it is held. The marks and its own remarks
go into MongoDB for whatever comes next.

What the observers left is then worked over by an agent of its own,
[`propose-rule`](.claude/skills/propose-rule/SKILL.md): it weighs what they ran into, how
often each kind of trouble comes up and what they proposed about it, and words a rule that
would settle it. What comes out is one of two things:

- a meta-rule added to the cards as they are sent to xmemory — the path not recommended;
- a change to the schema, or a fuller description of the data on xmemory's side.

Either way a new rule means a new memory: an instance is raised, the schema deployed onto
it, the eval sample written in, and the result weighed against the rules and the schema in
force. The same cards are observed again there, and it is the two sets of marks — before
the change and after it — that decide the proposal, rather than anyone's opinion of it.

The loop is run by the `memory` commands — write a set into an instance, ask it a question,
observe what it holds, propose, decide; [`memory/`](memory/) has them in detail.

## 4. Storage

Two stores, and what a record is for decides which one holds it.

### MongoDB

Everything the project holds about its own work.

- **Reference data** — the channels being read online, and how far into each of them the
  reading has got.
- **Event cards** — the post as it arrived from outside, the verdict the filter gave on it,
  and the answer a person gave about it. The three are kept apart rather than folded into
  one record: a card is judged in many runs and those verdicts have to stay comparable,
  while the person's answer is the one everything is measured against and is not to be
  confused with a machine's.
- **Eval material** — the cards gathered into named sets, the runs made over them, the
  rules, the marks an observer left on what memory did with a post, and what was proposed
  to improve the rules and the schema.

There is one schema, and a database uses the part of it that its work calls for. The one
production writes into holds the cards and the sources and nothing else; an evaluation
database is where the sets, the marks and the proposals accumulate.

### xmemory

What xmemory is and what it does is at <https://xmemory.ai/>.

The parsed data lives there:

- the places events are held at,
- the events themselves,
- the dates and times an event is held at, each tied to the place it is held at.

The schema those records are kept under is xmemory's own — an instance is created with it.
But changing that schema is part of the work here, since the eval can find the fault to be
in the schema rather than in how a post was read, so the version in force is kept in this
repository too: [`schema/xmemory-schema.md`](schema/xmemory-schema.md).

## 5. The way in

xmemory gives an agentic interface of its own: it takes a question asked in words and
answers it. Questions from outside can be relayed to it through the entry points it already
provides — <https://xmemory.ai/integration-overview/#manual-integrations>.

What this project has to put in front of that is proxies of its own — a chat bot, an MCP
server, and the like. None of them is built.

## Getting started

**Prerequisites**

- MongoDB — where [`storage`](storage/) writes.
- xmemory — an account, and an instance raised with the schema in
  [`schema/xmemory-schema.md`](schema/xmemory-schema.md); its MCP server added to Claude
  Code is how the observer reads that instance.
- Claude Code (`claude`) — the filter, the observer and `propose-rule` all run on it.
- Python 3.

**Init storage**

```
pip install -r requirements.txt
cp .env.example .env        # fill in MONGO_URI and MONGO_DB
python -m storage.setup
```

**Collect cards**

From a Telegram Desktop export:

```
python -m parsers.telegram_history <export> --out <dir>
python -m storage.load_cards <dir>
```

Or from the channels as they publish:

```
python -m parsers.telegram_live --login
python -m storage.add_source t.me/a_channel
python -m parsers.telegram_live
```

On a server that parser runs as a service — see [`deploy/`](deploy/).

**Filter them**

```
python -m judge.run --run live
```

The rest is in the READMEs of the parts: [`parsers/`](parsers/) for the sources,
[`storage/`](storage/) for what the database holds, [`judge/`](judge/) for the eval of the
filter, [`admin/`](admin/) for marking cards up by hand, [`memory/`](memory/) for the
memory loop, [`deploy/`](deploy/) for running the online parser as a service.

## Known issues

- The filter does not look at a card for a prompt injection.
- The filter's loop is not closed: wording a rule out of the disagreements is still a
  person's work, and nothing proposes one on its own.
