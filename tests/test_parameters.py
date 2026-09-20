"""Every action is held to what it says it takes.

An action declares its parameters (`orexis:takes`), its precondition projects one variable per
parameter, and its rules read them as `$tokens` — one spelling in three places
(an-action-takes-parameters). Nothing in the runtime checks that the three agree: a projected
variable the action does not declare is silently ignored, and a `$token` nobody declares refuses
only when a rule is simulated, inside a log line.

Both halves have already been wrong. `sensing:Observing` projected `?direction` that NOTHING in
its WHERE bound — an always-empty column, carried from row to step for every look any agent ever
took — and it was found by an audit run by hand, not by a gate. This is that audit.
"""

from __future__ import annotations

import glob
import re

import pytest
import rdflib

OREXIS = rdflib.Namespace("http://example.org/orexis#")
SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")

#  WHAT THE KERNEL BINDS ITSELF, so no action declares it: who I am and whom I act for; the
#  agent's own graph and the world's readings; the want and the pairs a precondition is offered;
#  how much the taker sized, when this step lands and how long since it was adopted; how long a
#  drift has had to drift. `$this` is SHACL's, in a shape rather than a rule.
KERNEL = frozenset({"me", "subject", "picks", "state", "want", "wants",
                    "litres", "lands", "since", "elapsed", "this"})
#  Projected beside the parameters: which want this row serves, and whom it is owed to. The
#  search branches on both, which is what keeps them the kernel's.
KERNEL_COLUMNS = frozenset({"want", "for_agent"})

RULES = (OREXIS.available, SH.construct, OREXIS.retracts, OREXIS.landsAfter,
         OREXIS.costs, OREXIS.waitsFor, OREXIS.lapsesAt, OREXIS.readyWhen)


@pytest.fixture(scope="module")
def vocabulary():
    g = rdflib.Graph()
    files = sorted(glob.glob("packages/*/actions.ttl") + glob.glob("packages/*/ontology.ttl"))
    assert files, "the glob stopped matching — no package vocabulary was read"
    for f in files + ["agent/ontology.ttl"]:
        g.parse(f, format="turtle")
    return g


def _actions(g):
    return sorted(set(g.subjects(rdflib.RDF.type, OREXIS.Action)), key=str)


def _local(iri) -> str:
    return str(iri).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def test_every_token_a_rule_reads_is_a_parameter_or_the_kernels(vocabulary):
    """A `$token` in a rule text is one the action declared, or one the kernel binds. Anything
    else reaches the binder as a token nobody bound, which REFUSES — at simulation time, in a
    log line nobody is reading."""
    actions = _actions(vocabulary)
    assert actions, "no actions found — the vocabulary stopped loading"
    for a in actions:
        takes = {_local(p) for p in vocabulary.objects(a, OREXIS.takes)}
        used = {t for pred in RULES for o in vocabulary.objects(a, pred)
                for t in re.findall(r"\$(\w+)", str(o))}
        assert not (used - takes - KERNEL), (
            f"{_local(a)} reads {sorted(used - takes - KERNEL)} but declares orexis:takes "
            f"{sorted(takes)} — declare the parameter or stop reading it")


def test_every_variable_a_precondition_projects_is_declared(vocabulary):
    """A projected variable the action does not declare is DROPPED when the row is built, so
    the column is written by the query, carried by nobody, and read as absent."""
    seen = 0
    for a in _actions(vocabulary):
        takes = {_local(p) for p in vocabulary.objects(a, OREXIS.takes)}
        for o in vocabulary.objects(a, OREXIS.available):
            m = re.search(r"SELECT\s+(?:DISTINCT\s+)?(.*?)\s+WHERE", str(o), re.S)
            assert m, f"{_local(a)}'s precondition is not a SELECT this test can read"
            projected = {v[1:] for v in m.group(1).split() if v.startswith("?")}
            seen += 1
            assert not (projected - takes - KERNEL_COLUMNS), (
                f"{_local(a)} projects {sorted(projected - takes - KERNEL_COLUMNS)} but declares "
                f"orexis:takes {sorted(takes)} — the column would be built and dropped")
    assert seen, "no precondition was read — every action lost its orexis:available?"


def test_an_action_that_can_be_planned_says_what_it_takes(vocabulary):
    """An action with a precondition is filled from its rows, so it takes something. One with
    neither is adopted by an event and may take nothing — the market's Presenting is the case,
    and it takes its venue anyway."""
    for a in _actions(vocabulary):
        if next(vocabulary.objects(a, OREXIS.available), None) is None:
            continue
        assert list(vocabulary.objects(a, OREXIS.takes)), (
            f"{_local(a)} has a precondition and declares no orexis:takes — every row it "
            f"affords would be identical, and two would collide in one world's graph")
