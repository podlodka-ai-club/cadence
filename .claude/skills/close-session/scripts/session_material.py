#!/usr/bin/env python3
"""Extract the raw material close-session needs from a session transcript.

Emits one JSON object on stdout:

  session_id, transcript, cwd, project_name, started_at,
  human_messages[]  - what the person actually typed (rules, corrections)
  agent_activity[]  - subagent launches and the reports they came back with

The transcript is authoritative: it survives compaction, and it is the only
place the real session start time lives.

Subagents run asynchronously. The tool_result of an Agent call is a launch
receipt, not an answer — the answer arrives later as a <task-notification>
carried in an ordinary user record. Both facts are load-bearing here: the
receipt is dropped, and the notification is an agent report rather than
something the person said.
"""
import argparse
import json
import os
import re
import sys

NOISE = re.compile(
    r"<system-reminder>.*?</system-reminder>"
    r"|<local-command-[a-z-]+>.*?</local-command-[a-z-]+>",
    re.S,
)
COMMAND_ENVELOPE = re.compile(r"<command-(?:name|message|args)>", re.I)
TASK_NOTIFICATION = re.compile(r"<task-notification>(.*?)</task-notification>", re.S)
# The receipt names its own agentId and says not to quote it; it is not a report.
LAUNCH_RECEIPT = "Async agent launched successfully"
AGENT_TOOLS = {"Task", "Agent", "SendMessage", "Workflow"}


def project_dir(cwd):
    return os.path.join(
        os.path.expanduser("~"), ".claude", "projects", re.sub(r"[^A-Za-z0-9]", "-", cwd)
    )


def find_transcript(cwd, session_id=None):
    d = project_dir(cwd)
    if not os.path.isdir(d):
        return None
    if session_id:
        p = os.path.join(d, session_id + ".jsonl")
        return p if os.path.isfile(p) else None
    files = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".jsonl")]
    # The live session is the transcript being written to right now.
    return max(files, key=os.path.getmtime) if files else None


def records(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def parts(rec):
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return [p for p in content if isinstance(p, dict)] if isinstance(content, list) else []


def tag(body, name):
    m = re.search(r"<{0}>(.*?)</{0}>".format(name), body, re.S)
    return m.group(1).strip() if m else ""


def result_text(part):
    c = part.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(b.get("text", "") for b in c if isinstance(b, dict))
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    ap.add_argument("--session-id", default=None)
    ap.add_argument("--transcript", default=None,
                    help="explicit transcript path; bypasses discovery")
    ap.add_argument("--max-chars", type=int, default=4000,
                    help="per-item truncation; 0 disables")
    args = ap.parse_args()

    cwd = os.path.abspath(args.cwd)
    path = args.transcript or find_transcript(cwd, args.session_id)
    if not path or not os.path.isfile(path):
        json.dump({"error": "no transcript found", "searched": path or project_dir(cwd)},
                  sys.stdout)
        print()
        return 1

    def cut(s):
        if args.max_chars and len(s) > args.max_chars:
            return s[: args.max_chars] + "\n…[truncated]"
        return s

    out = {
        "session_id": None,
        "transcript": path,
        "cwd": cwd,
        "project_name": os.path.basename(cwd),
        "started_at": None,
        "human_messages": [],
        "agent_activity": [],
    }
    labels = {}  # tool_use_id -> label of the agent launched with it

    def note(ts, kind, label, text):
        text = text.strip()
        if text:
            out["agent_activity"].append(
                {"ts": ts, "kind": kind, "label": label, "text": cut(text)})

    for rec in records(path):
        out["session_id"] = out["session_id"] or rec.get("sessionId")
        ts = rec.get("timestamp")
        if ts and not out["started_at"]:
            out["started_at"] = ts
        rtype = rec.get("type")
        side = bool(rec.get("isSidechain"))

        if rtype == "user" and not rec.get("isMeta"):
            for p in parts(rec):
                if p.get("type") == "tool_result":
                    label = labels.get(p.get("tool_use_id"))
                    if not label:
                        continue  # an ordinary tool result, not an agent's
                    text = result_text(p)
                    if LAUNCH_RECEIPT in text:
                        continue  # a receipt, not a report — and not quotable
                    note(ts, "agent-report", label, text)

                elif p.get("type") == "text" and not side:
                    raw = p.get("text", "")
                    for body in TASK_NOTIFICATION.findall(raw):
                        summary = tag(body, "summary")
                        label = labels.get(tag(body, "tool-use-id")) or summary or "agent"
                        status = tag(body, "status")
                        note(ts, "agent-report", label,
                             "\n".join(x for x in (
                                 "status: " + status if status and status != "completed" else "",
                                 tag(body, "result")) if x))
                    # Whatever the person typed alongside the notification, if anything.
                    text = clean(TASK_NOTIFICATION.sub("", raw))
                    if text and not COMMAND_ENVELOPE.search(raw):
                        out["human_messages"].append({"ts": ts, "text": cut(text)})

        elif rtype == "assistant":
            for p in parts(rec):
                if p.get("type") == "tool_use" and p.get("name") in AGENT_TOOLS:
                    inp = p.get("input") or {}
                    label = "{}:{}".format(
                        p["name"], inp.get("description") or inp.get("subagent_type") or "")
                    labels[p.get("id")] = label
                    note(ts, "agent-launch", label,
                         str(inp.get("prompt") or inp.get("message") or ""))
                elif p.get("type") == "text" and side:
                    note(ts, "sidechain", "subagent", clean(p.get("text", "")))

    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


def clean(text):
    return NOISE.sub("", text).strip()


if __name__ == "__main__":
    sys.exit(main())
