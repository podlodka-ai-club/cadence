"""Where cards go once a parser has built them.

A parser hands every card it builds to a sink and never decides what happens
next. Two of them keep what they are given — one writes JSON files, the other
puts cards in the database — and a queue or a process launched per card would
fit behind the same two methods:

    with JsonFileSink(root) as sink:
        for card in cards:
            sink.send(card)

`MongoSink` lives in `parsers.sinks.mongo` and is imported from there, not from
here: it needs a database driver, and a parser that only writes files should not
have to install one.
"""
from parsers.sinks.base import CountingSink, PrintSink, Sink
from parsers.sinks.json_files import JsonFileSink

__all__ = ["Sink", "CountingSink", "PrintSink", "JsonFileSink"]
