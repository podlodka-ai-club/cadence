"""The page, and the requests behind it.

No framework: one page file, the rest is JSON. Two walks are served, and each
has the same three requests — where we are, a decision, move on:

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
    review = None

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

    # -- routes ----------------------------------------------------------

    def do_GET(self):
        path = self.path.split("?", 1)[0]  # `/review?card=…` is the page; the query is the page's to read
        if path in ("/", "/review"):
            self.send_page()
        elif path == "/state":
            self.send_json(self.answering_state())
        elif path == "/review/state":
            self.send_json(self.review_state())
        else:
            self.send_json({"error": "no such route"}, status=404)

    def do_POST(self):
        if self.path == "/review/back":
            # Stepping back decides nothing, so it needs no card to agree with.
            self.reviewing().step_back()
            self.send_json(self.review_state())
            return
        if self.path == "/review/open":
            # Jumping decides nothing either; the card it names only has to exist.
            try:
                request = self.body()
            except ValueError:
                self.send_json({"error": "the request is not JSON"}, status=400)
                return
            if not self.reviewing().go_to(request.get("source"), str(request.get("externalId") or "")):
                self.send_json({"error": "no answered card %s/%s" % (
                    request.get("source"), request.get("externalId"))}, status=404)
                return
            self.send_json(self.review_state())
            return
        if self.path not in ("/answer", "/skip", "/review/answer", "/review/next"):
            self.send_json({"error": "no such route"}, status=404)
            return
        walk = self.reviewing() if self.path.startswith("/review/") else self.session
        try:
            request = self.body()
        except ValueError:
            self.send_json({"error": "the request is not JSON"}, status=400)
            return

        card = walk.take(request.get("source"), request.get("externalId"))
        if card is None:
            self.send_json(
                {"error": "that is not the card being asked about — the page has reloaded"},
                status=409)
            return

        if self.path in ("/answer", "/review/answer"):
            try:
                accept, reasons = decision(request)
            except ValueError as error:
                self.send_json({"error": str(error)}, status=400)
                return
            if self.path == "/answer":
                upsert(Handler.db, [card])  # a card enters the set as it is answered
            record(Handler.db, card.source, card.id, accept, reasons)

        if self.path == "/answer":
            walk.pending.remove(card)
        elif self.path == "/skip":
            walk.skip(card)
        else:
            if self.path == "/review/answer":
                walk.replace(card, accept, reasons)
            walk.move_on()

        self.send_json(self.answering_state() if walk is self.session else self.review_state())


def serve(db, session, open_review, port):
    """Run until interrupted. Returns when the person stops it."""
    Handler.db = db
    Handler.session = session
    Handler.open_review = open_review
    server = ThreadingHTTPServer((HOST, port), Handler)
    print("answering at http://%s:%d, reviewing at http://%s:%d/review — stop with Ctrl+C"
          % (HOST, port, HOST, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
