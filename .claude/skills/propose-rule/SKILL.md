---
name: propose-rule
description: Word one instruction to whatever writes posts into a memory of city events, out of what observers complained about. Use when asked to propose or draft a memory rule from observations, or when the user runs /propose-rule. Takes the complaints as they stand.
---

# propose-rule

Several observers looked, one at a time and without seeing each other's work, at how posts
landed in a memory of city events. Each said what memory got wrong about one post and what
should have been done differently. Where they agree, the fault is in how memory reads posts
rather than in one post — and that is what this skill turns into a single instruction to
whoever reads the next one.

It writes nothing anywhere. The instruction is what the caller does something with.

## Arguments

The complaints, in the request as it stands: a line per card naming the post, the part of
it that was marked down and why, and under it what that observer would have done instead.
With no complaints in the request, ask for them.

## 1. Read what they agree on

The complaints are about one fault, and the wording follows from what they have in common,
not from the worst of them. Read all of them before writing anything: one observer's
sentence is an anecdote, and five of them saying the same thing is the fault.

What a complaint says memory *did* is evidence. What a complaint proposes is a suggestion
from someone who saw one post — take the intent, not the wording.

## 2. Know what memory can hold

The instruction has to be carried out against a store of a particular shape, and one that
cannot be followed leaves things exactly as they were.

- An **occurrence** is a moment: when it starts, and when it ends where the post says so.
  There is no repetition to store and no way to say «каждую субботу» — an instruction to
  record a recurrence records nothing at all.
- An occurrence stretched from the first day to the last is **one** evening in an answer,
  not many. A run of days a reader can turn up to is a run of occurrences. An occurrence
  left without an end is no better: it is still one moment, and whoever asks about a day
  in the middle of it is told nothing.
- An **event** is reached through its occurrences, and a **place** through them too. An
  event with no occurrence is in memory and findable by nobody.
- Memory is asked what a person can go to on a given day — «куда можно сходить 30 августа»
  — and answers with what falls on that day.
- Memory is fed a stream and not a book: a source writes about the same thing again, and
  the later post is read into memory as well. So an instruction that reaches a few weeks
  ahead need not reach further — what runs out is refilled by the next post about it.

## 3. Write one instruction

One instruction, in Russian: the posts are Russian and so is whoever reads them.

It rides in the context of **every** post memory is given, including the posts the
complaints say nothing about. So:

- **Say when it applies** — the kind of post it is about, in the words such a post uses.
  A post outside that kind must be left exactly as it was read before.
- **Say what to produce, out of what.** Concrete enough to act on without deciding
  anything: what record, from which words of the post.
- **Say where it stops.** An instruction that can be carried out forever will be. Where
  the post names an end, that is the limit. Where it names none — and a post about a
  thing that simply goes on usually names none — the instruction still has to stop
  somewhere that can be counted to from the post's own publication date. Stopping
  nowhere is not an answer: it puts the reader back where the complaint started.
- **Anchor dates to the post**, never to today — its publication date, or a date it names.
  A run repeated tomorrow has to come out the same way.

Two to four sentences. No list, no heading, no explaining why: the reader of this is not
being persuaded, it is being told.

## 4. Return the instruction

In a fenced `text` block, and nothing else in the reply:

```text
Если пост ... , то ... . Не ... .
```
