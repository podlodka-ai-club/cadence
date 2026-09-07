"""Put one question to an xmemory instance and print what comes back.

    python -m memory.ask INSTANCE_ID QUESTION [--read-mode MODE]

The question a person would ask — *куда можно сходить в субботу* — put to memory
as it stands. Nothing is stored and nothing is judged: the answer goes to the
screen, and whoever asked reads it. It is the plainest measure there is of what
memory can and cannot do, and the only one an outsider needs no explanation for.

`--read-mode` is the shape the answer comes back in: `single` (the default) for
one written answer, `raw` for the rows behind it.
"""
import argparse
import json
import subprocess
import sys

TIMEOUT = 900


def ask(instance, question, read_mode="single"):
    """Ask, and return what came back: the answer, and the whole envelope."""
    completed = subprocess.run(
        ["xmemcli", "--json", "--instance-id", instance,
         "read", question, "--read-mode", read_mode],
        capture_output=True, text=True, timeout=TIMEOUT,
    )
    try:
        envelope = json.loads(completed.stdout)
    except ValueError:
        raise SystemExit("xmemcli said nothing readable: %s" % (
            (completed.stderr or completed.stdout).strip()[-500:]))
    return envelope.get("answer"), envelope


def readable(answer):
    """The answer as it should be read: rows laid out, prose left alone."""
    if not isinstance(answer, str):
        return json.dumps(answer, ensure_ascii=False, indent=2)
    try:
        return json.dumps(json.loads(answer), ensure_ascii=False, indent=2)
    except ValueError:
        return answer


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("instance", metavar="INSTANCE_ID", help="the xmemory instance to ask")
    parser.add_argument("question", metavar="QUESTION", help="the question, in the words it would be asked in")
    parser.add_argument("--read-mode", default="single", choices=("single", "raw", "xresponse"),
                        help="the shape of the answer (default: single)")
    args = parser.parse_args(argv)

    answer, envelope = ask(args.instance, args.question, args.read_mode)
    if answer is None:
        raise SystemExit("no answer: %s" % json.dumps(envelope, ensure_ascii=False)[:500])
    print(readable(answer))


if __name__ == "__main__":
    main()
