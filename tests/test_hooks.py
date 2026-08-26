"""A hook is a term (a-hook-is-a-term): every question the choir is asked is an `ag:Hook` some
ontology declares, every answer a module gives is to a declared one, and a string nobody
declared is refused rather than answered by silence."""

from __future__ import annotations

import pytest

from agent import loader
from agent.module import Module
from agent.ontology import AG, DESIRES, HANDLE, REPORTS, SEND
from conftest import build_agent, wired_sensors


def _provided_classes():
    return [cls for p in loader.packages() if p.kind != "kernel" for cls in p.provides()
            if isinstance(cls, type) and issubclass(cls, Module)]


def test_every_hook_a_module_answers_is_one_an_ontology_declares():
    declared = loader.hooks()
    assert declared, "no ontology declares a hook — the loader found nothing"
    classes = _provided_classes()
    assert classes, "no module classes found — the loader found nothing"
    unknown = sorted((cls.__name__, term) for cls in classes
                     for term in cls._hooks() if term not in declared)
    assert not unknown, f"modules answer hooks no ontology declares: {unknown}"


def test_the_kernels_defaults_carry_the_kernels_terms():
    assert Module._hooks()[DESIRES] == "desires"
    assert Module._hooks()[REPORTS] == "reports"


def test_an_override_by_name_inherits_the_term(monkeypatch):
    fern = build_agent("fern", monkeypatch=monkeypatch)
    keeper = fern.module("intention")
    assert keeper.answer(REPORTS) == keeper.reports, "reports() overridden by name still answers ag:reports"


def test_a_hook_nobody_declared_is_refused(monkeypatch):
    fern = build_agent("fern", monkeypatch=monkeypatch)
    with pytest.raises(ValueError, match="not a hook any ontology declares"):
        fern.ask("urn:orexis:nothing-of-the-sort")
    with pytest.raises(ValueError):
        fern.tell("send")   # the old raw string, not the term


def test_the_transport_answers_send_and_nothing_else_does(monkeypatch):
    fern = build_agent("fern", monkeypatch=monkeypatch)
    answering = [m.name for m in fern.modules if m.answer(SEND) is not None]
    assert answering == ["mqtt"]


# --- the rows (layered-by-timescale-and-interruptibility) --------------------------------

REACTIVE = AG + "Reactive"


def test_every_hook_declares_which_row_answering_it_belongs_to():
    """A hook without a row is a question nobody has placed: is answering it allowed to block,
    allowed to search, allowed to take a second? The row is a term because it partitions
    METHODS of one module — `SensingModule` answers in three rows — which no directory can."""
    rows, declared = loader.hook_rows(), loader.hooks()
    assert declared, "no ontology declares a hook"
    missing = sorted(declared - set(rows))
    assert not missing, f"hooks with no ag:row: {missing}"
    assert set(rows.values()) <= {AG + "Reactive", AG + "Progression", AG + "Deliberative"}


def test_the_rows_say_what_the_records_say():
    rows = loader.hook_rows()
    assert rows[HANDLE] == REACTIVE, "a message arriving is reactive: classify and write"
    assert rows[AG + "take"] == AG + "Progression", "taking a committed act spans time"
    assert rows[AG + "desireUrgency"] == AG + "Deliberative", "measuring a want is the search's"


def test_a_reactive_hook_never_reaches_the_planner(monkeypatch):
    """The rule the rows exist to enforce: *anything that searches belongs in deliberation,
    anything that must never block belongs in the reactive layer.* Delivering a message must
    not enter a search on the delivering thread.

    RECORDED, not raised: `Agent.tell` catches what a module throws, so an exception from
    inside the planner would be swallowed and the gate would pass while the defect stood.

    It was a strict xfail until #392 landed — the gardener's actuation answered a fresh
    reading by asking the search what to do about it, inside `handle`. It marks the want now
    and the pass runs on the mind's own thread, which is what this holds.

    The harness settles after every delivery (`conftest.deliver`), so the consequences are
    here to assert — on a thread that is still not this one.
    """
    import threading

    from agent.planner import Planner
    from conftest import genesis_store

    gardener = build_agent("gardener", genesis_store(world="loner"), monkeypatch)
    here, ran = threading.current_thread(), []
    plan = Planner.plan
    monkeypatch.setattr(Planner, "plan",
                        lambda self, desire: (ran.append(threading.current_thread()),
                                              plan(self, desire))[1])
    gardener.deliver("sensors/moisture_probe/reading", {"value": 0.10})
    assert not [t for t in ran if t is here], \
        "a reading was delivered and a search ran on the delivering thread"
