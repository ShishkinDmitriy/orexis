"""The road, one case per file: given these beliefs and this desire, these wants and no others.

**No world, no genesis, no agent.** Each `road/*.trig` is one case, whole — the world the desire
ranges over, the levers whose effects say which properties move together, the desire with its
met-test, what the instruments read now, what is foreseen and from when, what already stands,
and a graph `:expected` saying which wants the road must leave standing, by name,
about what, and at what instant where at one. This file loads a case into a bare store, stands
a stand-in agent on it — the real `Desires` and `Wants` collections over that store, nothing
else — runs `pursuit.top_up`, and compares. A case costs milliseconds; the four world files
that covered the road end to end (`tests/test_greenhouse.py`, `test_foreseen.py`,
`test_one_road.py`, `test_pursued.py`) each stood a whole agent up to show one of these.

The clock stands at 2026-01-01T12:00:00Z, so a file can say an instant and mean it. What the
store needs beyond the case is five triples: which three graphs are public, and that the two
graph classes a case uses exist at all — the door asks for predictions and for the agent's own
graphs by `rdfs:subClassOf*`, and a zero-length path matches a class only where the class is
a term of the graph asked. A case classifies its roots graph as boot does, `orexis:DesireGraph`:
the road finds a root's shape by asking which graphs are the agent's, never by spelling the
graph's name. See knowledge/decisions/one-road-derives-every-want.md.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from orexis_agent_progression import clock
from orexis_agent_progression.ontology import ONTOLOGY_GRAPH, picks_graph
from orexis_agent_progression.store import Store, bindings

from orexis_agent_deliberation import pursuit
from orexis_agent_deliberation.desires import Desires
from orexis_agent_deliberation.wants import Wants

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
AGENT, ME = "keeper", "http://example.org/test#keeper"
WORLD, ACTIONS = "http://example.org/test#world", "http://example.org/test#actions"
EXPECTED = "http://example.org/test#expected"
CASES = sorted((Path(__file__).parent / "road").glob("*.trig"))


def stand_in(case: Path):
    """An agent standing on the case: the store the file describes, and the two collections."""
    st = Store()
    st.agent_id, st.agent_uri, st.graph = AGENT, ME, picks_graph(AGENT)
    st.update(f"""INSERT DATA {{ GRAPH <{ONTOLOGY_GRAPH}> {{
      <{ONTOLOGY_GRAPH}> a orexis:PublicGraph . <{WORLD}> a orexis:PublicGraph . <{ACTIONS}> a orexis:PublicGraph .
      orexis:PredictionGraph rdfs:subClassOf orexis:Graph . orexis:DesireGraph rdfs:subClassOf orexis:Graph . }} }}""")
    st.put_graph(WORLD, case.read_text(), dataset=True)
    desires, wants = Desires(st), Wants(st)
    wants.on_saved.append(lambda _: desires.rebuild())
    wants.on_deleted.append(lambda _: desires.rebuild())
    return SimpleNamespace(id=AGENT, me=SimpleNamespace(uri=ME), beliefs=st, desires=desires,
                           wants=wants, ask=lambda *a, **k: [], keeper=None)


Row = tuple[str, frozenset[str], datetime | None, str | None, frozenset[tuple[str, str, str]]]


def wants_in(st: Store, graph: str, wants: set[str] | None = None) -> set[Row]:
    """The wants a graph describes, each as (name, what it is about, the instant, the node its
    met-test targets, the met-test's constraint blocks as (path, constraint, value)) — the
    same reading of the `:expected` graph and of what the road wrote, so the two compare."""
    scope = f"GRAPH <{graph}>" if graph else "GRAPH ?g"
    rows = bindings(st.query_union(f"""SELECT ?w ?about ?at ?node ?path ?cp ?cv WHERE {{
      {scope} {{
        ?w orexis:about ?about .
        OPTIONAL {{ ?w orexis:holdsAt ?at }}
        OPTIONAL {{ ?w orexis:metWhen ?s .
                   OPTIONAL {{ ?s sh:targetNode ?node }}
                   OPTIONAL {{ ?s sh:property ?b . ?b sh:path ?path ; ?cp ?cv .
                              FILTER(?cp IN (sh:minInclusive, sh:maxInclusive,
                                             sh:minExclusive, sh:maxExclusive)) }} }} }} }}"""))
    by_want: dict = {}
    for r in rows:
        if wants is not None and r["w"] not in wants:
            continue
        w = by_want.setdefault(r["w"], {"about": set(), "at": r.get("at"), "node": r.get("node"), "blocks": set()})
        w["about"].add(r["about"])
        if r.get("path"):
            w["blocks"].add((r["path"], r["cp"], r["cv"]))
    return {(name, frozenset(w["about"]), datetime.fromisoformat(w["at"]) if w["at"] else None,
             w["node"], frozenset(w["blocks"])) for name, w in by_want.items()}


def expected_in(st: Store) -> set[Row]:
    return wants_in(st, EXPECTED)


def standing_under(agent, root: str) -> set[Row]:
    names = {w.uri for w in agent.wants.find_all_by_desire(root)}
    return wants_in(agent.beliefs, "", names)


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_the_road_leaves_standing_what_the_case_expects(case, monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    agent = stand_in(case)
    [root] = {d.uri for d in agent.desires.find_all()}    # a row per `about`, one desire
    pursuit.top_up(agent, root)
    assert standing_under(agent, root) == expected_in(agent.beliefs)


def test_every_case_is_read():
    """A glob that stopped matching would pass every case by running none."""
    assert len(CASES) >= 11, [c.name for c in CASES]
