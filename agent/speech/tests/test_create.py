"""Speech's part: it says a document as the agent said it, and tells each agent it is to by its own
`told` signal — which, linked, reaches every transport that can tell a peer."""

from __future__ import annotations

import pyoxigraph as ox

from agent.speech.create import create

from .test_said import ME, T, _doc, store  # noqa: F401 — the fixture


class _Transport:
    def __init__(self):
        self.told = []

    def tell_to(self, to, document):
        self.told.append(to)


def test_its_part_believes_what_was_said_and_tells_each_agent(store, stand_in_runtime):  # noqa: F811
    runtime = stand_in_runtime(store, ME, None)
    part, transport = create(runtime), _Transport()
    part.link({"speech": part, "transport": transport})
    assert part.say(document=_doc(T + "round", "open"), to=[T + "rose", T + "fern"]) == [T + "round"]
    assert transport.told == [T + "rose", T + "fern"]


def test_a_statement_said_and_one_heard_are_each_an_event_carrying_what_it_said(store, stand_in_runtime):  # noqa: F811
    """Said, with whom it was told to; heard, as a statement written that a peer said — each carrying the statement's
    triples, kept in a journal as the history part keeps them. (The kind a statement says it is rides beside them
    where the vocabulary puts it beneath the statement; this store's vocabulary puts nothing there.)"""
    from datetime import datetime, timezone

    from agent.journal import Journal, mint
    from agent.speech.heard import heard

    now = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
    runtime = stand_in_runtime(store, ME, now)
    part, journal = create(runtime), Journal()
    for signal in (part.said, part.heard):
        signal.connect(lambda e: journal.record(node := mint(), e.statements(node), e.at))
    part.link({"speech": part})
    part.start(runtime)
    part.say(document=_doc(T + "round", "open"), to=[T + "rose"])
    (kind, stated), = [(k, h) for k, h in runtime.heard]
    for graph in heard(store, ME, _doc(T + "bid", "two").dump(format=ox.RdfFormat.TRIG)):
        stated(graph)
    stated(T + "round")                      # what the agent said is no statement heard
    found = sorted((r["k"].value.rsplit("#", 1)[-1], r["g"].value, r["says"].value, r["to"].value if r["to"] else None)
                   for r in journal.store.query(f"""
PREFIX speech: <http://example.org/orexis/speech#>
SELECT ?k ?g ?says ?to WHERE {{ GRAPH ?e {{ ?e a ?k ; speech:statement ?g . ?g <{T}says> ?says .
  OPTIONAL {{ ?e speech:to ?to }} }} }}"""))
    assert found == [("Heard", T + "bid", "two", None), ("Said", T + "round", "open", T + "rose")]
