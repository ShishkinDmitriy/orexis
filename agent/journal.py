"""The journal: what happened to one agent, in RDF, in a triplestore of the agent's own beside its beliefs and
apart from them — the events its packages say, kept for good, and its log, kept for the last minutes.

A JOURNAL IS WATCHED AND NEVER BELIEVED (knowledge/domain/kernel/journal.md). Nothing in it reaches a plan, and no
part reads it: the history part writes it (`agent/history/`), and a person reads it — `orexis-replay` draws it,
`orexis-explain` asks it — over the SPARQL endpoint the agent serves (`serve`). It is a second store and never a
graph of the belief base, so a reader of the journal is handed no belief, and the replay that reads it still opens
no belief volume (the-journal-is-the-agents-flight-recorder).

TWO KINDS OF ENTRY, each a named graph holding one node, named by it:
- an EVENT a package says, whatever its class — `planning:PlanPublished`, `execution:StepTaken`,
  `coordination:Concluded` — beneath `orexis:Event`, at its `prov:atTime`. Kept for good: it is the history.
- a LOG RECORD, `orexis:LogRecord`, what the code said in the log as it ran, its logger, level and message. Kept for
  the WINDOW, the last so many seconds (`JOURNAL_WINDOW_S`, ten minutes where nothing says), and swept after, unless
  an INCIDENT kept it: the minutes before an event typed `orexis:Incident`, or a record at WARNING or above, are kept
  for good beside it (`orexis:keptBy`), so what led up to a failure is there to read and what led up to nothing goes.
  That is the dash cam: the history is the flight data, the log the cockpit's voice.

THIS MODULE SITS BENEATH EVERY PACKAGE AND IMPORTS NOTHING OF `agent`, as `agent/series.py` does: an event's
triples are its package's words, which the package writes (`statements`), and the journal stamps the instant and
keeps the window. A JOURNAL IS FOUND as a sink is, by the agent it is for (`install`, `journal`), so a process walking
two couriers keeps two; a deployed agent is told where its store lives (`--journal`), and is handed one in memory
where it is told nothing — the endpoint and the log are then the process's alone to serve.
"""

from __future__ import annotations

import logging
import os
import threading
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pyoxigraph as ox

log = logging.getLogger("journal")

OREXIS = "http://example.org/orexis#"
PROV = "http://www.w3.org/ns/prov#"
_XSD = "http://www.w3.org/2001/XMLSchema#"
_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

EVENT = ox.NamedNode(OREXIS + "Event")
INCIDENT = ox.NamedNode(OREXIS + "Incident")
LOG_RECORD = ox.NamedNode(OREXIS + "LogRecord")
AT = ox.NamedNode(PROV + "atTime")
KEPT_BY = ox.NamedNode(OREXIS + "keptBy")
LOGGER = ox.NamedNode(OREXIS + "logger")
LEVEL = ox.NamedNode(OREXIS + "level")
MESSAGE = ox.NamedNode(OREXIS + "message")

#  HOW LONG THE LOG IS KEPT where no incident keeps it, in the agent's seconds, where the environment says nothing.
WINDOW_S = 600.0
#  HOW OFTEN THE WINDOW IS SWEPT, at most, in the agent's seconds: a sweep is one update, run as a record is written.
_SWEEP_S = 60.0
#  THE PORT THE ENDPOINT LISTENS ON INSIDE THE CONTAINER, where the environment says nothing: oxigraph's own.
PORT = 7878

#  THE LOG RECORDS AN INCIDENT KEEPS: every one inside the window before it, kept by nothing yet.
_KEEP_U = """
INSERT { GRAPH ?r { ?r <%(kept)s> <%(incident)s> } }
WHERE { GRAPH ?r { ?r a <%(record)s> ; <%(at)s> ?t } FILTER(?t >= %(since)s && ?t <= %(until)s)
        FILTER NOT EXISTS { GRAPH ?r { ?r <%(kept)s> ?any } } }"""
#  THE LOG RECORDS THE WINDOW HAS PASSED, kept by no incident.
_SWEPT_Q = """
SELECT ?r WHERE { GRAPH ?r { ?r a <%(record)s> ; <%(at)s> ?t } FILTER(?t < %(before)s)
                  FILTER NOT EXISTS { GRAPH ?r { ?r <%(kept)s> ?any } } }"""

#  EVERY JOURNAL, by the agent it is for — None for every agent the process runs, as a deployed one runs one.
_journals: dict[str | None, "Journal"] = {}


def instant(at: datetime) -> ox.Literal:
    """An instant as the journal writes it: an `xsd:dateTime`, with its zone."""
    return ox.Literal(at.isoformat(), datatype=ox.NamedNode(_XSD + "dateTime"))


def literal(value) -> ox.Literal:
    """A Python value as the literal it is: a boolean, an integer, a double, an instant or a text."""
    if isinstance(value, bool):
        return ox.Literal("true" if value else "false", datatype=ox.NamedNode(_XSD + "boolean"))
    if isinstance(value, int):
        return ox.Literal(str(value), datatype=ox.NamedNode(_XSD + "integer"))
    if isinstance(value, float):
        return ox.Literal(repr(value), datatype=ox.NamedNode(_XSD + "double"))
    if isinstance(value, datetime):
        return instant(value)
    return ox.Literal(str(value))


def mint() -> ox.NamedNode:
    """A name for an entry: a UUID's URN, unique across every agent's journal, so a replay reading several keeps them
    apart without renaming any."""
    return ox.NamedNode(f"urn:uuid:{uuid.uuid4()}")


class Journal:
    """One agent's journal over `store` — a pyoxigraph store of its own, on disk or in memory — keeping its log for
    `window_s` of the agent's seconds, read off `now`."""

    def __init__(self, store: ox.Store | None = None, window_s: float = WINDOW_S, now=None):
        self.store = store if store is not None else ox.Store()
        self.window = timedelta(seconds=window_s)
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._swept: datetime | None = None

    def record(self, node: ox.NamedNode, triples, at: datetime | None = None) -> None:
        """Keep the entry `node` — its `triples`, which say what it is — at `at`, or now: a graph named by it, its
        instant stamped. An entry typed `orexis:Incident` keeps the window of log before it."""
        at = at or self._now()
        triples = [*triples, ox.Triple(node, AT, instant(at))]
        self.store.extend([ox.Quad(t.subject, t.predicate, t.object, node) for t in triples])
        if any(t.subject == node and t.predicate == _TYPE and t.object == INCIDENT for t in triples):
            self.keep(node, at)
        self._sweep(at)

    def remark(self, record: logging.LogRecord, at: datetime | None = None) -> ox.NamedNode:
        """Keep a log record — at WARNING or above an incident, keeping the window before it."""
        node = mint()
        message = record.getMessage()
        if record.exc_info:
            message += "\n" + "".join(traceback.format_exception(*record.exc_info)).rstrip()
        triples = [ox.Triple(node, _TYPE, LOG_RECORD), ox.Triple(node, _TYPE, EVENT),
                   ox.Triple(node, LOGGER, ox.Literal(record.name)), ox.Triple(node, LEVEL, ox.Literal(record.levelname)),
                   ox.Triple(node, MESSAGE, ox.Literal(message))]
        if record.levelno >= logging.WARNING:
            triples.append(ox.Triple(node, _TYPE, INCIDENT))
        self.record(node, triples, at)
        return node

    def keep(self, incident: ox.NamedNode, at: datetime) -> None:
        """Keep for good, beside `incident` at `at`, every log record of the window before it."""
        self.store.update(_KEEP_U % {"kept": KEPT_BY.value, "incident": incident.value, "record": LOG_RECORD.value,
                                     "at": AT.value, "since": instant(at - self.window), "until": instant(at)})

    def sweep(self, now: datetime | None = None) -> int:
        """Take out every log record the window has passed that no incident keeps; how many."""
        now = now or self._now()
        gone = [r["r"] for r in self.store.query(_SWEPT_Q % {"record": LOG_RECORD.value, "at": AT.value,
                                                              "kept": KEPT_BY.value, "before": instant(now - self.window)})]
        for graph in gone:
            self.store.remove_graph(graph)
        self._swept = now
        return len(gone)

    def _sweep(self, now: datetime) -> None:
        if self._swept is None or (now - self._swept).total_seconds() >= _SWEEP_S:
            self.sweep(now)

    def flush(self) -> None:
        """What is written reaches the disk, where the store is on one."""
        try:
            self.store.flush()
        except Exception:                                                  # noqa: BLE001 — an in-memory store
            pass


class Handler(logging.Handler):
    """The log, kept in a journal: every record at the handler's level, as `Journal.remark` keeps it."""

    def __init__(self, journal: Journal, level: int = logging.INFO):
        super().__init__(level)
        self.journal = journal

    def emit(self, record: logging.LogRecord) -> None:
        if record.name == log.name:
            return                                                          # the journal says nothing of itself
        try:
            self.journal.remark(record)
        except Exception:                                                   # noqa: BLE001
            self.handleError(record)


def install(journal: Journal | None, agent: str | None = None) -> None:
    """Make `journal` the one `agent`'s events go to — every agent's the process runs, where none is named — or none."""
    if journal is None:
        _journals.pop(agent, None)
    else:
        _journals[agent] = journal


def journal(agent: str | None = None) -> Journal | None:
    """The journal `agent`'s events go to — its own where one is installed for it, the process's otherwise — or None,
    and then no event is made into triples at all."""
    return _journals.get(agent) if agent is not None and agent in _journals else _journals.get(None)


def window_s(environ=None) -> float:
    """How long the log is kept, in the agent's seconds: `JOURNAL_WINDOW_S`, or ten minutes."""
    env = os.environ if environ is None else environ
    return float(env.get("JOURNAL_WINDOW_S") or WINDOW_S)


# ---------------------------------------------------------------- the endpoint

#  WHAT AN ANSWER IS SERIALISED AS, by what the query answers: the SPARQL results' JSON for a select and an ask, and
#  N-Triples for a construct and a describe.
_RESULTS = "application/sparql-results+json"
_TRIPLES = "application/n-triples"


def answer(store: ox.Store, text: str) -> tuple[str, bytes]:
    """What the SPARQL protocol answers `text` with over `store`: its media type and its body. Every graph is the
    default graph, so an open pattern reads every entry; `GRAPH` still names one. A query is all it answers: an update
    does not parse as one, and is refused."""
    results = store.query(text, use_default_graph_as_union=True)
    if isinstance(results, ox.QueryTriples):
        return _TRIPLES, results.serialize(format=ox.RdfFormat.N_TRIPLES)
    return _RESULTS, results.serialize(format=ox.QueryResultsFormat.JSON)


def serve(journal_: Journal, host: str = "127.0.0.1", port: int = PORT) -> ThreadingHTTPServer:
    """Serve `journal_` read-only over the SPARQL protocol at `http://<host>:<port>/sparql` — `GET ?query=`, or `POST` of
    `application/sparql-query` or a form — on a thread of its own, which reads the store and never writes it; the
    server, to shut down. Nothing else is served: the journal alone, never a belief."""

    class Asked(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlparse(self.path)
            self._answer(url.path, parse_qs(url.query).get("query", [None])[0])

        def do_POST(self):
            url = urlparse(self.path)
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode()
            kind = (self.headers.get("Content-Type") or "").split(";")[0].strip()
            text = body if kind == "application/sparql-query" else parse_qs(body).get("query", [None])[0]
            self._answer(url.path, text)

        def _answer(self, path: str, text: str | None):
            if path != "/sparql":
                return self._said(404, "text/plain", b"the journal answers at /sparql\n")
            if not text:
                return self._said(400, "text/plain", b"a query is asked as ?query= or a body\n")
            try:
                kind, body = answer(journal_.store, text)
            except (SyntaxError, ValueError) as exc:
                return self._said(400, "text/plain", f"{exc}\n".encode())
            self._said(200, kind, body)

        def _said(self, status: int, kind: str, body: bytes):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):                              # noqa: A002 — the base class's name
            pass

    server = ThreadingHTTPServer((host, port), Asked)
    threading.Thread(target=server.serve_forever, name="journal", daemon=True).start()
    log.info("the journal answers at http://%s:%d/sparql", host, server.server_address[1])
    return server


def ask(url: str, text: str, timeout: float = 30.0) -> ox.QuerySolutions | ox.QueryBoolean:
    """A select or an ask over the journal at `url`, as its endpoint answers — what a reader outside the agent calls."""
    from urllib.request import Request, urlopen

    request = Request(url, data=text.encode(), headers={"Content-Type": "application/sparql-query", "Accept": _RESULTS})
    with urlopen(request, timeout=timeout) as response:
        return ox.parse_query_results(response.read(), format=ox.QueryResultsFormat.JSON)

