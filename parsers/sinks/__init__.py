"""Where cards go once a parser has built them.

A parser hands every card it builds to a sink and never decides what happens
next. Today the only sink that keeps anything writes JSON files; a database, a
queue, or a process launched per card all fit behind the same two methods:

    with JsonFileSink(root) as sink:
        for card in cards:
            sink.send(card)
"""
from parsers.sinks.base import CountingSink, Sink
from parsers.sinks.json_files import JsonFileSink

__all__ = ["Sink", "CountingSink", "JsonFileSink"]
