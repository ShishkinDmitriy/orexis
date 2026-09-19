"""The road as two functions over the store, one case per file, each function held to a
SNAPSHOT of the whole store it leaves behind.

**No world, no genesis, no agent.** Each `road/<case>.trig` is one case, whole — the world the
desire ranges over, the levers whose effects say which properties move together, the desire
with its met-test, what the instruments read now, what is foreseen and from when, and what
already stands. This file loads a case into a bare store, stands a stand-in agent on it — the
real `Desires` and `Wants` collections over that store, nothing else — and runs the road's two
functions in turn (judge-desires-then-derive-wants):

- `judge_desires`: every desire judged at the present and at each foreseen instant, the
  judgments written to the store. Held to `road/<case>.judge_desires.trig`.
- `derive_wants`: the wants those judgments imply, minted under their desires, reading the
  store and nothing else. Held to `road/<case>.derive_wants.trig`, which is written against
  the judged state, so its diff against the first snapshot is the derivation alone.

A case costs milliseconds; the four world files that covered the road end to end
(`tests/test_greenhouse.py`, `test_foreseen.py`, `test_one_road.py`, `test_pursued.py`) each
stood a whole agent up to show one of these.

THE WHOLE STORE, NOT A READING OF IT. The first cut of these cases carried an `:expected`
graph and compared five things per want — name, what it is about, the instant, the target
node, the constraint blocks — and a want writes nineteen quads: the holder's link, the label,
the provenance link, its graph's classification and owner, its period. Any of those could be
wrong with every case green, and the road could write into a graph it was handed to read and
nothing would say so. A snapshot of the store compared whole is exact — what the function left,
and nothing else, in every graph — so a change in behaviour shows as a diff of the snapshot,
reviewed by eyes, and never as a check somebody forgot to widen. Regenerate with
`pytest packages/orexis-agent-deliberation/tests --update-snapshots`; a case without a
snapshot fails rather than passing on nothing.

TriG, IN THE CASE'S OWN ORDER, so `diff` of the input against the snapshot is the change: a
graph the function left as it found it is copied from the input verbatim, comments and all;
one it changed is re-rendered in its place, its comment kept; one it dropped leaves a note;
and what it wrote comes after, under a marker. The rendering is a small serializer of this
file's that orders everything — subjects, predicates, objects — and inlines a blank node used
once, so a shape reads as the shape it is and the same store writes the same text on every
run. Compared STRUCTURALLY: the snapshot is parsed back and both sides are canonicalised to
the same quad lines, so a label or a layout is never what fails a case. The clock stands at
2026-01-01T12:00:00Z, so a file can say an instant and mean it, and a period the road writes
is the same on every run. What the store needs beyond the case is seven triples: which three
graphs are public, and that the graph classes the road asks by exist at all — the door asks
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
from rdflib import BNode, Graph, Literal, URIRef
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
CASES = sorted(p for p in ROAD.glob("*.trig") if "." not in p.stem)    # a snapshot is <case>.<function>.trig
UPDATE = "pytest packages/orexis-agent-deliberation/tests --update-snapshots"


def stand_in(case: Path, text: str | None = None):
    """An agent standing on the case — or on `text`, a snapshot of one: the store the file
    describes, and the two collections."""
    st = Store()
    st.agent_id, st.agent_uri, st.graph = AGENT, ME, picks_graph(AGENT)
    st.update(f"""INSERT DATA {{ GRAPH <{ONTOLOGY_GRAPH}> {{
      <{ONTOLOGY_GRAPH}> a orexis:PublicGraph . <{WORLD}> a orexis:PublicGraph . <{ACTIONS}> a orexis:PublicGraph .
      orexis:PredictionGraph rdfs:subClassOf orexis:Graph . orexis:DesireGraph rdfs:subClassOf orexis:Graph .
      deliberation:JudgmentGraph rdfs:subClassOf orexis:WorkingGraph . orexis:WorkingGraph rdfs:subClassOf orexis:Graph . }} }}""")
    st.put_graph(WORLD, text if text is not None else case.read_text(), dataset=True)
    desires, wants = Desires(st), Wants(st)
    wants.on_saved.append(lambda _: desires.rebuild())
    wants.on_deleted.append(lambda _: desires.rebuild())
    return SimpleNamespace(id=AGENT, me=SimpleNamespace(uri=ME), beliefs=st, desires=desires,
                           wants=wants, ask=lambda *a, **k: [], keeper=None)


RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
BARE = {URIRef(f"http://www.w3.org/2001/XMLSchema#{t}") for t in ("integer", "decimal", "boolean")}


def canonical_graphs(graphs: dict[str, str]) -> dict[str, Graph]:
    """Each graph — IRI to N-Triples text — canonicalised, its blank nodes renamed `b1..bn` in
    the order of their canonical labels: the same graph gives the same nodes on every run,
    whether it came from the store or was read back from a snapshot."""
    out = {}
    for iri, text in graphs.items():
        canonical = to_canonical_graph(Graph().parse(data=text, format="nt"))
        labels = {node: BNode(f"b{n}") for n, node in enumerate(
            sorted({t for triple in canonical for t in triple if isinstance(t, BNode)}), 1)}
        graph = Graph()
        for s_, p_, o_ in canonical:
            graph.add((labels.get(s_, s_), p_, labels.get(o_, o_)))
        out[iri] = graph
    return out


def quad_lines(graphs: dict[str, Graph]) -> set[str]:
    """One line per quad, the blank nodes' labels prefixed with the graph's tail — what two
    snapshots are compared as, and what a mismatch is reported in."""
    lines = set()
    for iri, graph in graphs.items():
        tail = re.sub(r"\W", "_", iri.rsplit("/", 1)[-1])
        for s_, p_, o_ in graph:
            term = lambda t: f"_:{tail}_{t}" if isinstance(t, BNode) else t.n3()
            lines.add(f"{term(s_)} {term(p_)} {term(o_)} <{iri}> .")
    return lines


def prefixes_of(case: Path) -> dict[str, str]:
    """The case's own `@prefix` lines — the snapshot speaks the names the case does."""
    return dict(re.findall(r"^@prefix (\w*): <([^>]*)> \.", case.read_text(), flags=re.M))


BLOCK = re.compile(r"(?:^#[^\n]*\n)*^GRAPH (\S+) \{[ \t]*\}?\n?(?:.*?^\}\n)?\n*", flags=re.S | re.M)


def segments_of(text: str) -> tuple[str, list[tuple[str, str]]]:
    """A case's text — or a snapshot's, which is a case's with changes in it — as its preamble,
    the header comment and the prefixes, and one segment per `GRAPH` block: the graph's IRI and
    the block's text with the comment lines above it, in the order written. What the writer
    copies verbatim, and the order it keeps."""
    prefixes = dict(re.findall(r"^@prefix (\w*): <([^>]*)> \.", text, flags=re.M))
    blocks = [(m.group(1), m.group(0)) for m in BLOCK.finditer(text)]
    assert blocks, case.name
    preamble = text[:text.index(blocks[0][1])]

    def iri(name: str) -> str:
        if name.startswith("<"):
            return name[1:-1]
        prefix, local = name.split(":", 1)
        return prefixes[prefix] + local
    return preamble, [(iri(name), block) for name, block in blocks]


def renderer(prefixes: dict[str, str]):
    """A `render(iri, graph)` for one graph as a TriG block: subjects in rendered order (IRIs,
    then the blank nodes nothing inlined), predicates and objects sorted, `a` for the type,
    bare numbers where Turtle has them, a blank node used once inlined where it is used, an
    RDF list as `( … )`. rdflib's own TriG writer is held to no order, and a snapshot that
    moved when nothing changed would hide the change that mattered."""
    longest = sorted(prefixes.items(), key=lambda kv: -len(kv[1]))

    def name(term) -> str:
        if isinstance(term, URIRef):
            if term == URIRef(RDF + "type"):
                return "a"
            for prefix, ns in longest:
                if term.startswith(ns) and re.fullmatch(r"[\w.\-]*", term[len(ns):]) and not term.endswith("."):
                    return f"{prefix}:{term[len(ns):]}"
            return f"<{term}>"
        if isinstance(term, Literal):
            if term.datatype in BARE and re.fullmatch(r"[-+]?\d+(\.\d+)?|true|false", str(term)):
                return str(term)                  # Turtle's own short form
            text = term.n3()
            for prefix, ns in longest:
                if f"^^<{ns}" in text:
                    return text.replace(f"^^<{ns}", f"^^{prefix}:")[:-1]
            return text
        return f"_:{term}"

    def render(iri: str, graph: Graph) -> str:
        as_object = {}
        for _, _, o_ in graph:
            if isinstance(o_, BNode):
                as_object[o_] = as_object.get(o_, 0) + 1
        inlined = {b for b, n in as_object.items() if n == 1}

        def term(t, depth: int) -> str:
            if isinstance(t, BNode) and t in inlined:
                pairs = list(graph.predicate_objects(t))
                if {p_ for p_, _ in pairs} == {URIRef(RDF + "first"), URIRef(RDF + "rest")}:
                    items, node = [], t
                    while node != URIRef(RDF + "nil"):
                        items.append(term(graph.value(node, URIRef(RDF + "first")), depth))
                        node = graph.value(node, URIRef(RDF + "rest"))
                    return "( " + " ".join(items) + " )"
                pad = "      " + "    " * (depth + 1)
                body = f" ;\n{pad}".join(f"{name(p_)} {term(o_, depth + 1)}" for p_, o_ in sorted(
                    pairs, key=lambda po: (name(po[0]), term(po[1], depth + 1))))
                return f"[ {body} ]"
            return name(t)

        lines = [f"GRAPH {name(URIRef(iri))} {{"]
        subjects = sorted({s_ for s_, _, _ in graph if not (isinstance(s_, BNode) and s_ in inlined)},
                          key=lambda t: (isinstance(t, BNode), name(t)))
        for s_ in subjects:
            pairs = sorted(graph.predicate_objects(s_), key=lambda po: (name(po[0]), term(po[1], 0)))
            body = " ;\n      ".join(f"{name(p_)} {term(o_, 0)}" for p_, o_ in pairs)
            lines.append(f"  {name(s_)} {body} .")
        lines.append("}\n")
        return "\n".join(lines)
    return render


def trig_of(base: str, before: dict[str, Graph], after: dict[str, Graph], header: str) -> str:
    """The store after a function ran, as the base text — the case's, or the previous
    snapshot's — with the function's changes in it."""
    preamble, segments = segments_of(base)
    render = renderer(dict(re.findall(r"^@prefix (\w*): <([^>]*)> \.", base, flags=re.M)))
    same = lambda iri: quad_lines({iri: before[iri]}) == quad_lines({iri: after[iri]})
    out = [header + "\n" + preamble]
    for iri, block in segments:
        comments = "".join(re.findall(r"^#[^\n]*\n", block, flags=re.M))
        graph_name = re.search(r"^GRAPH (\S+)", block, flags=re.M).group(1)
        spacing = block[len(block.rstrip("\n")):]          # the blank lines the author left after it
        if iri not in after:
            out.append(f"{comments}# DROPPED: {graph_name}\n{spacing}")
        elif iri in before and same(iri):
            out.append(block)
        else:
            out.append(f"{comments}# CHANGED, re-rendered:\n" + render(iri, after[iri]) + spacing)
    written = [iri for iri in sorted(after) if iri not in {iri for iri, _ in segments}]
    if written:
        out.append("\n# --- WRITTEN (the first snapshot also holds the loader's own vocabulary stub) ---\n\n")
        out.append("\n".join(render(iri, after[iri]) for iri in written))
    return "".join(out)


def snapshot_of(st: Store) -> dict[str, Graph]:
    return canonical_graphs({g: st.dump_nt(g) for g in st.graph_names()})


def snapshot_read(path: Path) -> dict[str, Graph]:
    """The snapshot read back through the same door a case is loaded by — the store's own
    engine — so what is compared is what that engine makes of the text, on both sides."""
    st = Store()
    st.put_graph(WORLD, path.read_text(), dataset=True)
    return canonical_graphs({g: st.dump_nt(g) for g in st.graph_names()})


def held_to(case: Path, request, function: str, base: str, before: dict, after: dict) -> str:
    """Hold what `function` left to `road/<case>.<function>.trig`, writing it from `base` under
    `--update-snapshots`; on a mismatch, what was actually left goes to `<case>.<function>.actual.trig`
    for `diff`. Returns the snapshot's text, the base the next function's snapshot is written from."""
    path = ROAD / f"{case.stem}.{function}.trig"
    header = (f"# The whole store after `{function}` ran on {case.name}, in the input's own order:\n"
              f"# `diff` of the previous file against this one is what `{function}` did. Regenerated by\n"
              f"# `{UPDATE}` — review the diff; it is the claim.")
    text = trig_of(base, before, after, header)
    if request.config.getoption("--update-snapshots"):
        path.write_text(text)
    assert path.exists(), f"{case.name} has no snapshot for {function}: run `{UPDATE}` and review {path.name}"
    lines, expected = quad_lines(after), quad_lines(snapshot_read(path))
    left, missing = sorted(lines - expected), sorted(expected - lines)
    if left or missing:
        received = ROAD / f"{case.stem}.{function}.actual.trig"
        received.write_text(trig_of(base, before, after, f"# What `{function}` actually left on {case.name}."))
    assert not left and not missing, (
        f"{case.name}: the store `{function}` left differs from {path.name}\n"
        + "".join(f"  left, unexpected:           {l}\n" for l in left)
        + "".join(f"  the snapshot says, missing: {l}\n" for l in missing)
        + f"  what was left is in {received.name}: `diff {path.name} {received.name}`;\n"
        + f"  if the change is on purpose: `{UPDATE}`, then review the diff")
    return path.read_text() if path.exists() else text


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_judge_desires_leaves_the_store_as_the_snapshot_says(case, monkeypatch, request):
    monkeypatch.setattr(clock, "now", lambda: NOW)
    agent = stand_in(case)
    before = snapshot_of(agent.beliefs)
    pursuit.judge_desires(agent)
    held_to(case, request, "judge_desires", case.read_text(), before, snapshot_of(agent.beliefs))


@pytest.mark.parametrize("case", CASES, ids=[c.stem for c in CASES])
def test_derive_wants_leaves_the_store_as_the_snapshot_says(case, monkeypatch, request):
    """Run after `judge_desires` in the same store, and written against the judged state, so
    the diff of the two snapshots is the derivation alone — and reading the judged snapshot
    back into a bare store and deriving from THAT leaves the same store, which is the
    contract: `derive_wants` reads the store and nothing in hand."""
    monkeypatch.setattr(clock, "now", lambda: NOW)
    agent = stand_in(case)
    loaded = snapshot_of(agent.beliefs)
    pursuit.judge_desires(agent)
    judged = snapshot_of(agent.beliefs)
    judged_text = trig_of(case.read_text(), loaded, judged, "")
    pursuit.derive_wants(agent)
    derived = snapshot_of(agent.beliefs)
    held_to(case, request, "derive_wants", judged_text, judged, derived)
    #  FROM THE STORE ALONE: the judged snapshot read back, and derived from with nothing in hand.
    other = stand_in(case, text=judged_text)
    pursuit.derive_wants(other)
    assert quad_lines(snapshot_of(other.beliefs)) == quad_lines(derived), \
        "deriving from the judged store read back differs from deriving in the same store"


def test_every_case_is_read_and_no_snapshot_is_orphaned():
    """A glob that stopped matching would pass every case by running none; a snapshot whose
    case was deleted or renamed would keep saying something nobody checks."""
    assert len(CASES) >= 11, [c.name for c in CASES]
    orphans = sorted(p.name for p in ROAD.glob("*.*.trig")
                     if not p.name.endswith(".actual.trig") and not (ROAD / (p.stem.split(".")[0] + ".trig")).exists())
    assert not orphans, f"snapshots without a case: {orphans}"
