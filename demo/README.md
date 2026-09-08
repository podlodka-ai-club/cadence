# demo

Everything one turn of the memory loop needs to run on a database and a memory that start
empty, and the skill that runs it.

## What is here

| | |
| --- | --- |
| `cards/` | the reference set: fifty posts, as the parser wrote them |
| `answers.json` | what a person said about each card — an event to keep, or not, and why |
| `set.json` | the set `eval-1`: the fifty cards in the order they are written into memory |
| `schema-v2.yaml` | the schema the first memory is created with |
| `question.txt` | the question put to memory before the change and after it |
| `observe.txt` | the cards the observer is sent to, one `source/number` per line |

The posts are real: the reference set is what the filter and memory are measured against,
so what a person ruled on has to be exactly what is written in.

## Running it

From the repository root, in Claude Code, with `.env` pointing at an empty database and
`xmemcli` holding a credential:

```
/demo
```

The skill in `.claude/skills/demo/` takes it from there: storage, the filter over the set,
a first memory and a question to it, the observer, a proposal, a second memory under the
change, the gate, and the same question again. It shows every command before running it
and leaves every answer on the screen. Two memories are created along the way; when the
account has no room for one, it asks for an instance to be deleted and waits.

## What comes out

Two answers to one question, one from each memory, and the gate's decision between them
in the database — on the rule in `rules`, or on the schema change in `schema_changes`,
whichever the turn proposed. The two memories are left standing.
