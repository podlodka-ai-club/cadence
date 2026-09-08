---
name: demo
description: Lead a session through one turn of the memory loop on memories that start empty — write the reference set in, ask memory a question, mark what came out, propose what to change, write a second memory under the change, decide it, ask again. Use when asked to run, show or demonstrate the loop end to end, or when the user runs /demo. Takes nothing; everything it needs is in demo/.
---

# demo

One turn of the loop, run in front of whoever is watching, from a database and a memory
holding nothing to a decided change and a second answer to the same question. Every step
is a command from this repository; this skill runs them in order, leaves their output on
the screen, and says what to look at in it. Nothing is summarised away: what memory
answers is the evidence, and the person reads it themselves.

Everything the turn needs is in `demo/`:

| | |
| --- | --- |
| `cards/` | the reference set, fifty posts as the parser wrote them |
| `answers.json` | what a person said about each: an event to keep, or not, and why |
| `set.json` | the set `eval-1`: the fifty cards in the order they are written into memory |
| `schema-v2.yaml` | the schema the first memory is created with |
| `question.txt` | the question put to both memories |
| `observe.txt` | the cards the observer is sent to, one `source/number` per line |

## How to behave throughout

- Run every command from the repository root, show it before it runs, and leave what it
  printed on the screen. Say in a line what the output shows; do not restate it.
- Say how long a step is going to take before starting it. Writing fifty posts takes
  twenty minutes; observing twelve cards, about twenty-five. A person watching a silent
  screen for that long should know it is not stuck.
- Delete nothing. An xmemory instance is deleted only by the person, in the console; when
  one has to go, ask, wait for them to say it is done, and go on.
- When a command fails, show the failure, say what it means, and stop. Do not work around
  it silently: a turn that had to be patched by hand is not the turn being shown.

## 0. Before anything

Check, and say in one line each what was found:

- the working tree is clean (`git status --porcelain` prints nothing) — the observer and
  the proposer start sessions of their own, and a session started on an uncommitted
  change stops to ask about it instead of working;
- `.env` exists, and `python -m storage.setup --help` runs — the interpreter has what it
  needs;
- `xmemcli --json instance list` answers — the credential works — and how many instances
  it lists;
- `claude --version` answers;
- the six entries of `demo/` are there.

Anything missing: say what, and stop.

## 1. The reference set into storage

```
python -m storage.setup
python -m storage.load_cards demo/cards
python -m storage.load_answers demo/answers.json
python -m storage.load_set demo/set.json
```

Fifty cards, fifty answers, one set. `setup` is idempotent and the loads are upserts, so
a database that already holds them is refreshed rather than doubled; a set already there
is refused by name, and that is fine — say so and go on.

## 2. The filter over the set

```
python -m judge.run --run demo --rules none --set eval-1
python -m judge.report --run demo
```

The filter decides card by card whether it is an event worth keeping, and the report sets
its verdicts against the answers. Point at the disagreements: those are the cards the
reference set exists for.

## 3. The first memory

**A free slot.** Run `xmemcli --json instance list` and say how many instances there are.
Then create:

```
xmemcli --json instance create --name cadence-demo-a --schema-file demo/schema-v2.yaml
```

If it is refused for want of room, show the refusal, ask the person to delete an instance
in the xmemory console and to say when it is done, then run the same command again. Take
`instance_id` from what comes back — call it A from here — and register the server the
observer will read it through:

```
claude mcp add xmemory-demo-a -- xmemcli mcp A
```

**Write the set in.** Twenty minutes; the log names each card as it lands.

```
python -m memory.send eval-1 A
```

**Ask.** The question in `demo/question.txt`, put as it stands:

```
python -m memory.ask A "$(cat demo/question.txt)"
```

Read the answer against the set: which of the fifty posts describe something a person
could go to on that day, and which of those are not in the answer. Name them. This is the
hole the rest of the turn is about, and it is the person's to see, so give them the time.

## 4. Mark what came out

The cards in `demo/observe.txt`, each observed in a session of its own that is told
nothing but the post's address and which memory to look in:

```
python -m memory.observe eval-1 xmemory-demo-a A --cards $(paste -sd, demo/observe.txt)
```

About twenty-five minutes. Each line is a card and its three marks — schedule, event,
place — and what the observer blamed. Point at the marks of zero and at what they share.

## 5. Propose

```
python -m memory.propose A --name demo-1
```

It counts what the observers blamed, takes the complaint blamed on most cards, and hands
those observers' words together with the schema to the `propose-rule` skill. Two answers
are possible, and both close the turn; say which one came back and what it means.

**A rule** — an instruction to whoever writes a post, printed and kept as a draft in
`rules`. Go to 6a.

**A finding** — that no instruction could correct this, because a sentence of the schema
itself tells memory to do what was complained about. The finding names the record, the
field and the sentence, and is kept as a draft in `schema_changes`. Go to 6b.

## 6a. The second memory, under the rule

A free slot as in step 3, then the same schema, the same set, the rule in the wrapper of
every post:

```
xmemcli --json instance create --name cadence-demo-b --schema-file demo/schema-v2.yaml
claude mcp add xmemory-demo-b -- xmemcli mcp B
python -m memory.send eval-1 B --rules demo-1
python -m memory.observe eval-1 xmemory-demo-b B --cards $(paste -sd, demo/observe.txt)
python -m memory.gate demo-1 --before A --after B
```

Then step 7.

## 6b. The second memory, under the changed schema

The finding is a question: what should the schema say instead. Answer it here, in the
person's seat, and show the answer before anything is created with it.

1. Word the change: the sentence that replaces the one the finding blamed, written for
   the schema — the record's own description, in the same voice as the rest of it, saying
   what memory is to do with the posts the complaint was about. Say nothing the finding
   did not ask for. Write it to `untracked/demo-change.txt` and show it.
2. Put it on the draft:

   ```
   python -m memory.approve demo-1 untracked/demo-change.txt
   ```

3. Make the schema the second memory is created with: a copy of `demo/schema-v2.yaml` at
   `untracked/demo-schema-v3.yaml` in which the blamed sentence is replaced by the change
   and nothing else is touched. Show the difference between the two files.
4. A free slot as in step 3, then the changed schema, the same set, no rule:

   ```
   xmemcli --json instance create --name cadence-demo-b --schema-file untracked/demo-schema-v3.yaml
   claude mcp add xmemory-demo-b -- xmemcli mcp B
   python -m memory.send eval-1 B
   python -m memory.observe eval-1 xmemory-demo-b B --cards $(paste -sd, demo/observe.txt)
   python -m memory.gate demo-1 --schema --before A --after B
   ```

Then step 7.

## 7. Ask again, and close

```
python -m memory.ask B "$(cat demo/question.txt)"
```

Put the two answers side by side — the one from step 3 and this one — and under them:

- what the gate decided and by what numbers: how many of the cards it judged were fixed,
  how many broken, and the marks before and after;
- which of the posts named as missing in step 3 are in the answer now, and which are not;
- what was not touched: the complaints the observers made that the change was not about
  are still there, and the next turn starts from them;
- what it took: the minutes each write and each observation ran, read off their logs.

That is the turn. Nothing is committed, nothing is deleted, and the two memories stay as
they are for the person to question further.
