"""Want rows, for the planning suites that read one and unmake one.

The snapshot machinery every case suite shares is `agent/conftest.py`, one level up. What is
here is the seed these two need and nobody else does.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

import pyoxigraph as ox

from agent.store import catalogue_of, update



# --- want rows, for the cases that read one and unmake one ---
#
#  ITS OWN CONSTANTS, spelled `_W_*`. This file already has a `NOW` and an `AGENT` and
#  they mean a different instant and a different agent; a second pair under the same
#  names would rebind them for every snapshot case in the module, silently. Measured:
#  17 of them went red.--------------------------------
#
#  ONE FIXTURE AND NO CONFTEST IMPORT. `_derived` and `_owe` were module-level functions two
#  test modules imported by name; a sibling module is importable only because pytest puts the
#  test's own directory on `sys.path`, and a second `conftest` anywhere else on it makes which
#  one you get a question about ordering. A fixture is the door pytest already opens.

_W_DESIRE = "urn:test:gardener.no_overdue_debts"
_W_HOLDER = "urn:test:gardener"
_W_AGENT = "gardener"
#  WHEN THE WRITE HAPPENS. A want's period starts at the instant it was derived, and that
#  instant is the caller's — so a test says it rather than patching a clock.
_W_NOW = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)


def _bare_store():
    """A bare store and NOTHING ELSE — which is the whole point of handing one in. The read
    took the holder's URI and the agent's id too, until those were seen for what they are:
    another aggregate root's identity, which a read over a store has no business holding.
    Whose the wants are is the store's own (rule 4: one agent, one volume)."""
    st = ox.Store()
    #  A catalogue, and the vocabulary's word on what a record is beneath: the read asks for
    #  graphs of WANTS and of RECORDS, and an obligations graph is one by the axiom the market
    #  declares. The derivation's own graphs need no axiom — they ARE graphs of wants, and
    #  that the derivation wrote them is `orexis:arrivedBy` rather than a class.
    update(st, """INSERT DATA {
  GRAPH <urn:test:catalogue> { <urn:test:catalogue> a orexis:CatalogueGraph . <urn:test:ontology> a orexis:OntologyGraph }
  GRAPH <urn:test:ontology> { <urn:test:ObligationsGraph> rdfs:subClassOf orexis:RecordGraph } }""")
    return st


def _graph_of(at, until) -> str:
    """The graph a want in trouble over one stretch is written to HERE — the case's own name,
    since a name is for eyes and every read asks the class. It was the derivation's own
    builder, imported, which made the read's cases depend on a writer's spelling."""
    stamp = lambda t: t.isoformat().replace(":", "").replace("+", "p")
    return f"urn:test:wants/{stamp(at)}--{stamp(until) if until else 'open'}"


def _derived(store, uri="urn:test:want", desire=_W_DESIRE, *, at=_W_NOW, until=None, side=None):
    """A want, written the way the DERIVATION writes one — a graph of wants that arrived
    derived, whose PERIOD IS THE STRETCH the trouble occupies, and provenance saying when the
    agent found it.

    WRITTEN HERE AND NOT THROUGH THE WRITER. `derive_wants` has a private `_write`, and these
    cases are about the READ: seeding them through the writer would test the two against each
    other, so a matching pair of mistakes would pass. The rows below are what `find_wants`
    claims to be able to read, said plainly, and if the writer stops producing them the
    snapshot cases in `tests/derive_wants/` are what say so.
    """
    graph = _graph_of(at, until)
    broke = f" ; orexis:violationIs <{side}>" if side else ""
    period = f' ; orexis:start "{at.isoformat()}"^^xsd:dateTime' + (
        f' ; orexis:end "{until.isoformat()}"^^xsd:dateTime' if until else "")
    update(store, f"""INSERT DATA {{
  GRAPH <{graph}> {{
    <{_W_HOLDER}> orexis:holds <{uri}> .
    <{uri}> a orexis:Want{broke} ;
        prov:generatedAtTime "{_W_NOW.isoformat()}"^^xsd:dateTime ;
        prov:wasDerivedFrom <{desire}> ;
        rdfs:label "a want under test" . }}
  GRAPH <{catalogue_of(store)}> {{
    <{graph}> a orexis:WantGraph , orexis:Graph ; orexis:arrivedBy orexis:Derived ;
        orexis:beliefsOf <{_W_HOLDER}> . }} }}""")
    #  THE PERIOD ONCE PER GRAPH, and this guard is the writer's own. A period is a BLANK NODE
    #  and a blank node in an `INSERT` is a new node every time it runs; several wants share a
    #  stretch's graph now, so asserting it per want gave the graph a period per want and every
    #  read joining through `dcterms:temporal` returned each want once per period.
    update(store, f"""
INSERT {{ GRAPH <{catalogue_of(store)}> {{ <{graph}> dcterms:temporal
      [ a dcterms:PeriodOfTime{period} ] . }} }}
WHERE  {{ GRAPH <{catalogue_of(store)}> {{ }}
          FILTER NOT EXISTS {{ GRAPH <{catalogue_of(store)}> {{ <{graph}> dcterms:temporal ?h }} }} }}""")


def _owe(store, uri):
    """A debt, written the way a LEDGER writes one — its own graph, classified its own family.

    THE FAMILY IS THIS CASE'S OWN WORD, not a package's. It was `market:ObligationsGraph`, and
    that prefix reached the store because the 1.0 assembly walked `packages/` and merged every
    ontology it found. This tree reads its own, so a package's word is not in its dictionary —
    which is the point of the tree being liftable, and which this case is the only thing that
    noticed. What the case is ABOUT is a record graph some package owns; which package is not
    part of the claim.
    It cannot be written through `save`, which classifies what it writes as the derivation's,
    and that is the point of the case below."""
    graph = f"http://example.org/orexis/market#obligations/gardener/{uri.rsplit(':', 1)[-1]}"
    update(store, f"""INSERT DATA {{
  GRAPH <{graph}> {{ <{uri}> a orexis:Want ; prov:wasDerivedFrom <{_W_DESIRE}> ;
      rdfs:label "a debt under test" . }}
  GRAPH <{catalogue_of(store)}> {{ <{graph}> a <urn:test:ObligationsGraph> , orexis:RecordGraph . }} }}""")


class _Wants:
    """A bare store and the two writers a want-row case seeds it with.

    **No world, no genesis, no agent.** A read over a store owns nothing, so a bare in-memory
    store is all one needs to exercise it — and that it suffices is the finding, because a
    read that needed a whole agent to stand up would be a part of one.

    **THE ROWS ARE WRITTEN HERE**, not through the derivation's own writer, so a read is never
    tested against the writer that seeds it: a matching pair of mistakes would pass. What the
    WRITER produces is `derive_wants/`, case by case, against the whole store it leaves.
    """

    desire, holder, agent, at = _W_DESIRE, _W_HOLDER, _W_AGENT, _W_NOW

    def __init__(self, store):
        self.store = store

    def derived(self, uri="urn:test:want", desire=_W_DESIRE, *, at=_W_NOW, until=None, side=None):
        _derived(self.store, uri, desire, at=at, until=until, side=side)

    def owed(self, uri):
        _owe(self.store, uri)

    def graph_of(self, at=_W_NOW, until=None) -> str:
        """The graph this fixture wrote a want of that stretch into."""
        return _graph_of(at, until)


@pytest.fixture
def wants():
    return _Wants(_bare_store())
