"""What every world's tests are held to beside what each test asserts: every belief and prediction a
running agent holds says on its row what it holds (a-graph-changes-in-place-and-its-row-says-what-it-holds).

A writer that changes a belief or a prediction stamps the hash of its content on the graph's row, so
a copy made of it can tell whether it is still right. A writer that forgets leaves a row that lies,
and nothing a world's own assertions read would notice; so after every test, every runtime the test
made or still holds is read whole, and a graph whose content hashes otherwise than its row says — or
whose row says no hash at all — fails the test, naming the graph and its kinds.

Every world's tests build their agents through `Runtime`, so the runtimes are what is followed, each
from its construction, however long it lives.
"""

from __future__ import annotations

import gc
import weakref

import pytest

from agent.hash_named_graph import digest_of
from agent.ontology import BELIEF, PREDICTION
from agent.runtime import Runtime
from agent.store import catalogue_of, graphs_of, rows

_RUNNING: "weakref.WeakSet[Runtime]" = weakref.WeakSet()
_made = Runtime.__init__


def _followed(self, *args, **kwargs):
    _made(self, *args, **kwargs)
    _RUNNING.add(self)


Runtime.__init__ = _followed

_STAMP_Q = """SELECT ?h (GROUP_CONCAT(STR(?k); separator=" ") AS ?kinds) WHERE {
  GRAPH $cat { $g a ?k . OPTIONAL { $g orexis:hash ?h } } } GROUP BY ?h"""


def unstamped(store) -> list[str]:
    """Every belief and prediction of `store` whose content hashes otherwise than its row says, or
    whose row says no hash, and every other graph whose row says a hash its content does not: the
    graph, and what its row says it is."""
    cat = catalogue_of(store)
    if cat is None:
        return []
    out = []
    stated = [r["g"] for r in rows(store, """SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
        ?g orexis:hash ?h } }""", ())]
    for graph in dict.fromkeys([*graphs_of(store, BELIEF, PREDICTION), *stated]):
        row = next(iter(rows(store, _STAMP_Q, (), cat=cat, g=graph)), {})
        said = row.get("h")
        if said != digest_of(store, graph):
            kinds = sorted({k.rsplit("#", 1)[-1] for k in row.get("kinds", "").split()})
            out.append(f"{graph} ({', '.join(kinds)}): the row says {said or 'no hash'}")
    return out


@pytest.fixture(autouse=True)
def every_belief_says_what_it_holds():
    yield
    gc.collect()                         # a runtime an earlier test let go is no runtime of this one
    lying = [line for runtime in list(_RUNNING) for line in unstamped(runtime.beliefs)]
    assert not lying, ("a belief or prediction was changed and its row not stamped "
                       "(a-graph-changes-in-place-and-its-row-says-what-it-holds):\n  " + "\n  ".join(lying))


#  THE INCREMENTAL REFRESH HELD TO A FULL ONE (#953, slice 5). `prepare_ground` keeps a copy whose
#  source's row says the hash the copy was made with, and `lay_ground` keeps a cut its patterns still
#  name; a copy kept that a full refresh would have made otherwise is the stale copy this exists to
#  forbid. So after every pass's grounds are laid, the imaginarium is filled again from nothing, beside,
#  and every graph that crossed or was cut must hold what the incremental one holds, with the same row.

import pyoxigraph as ox                                     # noqa: E402

from agent.planning import planner as _planner              # noqa: E402
from agent.planning.ontology import CHANGEABLE_GRAPH        # noqa: E402
from agent.planning.prepare_ground import CROSSING          # noqa: E402

_prepare, _lay = _planner.prepare_ground, _planner.lay_ground
_FILLED: dict = {}
_DRIFTED: list = []


def _prepared(beliefs, into, **kwargs):
    _FILLED[id(into)] = (beliefs, kwargs)
    return _prepare(beliefs, into, **kwargs)


def _laid(store, *args, **kwargs):
    made = _lay(store, *args, **kwargs)
    if id(store) in _FILLED:
        beliefs, filled = _FILLED[id(store)]
        whole = ox.Store()
        _prepare(beliefs, whole, **filled)
        _lay(whole, *args, **kwargs)
        _DRIFTED.extend(_apart(store, whole))
    return made


def _apart(kept, whole) -> list[str]:
    """Every graph that crossed or was cut that the two imaginaria hold otherwise, or one of them alone."""
    def held(store):
        cat = catalogue_of(store)
        out = {}
        for g in graphs_of(store, *CROSSING, CHANGEABLE_GRAPH):
            content = frozenset(store.quads_for_pattern(None, None, None, ox.NamedNode(g)))
            row = frozenset((q.predicate.value, str(q.object)) for q in
                            store.quads_for_pattern(ox.NamedNode(g), None, None, ox.NamedNode(cat))
                            if not isinstance(q.object, ox.BlankNode))
            out[g] = (content, row)
        return out
    a, b = held(kept), held(whole)
    made = {r["g"] for r in rows(kept, """SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
        ?g a planning:WantGraph ; orexis:arrivedBy orexis:Derived } }""", ())}
    out = []
    for g in sorted((set(a) | set(b)) - made):
        if a.get(g) != b.get(g):
            which = "kept alone" if g not in b else "full alone" if g not in a else (
                "its content" if a[g][0] != b[g][0] else "its row")
            if g in a and g in b and a[g][0] != b[g][0]:
                which += f" — kept only {sorted(map(str, a[g][0] - b[g][0]))[:3]} — full only {sorted(map(str, b[g][0] - a[g][0]))[:3]}"
            out.append(f"{g}: {which}")
    return out


@pytest.fixture(autouse=True)
def every_refresh_holds_what_a_full_one_would(monkeypatch):
    """Installed for a world's test alone and taken away after it, with every store it was handed: a
    belief base held past its test is a volume still locked when the next opens it."""
    _DRIFTED.clear()
    monkeypatch.setattr(_planner, "prepare_ground", _prepared)
    monkeypatch.setattr(_planner, "lay_ground", _laid)
    yield
    _FILLED.clear()
    drifted, _ = list(dict.fromkeys(_DRIFTED)), _DRIFTED.clear()
    assert not drifted, ("the imaginarium a pass refreshed holds otherwise than one filled from nothing "
                         "(#953, slice 5):\n  " + "\n  ".join(drifted))
