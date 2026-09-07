---
name: observe-record
description: Score how one post landed in memory — its schedule, its event, its place — and say what could be better. Use when asked to observe, check or score what a post left in xmemory against the post itself, or when the user runs /observe-record. Takes the post's source and number, and the memory to look in.
---

# observe-record

One post went into memory. This skill asks whether what came out of it is right,
and returns three marks — **schedule**, **event**, **place** — with what is wrong
with each and what would keep it from happening again.

It writes nothing anywhere. The marks are what the caller does something with.

## Arguments

- the post: a **source** and its **number**, `t.me/a_channel 1234`;
- the **memory** to look in: the xmemory instance whose `read` tool is available
  to this session, named in the request.

With either missing, ask for it.

## 1. Read the post

```
python -m storage.show_card SOURCE NUMBER
```

The text, the posting date and the links, as they stood in the source. Everything
below is judged against this and nothing else: what the post does not say, memory
was not meant to know.

## 2. Ask memory what it holds

Ask, never dump. Memory is the whole city's, not this post's, and a listing of
everything in it would neither fit nor mean anything. Six questions are enough,
and each is about this post:

1. What the post produced — the event, its occurrences and the places they are
   held at — found by the source and the post's number.
2. Whether the venue is **reachable from the event**: how many occurrences the
   event has, and which places hang off them. Ask this outright rather than
   inferring it from question 1 — a place can sit in memory under the right
   name and address with nothing leading to it, and an answer that names the
   place does not by itself say the event reaches it.
3. Places whose **name** resembles the venue this post names.
4. Places at the **same address**, whatever they are called.
5. Events whose **title** resembles this one's.
6. What else memory has **at the same time** as this event's occurrences.

Questions 3–6 are how a duplicate shows itself: the same venue written twice, the
same event announced by two posts, two records standing in one slot. An answer to
them is a suspicion, not a verdict — see section 3.

**Ask for the key field first.** A record whose field is empty drops silently out
of an answer that asked for that field, so a place with no address does not come
back at all when the question asks for addresses. Ask for names and titles first,
then ask about the one record you are interested in.

## 3. Settle a suspicion

Two records that look alike are not yet a duplicate. When memory returns something
resembling this post's event or venue, take **that** record's post number from
memory and read that post the same way:

```
python -m storage.show_card SOURCE NUMBER
```

Two posts about the same concert are a duplicate; two concerts of the same
performer on different days are not. Two spellings of one venue are a duplicate;
two halls in one building are not. Settle it by the posts, not by the strings.

## 4. Mark the three

Each mark is 5, 3 or 0, and each is given for its own part.

**Schedule** — when the event is held.

| | |
|---|---|
| 5 | every date and time the post gives is in memory, and nothing beyond it |
| 3 | occurrences are there and readable, but a reader gets less than the post said |
| 0 | no occurrence at all, or an occurrence that contradicts the post |

**Event** — the event as a record.

| | |
|---|---|
| 5 | the record is the only one for this event: either nothing like it was there, or memory recognised what was and added to it |
| 3 | the event is readable, but either it is a second record of one already held, or `title` and `description` do not carry what the post says about it |
| 0 | any one of: the post's event is not in memory; it has no occurrence; no place is reachable from it. A record nothing leads to is worth nothing, however well its own fields are filled |

**Place** — the venue as a record.

| | |
|---|---|
| 5 | the only record for this venue: nothing like it was there, or memory recognised what was |
| 3 | the venue is readable, but either it is a second record of one already held, or `name` and `address` do not carry what the post says — the address standing in for a missing name, or an address the post gives and the record does not |
| 0 | either: the venue is not in memory; or it is in memory and no occurrence of this event leads to it. Right name and right address do not lift this — a venue nothing reaches is a venue nobody finds |

A post that names no venue at all, or no date at all, is not a fault of memory:
mark that part 5 and say so in `why`.

An event left with no occurrence usually takes the other two marks down with it,
because a venue is reached through an occurrence and there is none. Do not soften
that: three zeros on one post say the post is wholly lost, which is the thing
worth seeing.

## 5. Name what is wrong

Every mark below 5 carries at least one label, from this list and no other. Where
nothing here fits, use `other` and say in `why` what the list is missing — that is
how the list learns it is short.

| Schedule | |
|---|---|
| `no-occurrences` | the post gives opening hours or a season rather than dates, and nothing was recorded |
| `mode-collapsed` | a run of many days became one or two occurrences |
| `doors-time` | the time of the doors was taken for the time it starts |
| `end-missing` | the post gives an end or a duration and the occurrence has no end |
| `time-lost` | the day is right and the time of day is not, though the post gives it |
| `wrong-date` | a date that is not the one the post gives |
| `occurrence-duplicate` | the same occurrence recorded more than once |

| Event | |
|---|---|
| `duplicate` | a second record of an event memory already held |
| `title-generic` | the title is empty, or a bare word anyone could have written |
| `facts-lost` | the post says something substantial about the event and the record does not |
| `not-found` | nothing in memory came from this post |
| `unlinked` | the event has no occurrence, or no place through one |

| Place | |
|---|---|
| `duplicate` | a second record of a venue memory already held |
| `name-is-address` | the address stands where the name should be |
| `address-missing` | the post gives an address and the record has none |
| `two-places-in-one` | one record holding two venues |
| `not-found` | the post names a venue and memory has none |
| `unlinked` | the venue is in memory and no occurrence leads to it |

## 6. Return the marks

One JSON object, in a fenced `json` block, and nothing else in the reply:

```json
{
  "source": "t.me/a_channel",
  "externalId": "1234",
  "asked": ["what the post produced", "places named like «…»", "events titled like «…»"],
  "schedule": {"score": 0, "labels": ["no-occurrences"], "why": "the post gives «ежедневно 11:00–19:00» and no date; memory holds no occurrence, so the event is unreachable in time"},
  "event": {"score": 3, "labels": ["duplicate"], "why": "the same concert is already held under a title differing by one word; both posts announce the night of 3 October"},
  "place": {"score": 5, "labels": [], "why": "one record, name and address as the post gives them"},
  "proposal": "recognise an event by its title ignoring case and quotation marks"
}
```

| Field | |
|---|---|
| `asked` | what you asked memory, in your own words, one line each |
| `score` | 5, 3 or 0 |
| `labels` | every label that applies; `[]` only with a 5 |
| `why` | one or two sentences: what memory holds, what the post said, why that is the mark |
| `proposal` | one sentence on what would keep the worst of these from happening again, or `null` when all three are 5 |

Say what you saw, not what you would like to have seen. A mark of 5 on a part
memory got right is worth as much as a 0 on a part it did not.
