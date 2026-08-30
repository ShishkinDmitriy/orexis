"""An extension point is a term (a-hook-is-a-term): every question anything is asked is an
`assembly:Extension` some ontology declares, everything filling one fills a declared one, and a
string nobody declared is refused rather than answered by silence.

Two kinds now, and the difference is the whole of `the-assembly-is-not-the-mind`. A RUN-TIME
point is filled by a `Module` instance and declares which cognitive row answering belongs to; an
ASSEMBLY-TIME point is filled by a package's `__init__` and declares none, because a row says
whether answering may block or search and there is no planner to stay out of at assembly."""

from __future__ import annotations

import pytest

from assembly import loader
from assembly.contribute import contributions_of
from agent.module import Module
from orexis_modality_graph.ontology import AG, DESIRES, HANDLE, REPORTS, SEND
from conftest import build_agent, wired_sensors


def _provided_classes():
    return [cls for p in loader.packages() if p.kind != "kernel" for cls in p.provides()
            if isinstance(cls, type) and issubclass(cls, Module)]


def test_every_hook_a_module_answers_is_one_an_ontology_declares():
    declared = loader.extensions()
    assert declared, "no ontology declares a point — the loader found nothing"
    classes = _provided_classes()
    assert classes, "no module classes found — the loader found nothing"
    unknown = sorted((cls.__name__, term) for cls in classes
                     for term in contributions_of(cls) if term not in declared)
    assert not unknown, f"modules fill points no ontology declares: {unknown}"


def test_the_kernels_defaults_carry_the_kernels_terms():
    assert contributions_of(Module)[DESIRES] == "desires"
    assert contributions_of(Module)[REPORTS] == "reports"


def test_an_override_by_name_inherits_the_term(monkeypatch):
    fern = build_agent("fern", monkeypatch=monkeypatch)
    keeper = fern.module("intention")
    assert keeper.answer(REPORTS) == keeper.reports, "reports() overridden by name still answers ag:reports"


def test_a_hook_nobody_declared_is_refused(monkeypatch):
    fern = build_agent("fern", monkeypatch=monkeypatch)
    with pytest.raises(ValueError, match="not an extension point any ontology declares"):
        fern.ask("urn:orexis:nothing-of-the-sort")
    with pytest.raises(ValueError):
        fern.tell("send")   # the old raw string, not the term


def test_the_transport_answers_send_and_nothing_else_does(monkeypatch):
    fern = build_agent("fern", monkeypatch=monkeypatch)
    answering = [m.name for m in fern.modules if m.answer(SEND) is not None]
    assert answering == ["mqtt"]


# --- the rows (layered-by-timescale-and-interruptibility) --------------------------------

REACTIVE = AG + "Reactive"


ASSEMBLY = "http://example.org/orexis/assembly#"


def test_every_run_time_point_declares_which_row_answering_it_belongs_to():
    """A run-time point without a row is a question nobody has placed: is answering it allowed
    to block, allowed to search, allowed to take a second? The row is a term because it
    partitions METHODS of one module — `SensingModule` answers in three rows — which no
    directory can.

    ASSEMBLY-TIME points are exempt, and not as a concession: a row constrains the ANSWERER on
    the cognitive axis, and at assembly there is no planner to stay out of and no latency to
    keep. A fourth row value invented to keep the field total would constrain nothing, which is
    what `stage` and `tags` were before they were deleted."""
    rows, declared = loader.extension_rows(), loader.extensions()
    assert declared, "no ontology declares a point"
    run_time = {d for d in declared if not d.startswith(ASSEMBLY)}
    assert run_time, "no run-time points found — the split stopped matching"
    missing = sorted(run_time - set(rows))
    assert not missing, f"run-time points with no ag:row: {missing}"
    assert set(rows.values()) <= {AG + "Reactive", AG + "Progression", AG + "Deliberative"}
    stray = sorted(d for d in declared if d.startswith(ASSEMBLY) and d in rows)
    assert not stray, f"assembly-time points carrying a cognitive row: {stray}"


def test_the_rows_say_what_the_records_say():
    rows = loader.extension_rows()
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


# --- the published contract (the-assembly-is-not-the-mind) -------------------------------


def _declared_signatures() -> dict[str, str]:
    """point -> the parameter list it publishes, read off `assembly:signature`."""
    import rdflib

    out: dict[str, str] = {}
    sig = rdflib.URIRef("http://example.org/orexis/assembly#signature")
    for path in loader.ontology_files():
        graph = rdflib.Graph().parse(path, format="turtle")
        for term, value in graph.subject_objects(sig):
            out[str(term)] = str(value)
    return out


def test_every_point_publishes_the_signature_that_fills_it():
    """A point nobody can write against is a private callback with extra steps."""
    declared, signatures = loader.extensions(), _declared_signatures()
    assert declared, "no ontology declares a point"
    missing = sorted(declared - set(signatures))
    assert not missing, (
        "extension points publishing no `assembly:signature` — a package cannot fill a point "
        f"another package declared without one:\n  {missing}")


def test_what_fills_a_point_matches_the_signature_it_publishes():
    """Strict, on parameter names, and it passes today everywhere.

    Before the contract was published, a filler whose parameters did not match raised
    `TypeError` inside `Agent.ask`, which logged *could not answer* and stepped over — so a
    wrong signature was a module quietly not participating, which is indistinguishable from a
    module with no opinion. Measured across every point with more than one filler, all fourteen
    already agreed; what changes is that disagreeing is now a failed gate rather than a silence.

    Names only. Two fillers agreeing on `(subject_uri, observed_property, value)` while
    disagreeing about what `value` may be is not caught here, and the record says so.
    """
    import inspect
    import re

    signatures = _declared_signatures()
    assert signatures, "no signatures declared — the scan stopped matching"

    def params(text: str) -> list[str]:
        """Names in order, `*args` and `**kwargs` stripped of their stars as `inspect` reports
        them — a point that takes open keywords says so, and `record` does."""
        inside = text[text.index("(") + 1:text.rindex(")")]
        return [p.split("=")[0].split(":")[0].strip().lstrip("*")
                for p in inside.split(",") if p.strip()]

    wrong, checked = [], 0
    for cls in _provided_classes() + [Module]:
        for term, name in contributions_of(cls).items():
            if term not in signatures:
                continue
            actual = [p for p in inspect.signature(getattr(cls, name)).parameters
                      if p not in ("self", "cls")]
            expected = params(signatures[term])
            checked += 1
            if actual != expected:
                wrong.append(f"{cls.__name__}.{name} fills {term.rsplit('#', 1)[-1]} as "
                             f"({', '.join(actual)}) — it publishes ({', '.join(expected)})")
    assert checked, "no filled points found — the scan stopped matching"
    assert not wrong, (
        "a filler disagrees with the signature its point publishes. `Agent.ask` calls it "
        "straight through, so this is a module that would be logged and stepped over rather "
        "than a failure anyone would see:\n  " + "\n  ".join(wrong))
