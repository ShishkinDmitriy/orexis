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
    whose row says no hash: the graph, and what its row says it is."""
    cat = catalogue_of(store)
    if cat is None:
        return []
    out = []
    for graph in graphs_of(store, BELIEF, PREDICTION):
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
