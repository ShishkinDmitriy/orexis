"""A hook is a term (a-hook-is-a-term): every question the choir is asked is an `ag:Hook` some
ontology declares, every answer a module gives is to a declared one, and a string nobody
declared is refused rather than answered by silence."""

from __future__ import annotations

import pytest

from agent import loader
from agent.module import Module
from agent.ontology import DESIRES, REPORTS, SEND
from conftest import build_agent


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
