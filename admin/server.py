"""The page, and the requests behind it.

No framework: one page file, the rest is JSON. Three walks are served, and
each has the same three requests — where we are, a decision, move on:

    GET  /               answering: the page
    GET  /state          the card being asked about, the counts, the reasons
    POST /answer         record a decision and move on
    POST /skip           put the card aside for this run and move on

    GET  /review         going back over answers already given: the page
    GET  /review/state   the card, its answer, the counts, the reasons
    POST /review/answer  replace the answer and move on
    POST /review/next    leave the answer as it is and move on
    POST /review/back    step back to the card before this one
    POST /review/open    jump to the card named in the request

    GET  /confirm        going over the filter's verdicts that have no answer: the page
    GET  /confirm/state  the card, the verdict as the suggested answer, the counts
    POST /confirm/answer record a different answer and move on
    POST /confirm/next   take the verdict as the answer and move on
    POST /confirm/back   step back to the card before this one
    POST /confirm/open   jump to the card named in the request

Every decision replies with where the walk now stands, so one press is one
request. The panel writes to the database and has no notion of who is asking,
so it listens on the loopback address only.
"""
import json
import os

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from storage.answers import record
from storage.cards import upsert
from storage.schema import REASONS

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page.html")
HOST = "127.0.0.1"


def as_json(card):
    """A card as the page sees it. No verdict of any kind travels with it."""
    if card is None:
        return None
    return {
        "source": card.source,
        "externalId": card.id,
        "date": card.date.isoformat(),
        "text": card.text,
        "links": list(card.links),
    }


def decision(request):
    """The decision a request carries. Raises ValueError if it is not one."""
    accept = bool(request.get("accept"))
    reasons = request.get("reasons") or []
    if not accept and not reasons:
        raise ValueError("a refusal needs a reason")
    unknown = [reason for reason in reasons if reason not in REASONS]
    if unknown:
        raise ValueError("unknown reason: %s" % ", ".join(unknown))
    return accept, ([] if accept else reasons)


class Handler(BaseHTTPRequestHandler):
    db = None            # where decisions are written
    session = None       # the walk over cards with no answer yet
    open_review = None   # opens the walk back over the answers already given
    open_confirm = None  # opens the walk over the filter's verdicts without an answer
    review = None
    confirm = None

    def log_message(self, *args):
        pass  # the panel reports what it does; the request log adds noise

    # -- replies ---------------------------------------------------------

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_page(self):
        with open(PAGE, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    # -- where each walk stands ------------------------------------------

    def reviewing(self):
        """The walk over the answers, opened the first time it is asked for."""
        if Handler.review is None:
            Handler.review = Handler.open_review()
        return Handler.review

    def confirming(self):
        """The walk over the verdicts, opened the first time it is asked for."""
        if Handler.confirm is None:
            Handler.confirm = Handler.open_confirm()
        return Handler.confirm

    def walk_at(self, path):
        """The walk a path belongs to, and the state to reply with."""
        if path.startswith("/review/"):
            return self.reviewing(), self.review_state
        if path.startswith("/confirm/"):
            return self.confirming(), self.confirm_state
        return self.session, self.answering_state

    def answering_state(self):
        return {
            "mode": "answer",
            "card": as_json(self.session.current),
            "answer": None,
            "progress": self.session.progress,
            "reasons": REASONS,
        }

    def review_state(self):
        review = self.reviewing()
        return {
            "mode": "review",
            "card": as_json(review.current),
            "answer": review.answer,
            "progress": review.progress,
            "reasons": REASONS,
        }

    def confirm_state(self):
        confirm = self.confirming()
        return {
            "mode": "confirm",
            "card": as_json(confirm.current),
            "answer": confirm.answer,  # the filter's verdict, standing as the suggestion
            "progress": confirm.progress,
            "reasons": REASONS,
        }

    # -- routes ----------------------------------------------------------

    def do_GET(self):
        path = self.path.split("?", 1)[0]  # `/review?card=…` is the page; the query is the page's to read
        if path in ("/", "/review", "/confirm"):
            self.send_page()
        elif path == "/state":
            self.send_json(self.answering_state())
        elif path == "/review/state":
            self.send_json(self.review_state())
        elif path == "/confirm/state":
            self.send_json(self.confirm_state())
        else:
            self.send_json({"error": "no such route"}, status=404)

    def do_POST(self):
        prefix, _, action = self.path.rpartition("/")
        actions = {"": ("answer", "skip"), "/review": ("answer", "next", "back", "open"),
                   "/confirm": ("answer", "next", "back", "open")}
        if action not in actions.get(prefix, ()):
            self.send_json({"error": "no such route"}, status=404)
            return
        walk, state = self.walk_at(self.path)

        if action == "back":
            # Stepping back decides nothing, so it needs no card to agree with.
            walk.step_back()
            self.send_json(state())
            return

        try:
            request = self.body()
        except ValueError:
            self.send_json({"error": "the request is not JSON"}, status=400)
            return

        if action == "open":
            # Jumping decides nothing either; the card it names only has to exist.
            if not walk.go_to(request.get("source"), str(request.get("externalId") or "")):
                self.send_json({"error": "no such card in this walk: %s/%s" % (
                    request.get("source"), request.get("externalId"))}, status=404)
                return
            self.send_json(state())
            return

        card = walk.take(request.get("source"), request.get("externalId"))
        if card is None:
            self.send_json(
                {"error": "that is not the card being asked about — the page has reloaded"},
                status=409)
            return

        if action == "answer":
            try:
                accept, reasons = decision(request)
            except ValueError as error:
                self.send_json({"error": str(error)}, status=400)
                return
            if prefix == "":
                upsert(Handler.db, [card])  # a card enters the set as it is answered
            record(Handler.db, card.source, card.id, accept, reasons)
        elif prefix == "/confirm":
            # Moving past a verdict is agreeing with it: it is written as the answer.
            suggested = walk.answer
            record(Handler.db, card.source, card.id, suggested["accept"], suggested["reasons"])

        if prefix == "":
            walk.pending.remove(card) if action == "answer" else walk.skip(card)
        else:
            if action == "answer":
                walk.replace(card, accept, reasons)
            walk.move_on()

        self.send_json(state())


def serve(db, session, open_review, open_confirm, port):
    """Run until interrupted. Returns when the person stops it."""
    Handler.db = db
    Handler.session = session
    Handler.open_review = open_review
    Handler.open_confirm = open_confirm
    server = ThreadingHTTPServer((HOST, port), Handler)
    print("answering at http://%s:%d, reviewing at /review, confirming verdicts at /confirm — stop with Ctrl+C"
          % (HOST, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
