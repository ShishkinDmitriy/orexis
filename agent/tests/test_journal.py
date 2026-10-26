"""The journal (`agent/journal.py`): events kept for good, the log kept for its window unless an incident keeps the
minutes before it, served read-only over the SPARQL protocol — and every word an event writes declared by the
package that writes it."""

from __future__ import annotations

import ast
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pyoxigraph as ox
import pytest

from agent import clock
from agent.journal import INCIDENT, Handler, Journal, ask, install, journal, mint, serve
from agent.runtime import Runtime, boot

AGENT = Path(__file__).resolve().parents[1]
HANOI = AGENT.parent / "world" / "hanoi"
NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")


def _record(message: str, level: int = logging.INFO) -> logging.LogRecord:
    return logging.LogRecord("planning", level, __file__, 1, message, (), None)


def _messages(j: Journal) -> list[str]:
    return sorted(r["m"].value for r in j.store.query(
        "SELECT ?m WHERE { ?r a <http://example.org/orexis#LogRecord> ; <http://example.org/orexis#message> ?m }",
        use_default_graph_as_union=True))


def test_the_log_is_kept_for_its_window_and_swept_after():
    at = [NOW]
    j = Journal(window_s=60, now=lambda: at[0])
    j.remark(_record("first"))
    at[0] = NOW + timedelta(seconds=30)
    j.remark(_record("second"))
    assert j.sweep(NOW + timedelta(seconds=70)) == 1 and _messages(j) == ["second"]
    assert j.sweep(NOW + timedelta(seconds=100)) == 1 and _messages(j) == []


def test_an_incident_keeps_the_window_before_it_and_nothing_older():
    at = [NOW]
    j = Journal(window_s=60, now=lambda: at[0])
    for n, seconds in enumerate((0, 50, 100)):
        at[0] = NOW + timedelta(seconds=seconds)
        j.remark(_record(f"line {n}"))
    at[0] = NOW + timedelta(seconds=120)
    j.remark(_record("the want stood unreachable", logging.ERROR))
    j.sweep(NOW + timedelta(hours=1))
    assert _messages(j) == ["line 2", "the want stood unreachable"], \
        "what came in the minute before the incident, and the incident, are kept; what came before that is not"


def test_an_incident_keeps_the_window_says_so_and_an_event_is_kept_for_good():
    at = [NOW]
    j = Journal(window_s=60, now=lambda: at[0])
    j.remark(_record("before"))
    event = mint()
    at[0] = NOW + timedelta(seconds=10)
    j.record(event, [], incident=True)
    assert ox.Quad(event, _TYPE, INCIDENT, event) in j.store, "an incident's entry says it is one"
    j.sweep(NOW + timedelta(days=1))
    assert _messages(j) == ["before"]
    assert ox.NamedNode(event.value) in set(j.store.named_graphs()), "an event is its own graph, and never swept"


def test_a_warning_is_an_incident_and_a_traceback_is_kept_with_its_record():
    j = Journal(window_s=60, now=lambda: NOW)
    handler = Handler(j)
    try:
        raise RuntimeError("a pass raised")
    except RuntimeError:
        import sys
        record = logging.LogRecord("runtime", logging.ERROR, __file__, 1, "stopping", (), sys.exc_info())
    handler.emit(record)
    handler.emit(logging.LogRecord("sensing", logging.WARNING, __file__, 1, "probe silent", (), None))
    (stopping, silent) = _messages(j)[1], _messages(j)[0]
    assert "RuntimeError: a pass raised" in stopping and silent == "probe silent"
    assert len(list(j.store.query("SELECT ?r WHERE { ?r a <http://example.org/orexis#Incident> }",
                                  use_default_graph_as_union=True))) == 2


def test_the_deployment_says_which_classes_and_from_which_level_a_record_is_an_incident():
    """`JOURNAL_INCIDENTS` adds a class the vocabulary does not count, and `JOURNAL_INCIDENT_LEVEL` raises the level: a
    warning is then a line kept for its window and no more, and an error still an incident."""
    from agent.journal import incident_level, incidents

    env = {"JOURNAL_INCIDENT_LEVEL": "error", "JOURNAL_INCIDENTS": "http://example.org/test#Concluded http://example.org/test#Other"}
    assert (incident_level(env), incidents(env)) == (logging.ERROR, {"http://example.org/test#Concluded", "http://example.org/test#Other"})
    assert (incident_level({}), incidents({})) == (logging.WARNING, frozenset())
    assert incident_level({"JOURNAL_INCIDENT_LEVEL": "loud"}) == logging.WARNING, "a name that is no level is said, and WARNING holds"
    j = Journal(window_s=60, now=lambda: NOW, incident_level=incident_level(env), incidents=incidents(env))
    warned, failed = j.remark(_record("store refused", logging.WARNING)), j.remark(_record("pass raised", logging.ERROR))
    concluded = mint()
    j.record(concluded, [ox.Triple(concluded, _TYPE, ox.NamedNode("http://example.org/test#Concluded"))])
    marked = {q.subject for q in j.store.quads_for_pattern(None, _TYPE, INCIDENT, None)}
    assert marked == {failed, concluded} and warned not in marked


def test_the_endpoint_answers_queries_and_refuses_an_update():
    j = Journal(now=lambda: NOW)
    j.remark(_record("hello"))
    server = serve(j, "127.0.0.1", 0)
    url = f"http://127.0.0.1:{server.server_address[1]}/sparql"
    try:
        (row,) = ask(url, "SELECT ?m WHERE { ?r <http://example.org/orexis#message> ?m }")
        assert row["m"].value == "hello"
        with pytest.raises(HTTPError) as refused:
            urlopen(Request(url, data=b"INSERT DATA { <http://a> <http://b> <http://c> }", headers={"Content-Type": "application/sparql-query"}))
        assert refused.value.code == 400
        assert not list(j.store.quads_for_pattern(ox.NamedNode("http://a"), None, None))
    finally:
        server.shutdown()


def test_the_history_part_keeps_each_event_a_runtime_says_in_its_agents_journal(monkeypatch):
    """Hanoi's one agent, a journal installed for it and no series store: the history part is created for the
    journal alone, and the plan the pass published is in it."""
    ticks = iter(range(1, 10_000))
    monkeypatch.setattr(clock, "now", lambda: NOW + timedelta(seconds=next(ticks)))
    kept = Journal(now=lambda: NOW)
    install(kept, "hanoi")
    try:
        assert journal("hanoi") is kept and journal("someone else") is None
        runtime = Runtime(boot(HANOI, "hanoi"), "hanoi", budget=400)
        assert "history" in runtime.parts
        runtime.run(passes=1, poll_s=0)
    finally:
        install(None, "hanoi")
    published = list(kept.store.query(
        "SELECT ?plan WHERE { ?e a <http://example.org/orexis/planning#PlanPublished> ; <http://example.org/orexis/planning#published> ?plan }",
        use_default_graph_as_union=True))
    assert len(published) == 1


# ---------------------------------------------------------------- every word declared

_DECLARED_IN = sorted(AGENT.glob("*/ontology.ttl")) + [AGENT / "ontology.ttl"]
_OURS = ("http://example.org/orexis#", "http://example.org/orexis/")


def _declared() -> set[str]:
    out = set()
    for path in _DECLARED_IN:
        g = ox.Store()
        g.load(path=str(path), format=ox.RdfFormat.TURTLE, base_iri=path.as_uri())
        out |= {q.subject.value for q in g.quads_for_pattern(None, _TYPE, None) if isinstance(q.subject, ox.NamedNode)}
    return out


def _named_in_events() -> set[str]:
    """Every term an `events.py` builds a name of: a namespace constant plus a string, as `_term("holding")`,
    `ox.NamedNode(EXECUTION + "act")` and `ox.NamedNode(PLANNING + "published")` spell them."""
    out = set()
    for path in sorted(AGENT.glob("*/events.py")) + [AGENT / "journal.py"]:
        tree = ast.parse(path.read_text())
        spaces = {t.id: n.value.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                  for t in n.targets if isinstance(t, ast.Name) and isinstance(n.value, ast.Constant)
                  and isinstance(n.value.value, str) and n.value.value.startswith(_OURS)}
        spaces.update({"EXECUTION": "http://example.org/orexis/execution#", "OREXIS": "http://example.org/orexis#"})
        for n in ast.walk(tree):
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add) and isinstance(n.left, ast.Name) \
                    and n.left.id in spaces and isinstance(n.right, ast.Constant):
                out.add(spaces[n.left.id] + n.right.value)
            if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_term" and n.args and isinstance(n.args[0], ast.Constant):
                out.add(spaces["COORDINATION"] + n.args[0].value)
            if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "_KIND" for t in n.targets):
                out |= {spaces["COORDINATION"] + v.value for v in n.value.values}
    return out


def test_every_word_an_event_writes_is_declared_by_an_ontology():
    named = _named_in_events()
    assert {"http://example.org/orexis/planning#PlanPublished", "http://example.org/orexis/coordination#Foreseen",
            "http://example.org/orexis/execution#landed", "http://example.org/orexis#LogRecord"} <= named, \
        "the scan still finds what the events name"
    assert not named - _declared(), f"named by an event and declared by no ontology: {sorted(named - _declared())}"


def test_an_agent_run_to_its_end_leaves_its_journal_on_disk_with_its_plan_and_its_log(tmp_path, caplog):
    """`orexis-agent` with `--journal`: Hanoi's mover, run to a plan, leaves a store holding the plan it published and
    the lines it logged — the boot's among them — and the process holds no journal once it is done."""
    from agent import runtime as runtime_module

    caplog.set_level(logging.INFO)                           # the level `orexis-agent` logs at, which pytest's root is not
    assert runtime_module.main([str(HANOI), "hanoi", "--journal", str(tmp_path / "journal"), "--passes", "20"]) == 0
    assert journal() is None and journal("hanoi") is None, "nothing is left installed"
    import gc
    gc.collect()                                             # the agent's own store, let go, as its process would be
    kept = ox.Store.read_only(str(tmp_path / "journal"))
    asked = lambda text: list(kept.query(text, use_default_graph_as_union=True))
    assert asked("SELECT ?e WHERE { ?e a <http://example.org/orexis/planning#PlanPublished> }")
    assert any("booted from" in r["m"].value for r in asked(
        "SELECT ?m WHERE { ?r a <http://example.org/orexis#LogRecord> ; <http://example.org/orexis#message> ?m }"))
