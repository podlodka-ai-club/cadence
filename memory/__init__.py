"""Putting posts into memory, questioning what came out, and learning from it.

Five commands, run with `python -m memory.<command>`:

    send      write the cards of a set into an xmemory instance
    ask       put one question to an instance and print the answer
    observe   mark how each card of a set landed in one instance
    propose   draft a rule from what the observations complain about
    gate      decide the rule from the observations of two instances

The loop they close is one turn long: write a set into memory, see what came
out, say in one instruction what should have been done differently, write the
same set into a second memory with the instruction in hand, and let the marks
of the two decide whether the instruction was worth keeping.
"""
