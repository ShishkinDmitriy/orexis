"""The road, one case per file, held to a SNAPSHOT of the whole store it leaves behind.

**No world, no genesis, no agent.** Each `road/<case>.trig` is one case, whole — the world the
desire ranges over, the levers whose effects say which properties move together, the desire
with its met-test, what the instruments read now, what is foreseen and from when, and what
already stands. This file loads a case into a bare store, stands a stand-in agent on it — the
real `Desires` and `Wants` collections over that store, nothing else — runs `pursuit.top_up`,
and compares EVERY quad the store then holds with `road/<case>.nq`, the snapshot beside the
case. A case costs milliseconds; the four world files that covered the road end to end
(`tests/test_greenhouse.py`, `test_foreseen.py`, `test_one_road.py`, `test_pursued.py`) each
stood a whole agent up to show one of these.

THE WHOLE STORE, NOT A READING OF IT. The first cut of these cases carried an `:expected`
graph and compared five things per want — name, what it is about, the instant, the target
node, the constraint blocks — and a want writes nineteen quads: the holder's link, the label,
the provenance link, its graph's classification and owner, its period. Any of those could be
wrong with every case green, and the road could write into a graph it was handed to read and
nothing would say so. A snapshot of the store compared whole is exact — what the road left,
and nothing else, in every graph — so a change in the road's behaviour shows as a diff of the
snapshot, reviewed by eyes, and never as a check somebody forgot to widen. Regenerate with
`pytest packages/orexis-agent-deliberation/tests --update-snapshots`; a case without a
snapshot fails rather than passing on nothing.

Sorted N-Quads, one line per quad, blank nodes labelled canonically per graph and prefixed
with the graph's tail so two graphs' nodes do not share a spelling. The clock stands at
2026-01-01T12:00:00Z, so a file can say an instant and mean it, and a period the road writes
is the same on every run. What the store needs beyond the case is five triples: which three
graphs are public, and that the two graph classes a case uses exist at all — the door asks
for predictions and for the agent's own graphs by `rdfs:subClassOf*`, and a zero-length path
matches a class only where the class is a term of the graph asked. A case classifies its
roots graph as boot does, `orexis:DesireGraph`: the road finds a root's shape by asking which
graphs are the agent's, never by spelling the graph's name. See
knowledge/decisions/one-road-derives-every-want.md.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from rdflib import Graph
from rdflib.compare import to_canonical_graph

from orexis_agent_progression import clock
from orexis_agent_progression.ontology import ONTOLOGY_GRAPH, picks_graph
from orexis_agent_progression.store import Store

from orexis_agent_deliberation import pursuit
from orexis_agent_deliberation.desires import Desires
from orexis_agent_deliberation.wants import Wants

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
AGENT, ME = "keeper", "http://example.org/test#keeper"
WORLD, ACTIONS = "http://example.org/test#world", "http://example.org/test#actions"
ROAD = Path(__file__).parent / "road"
CASES = sorted(ROAD.glob("*.trig"))
UPDATE = "pytest packages/orexis-agent-deliberation/tests --update-snapshots"


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


def snapshot_of(st: Store) -> list[str]:
    """Every quad the store holds, as sorted N-Quads lines — the same text whether the store
    was just written or the snapshot was read back, so the two compare line by line."""
    lines = []
    for graph in st.graph_names():
        tail = re.sub(r"\W", "_", graph.rsplit("/", 1)[-1])
        canonical = to_canonical_graph(Graph().parse(data=st.dump_nt(graph), format="nt"))
        #  N-Triples from the serializer, not `n3()`: a rule text with a newline in it is one
        #  escaped line there and a triple-quoted block here. The canonical labels are stable
        #  but long where two nodes are alike (`cb` and a hash), so each graph's are renamed
        #  `b1..bn` in label order, prefixed with the graph's tail, outside the literals — the
        #  even segments between unescaped quotes.
        text = canonical.serialize(format="nt")
        labels = {label: f"{tail}_b{n}" for n, label in enumerate(sorted(set(re.findall(r"_:(\w+)", text))), 1)}
        for line in text.splitlines():
            if not line.strip():
                continue
            assert line.endswith(" ."), line
            parts = re.split(r'(?<!\\)"', line[:-2])
            parts[::2] = [re.sub(r"_:(\w+)", lambda m: "_:" + labels[m.group(1)], part) for part in parts[::2]]
            lines.append('"'.join(parts) + f" <{graph}> .")
    return sorted(lines)


def snapshot_path(case: Path) -> Path:
    return case.with_suffix(".nq")


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_the_road_leaves_the_store_as_the_snapshot_says(case, monkeypatch, request):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    agent = stand_in(case)
    [root] = {d.uri for d in agent.desires.find_all()}    # a row per `about`, one desire
    pursuit.top_up(agent, root)
    actual = snapshot_of(agent.beliefs)
    path = snapshot_path(case)
    if request.config.getoption("--update-snapshots"):
        path.write_text(f"# The whole store after the road ran on {case.name}, as sorted N-Quads.\n"
                        f"# Regenerated by `{UPDATE}` — review the diff; it is the claim.\n"
                        + "\n".join(actual) + "\n")
    assert path.exists(), f"{case.name} has no snapshot: run `{UPDATE}` and review {path.name}"
    expected = [line for line in path.read_text().splitlines() if line and not line.startswith("#")]
    left, missing = sorted(set(actual) - set(expected)), sorted(set(expected) - set(actual))
    assert not left and not missing, (
        f"{case.name}: the store the road left differs from {path.name}\n"
        + "".join(f"  the road left, unexpected:  {l}\n" for l in left)
        + "".join(f"  the snapshot says, missing: {l}\n" for l in missing)
        + f"  (if the road changed on purpose: `{UPDATE}`, then review the diff)")


def test_every_case_is_read_and_no_snapshot_is_orphaned():
    """A glob that stopped matching would pass every case by running none; a snapshot whose
    case was deleted or renamed would keep saying something nobody checks."""
    assert len(CASES) >= 11, [c.name for c in CASES]
    orphans = sorted(p.name for p in ROAD.glob("*.nq") if not p.with_suffix(".trig").exists())
    assert not orphans, f"snapshots without a case: {orphans}"
