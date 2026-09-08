---
name: propose-rule
description: Word one instruction to whatever writes posts into a memory of city events, out of what observers complained about — or say that the fault is in the schema and whoever runs the loop must decide. Use when asked to propose or draft a memory rule from observations, or when the user runs /propose-rule. Takes the schema and the complaints as they stand.
---

# propose-rule

Several observers looked, one at a time and without seeing each other's work, at how posts
landed in a memory of city events. Each said what memory got wrong about one post and what
should have been done differently. Where they agree, the fault is in how memory reads posts
rather than in one post — and this skill says what to do about it: word one instruction to
whoever reads the next post, or report that no instruction can help because the fault is in
what memory was told to keep.

It writes nothing anywhere. What it returns is what the caller does something with.

## Arguments

Two things, in the request as it stands:

- **the schema** memory was given — the records it keeps, their fields, and what each of
  those is described as;
- **the complaints** — a line per card naming the post, the part of it that was marked
  down and why, and under it what that observer would have done instead.

With either missing, ask for it.

## 1. Read what they agree on

The complaints are about one fault, and the wording follows from what they have in common,
not from the worst of them. Read all of them before writing anything: one observer's
sentence is an anecdote, and five of them saying the same thing is the fault.

What a complaint says memory *did* is evidence. What a complaint proposes is a suggestion
from someone who saw one post — take the intent, not the wording.

## 2. Know what the system is for

Posts about what is happening in a city are read into memory one by one, as they are
published. Out of each, memory is meant to keep three things that hold together: the
event, when it is held, and where. A record missing any of the three is a record nobody
can do anything with — an event nobody can turn up to, a time belonging to nothing, a
venue nothing leads to.

The posts are written by people rather than by a database, and that is where the work is.
One event is announced in several posts under titles differing by a word. One venue is
written now by its name, now by its address, now by what locals call it. Times, spans and
durations are given loosely, in words rather than dates. Reading all of that into records
that line up with the records already there — the same event recognised as the same, the
same venue as the same — is what memory is for, and what it gets wrong.

What memory is asked for is a schedule, cut from whichever of the three sides the asker
holds: what is on at this venue, what is on at this time, when this event is on.

## 3. Read the schema as an instruction already given

The schema is not a description of memory: it is what memory was told to do, sentence by
sentence, and it was obeyed. So read it for two things.

**What can be kept at all.** An instruction to write down something the schema has no
place for writes down nothing. What a record is made of, which of its fields must be
filled, what may be left empty — all of it bounds what an instruction can ask for.

**What told memory to do the thing complained about.** A fault often traces to a sentence
that is doing exactly what it says. Find it before wording anything: a rule that argues
with a sentence of the schema has to say so plainly, or the two will simply disagree on
every post.

If the fault cannot be corrected by an instruction — the schema keeps no field for what
would have to be written, or the sentence that causes it is the schema's own and an
instruction would only contradict it on every post — then say so instead of wording a
rule. Name the record, the field and the sentence, and what would have to change there.
That verdict is the answer; a rule written to paper over it would be judged on cards it
was never able to fix.

## 4. What the rule has to be

The instruction rides in the context of **every** post memory is given, including all the
posts the complaints say nothing about. Two things are asked of it, and they pull against
each other.

**It must do no harm.**

- It must not swell memory with records that carry nothing. A memory padded out is not a
  memory improved, and whoever asks it a question pays for every record it holds.
- It must not leave more events without a time or without a venue than there were before.
  A record nothing reaches is worse than a thin one: it is invisible.
- A post the complaints are not about has to come out of it as it came out before.

**It must make the next write better** — a time read out of a post more exactly than it
was, an event recognised as one memory already holds, a venue recognised as one it
already knows.

Say when the instruction applies, in the words the posts themselves use, and say what to
do concretely enough that carrying it out decides nothing further.

Two to four sentences, in Russian: the posts are Russian and so is whoever reads them. No
list, no heading, no explaining why — the reader of this is not being persuaded, it is
being told.

## 5. Return one answer

One JSON object in a fenced `json` block, and nothing else in the reply:

```json
{"verdict": "rule", "text": "Если пост ... , то ... . Не ... ."}
```

`verdict` is `rule` when an instruction can carry the fix, and `text` is that instruction
as section 4 asks for it.

`verdict` is `schema` when it cannot, and `text` is then written for whoever will decide:
what in the schema causes the fault, and what would have to change there. English
or Russian, whichever says it plainer.
