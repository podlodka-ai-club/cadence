"""The database: what is kept in it, and the commands that put it there.

Three parts, kept apart on purpose:

    schema.py       what each collection holds and the rules Mongo enforces
    mongo.py        credentials and the connection they open
    <command>.py    one task each, run with `python -m storage.<command>`

Nothing here decides anything about a card. The module stores what it is
given and refuses what does not fit the shape.
"""
