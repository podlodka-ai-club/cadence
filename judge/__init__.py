"""Judging cards with the filter, and measuring what it said.

Two commands, run with `python -m judge.<command>`:

    run       hand cards to the filter-card skill, keep its verdicts
    report    compare the verdicts of a run with the answers, or with another run

The judge is `claude -p` carrying out the skill on a batch of cards; everything
around it — which cards, the batches, the parallelism, the writing, the
counting — is plain Python here. Nothing in this module decides anything about
a card itself.
"""
