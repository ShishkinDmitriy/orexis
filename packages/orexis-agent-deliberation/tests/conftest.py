"""The deliberation package's own test options, and the snapshot machinery its two road
tests share (`test_judge_desires.py`, `test_derive_wants.py`).

`--update-snapshots` rewrites every road case's snapshot (`road/<case>.nq`) from what the road
actually left in the store, instead of holding the store to it. Registered here, beside the
tests that read it, so it is recognised when these tests are named on the command line:

    pytest packages/orexis-agent-deliberation/tests --update-snapshots

A regenerated snapshot is reviewed by eyes before it is committed — the diff IS the claim
that the road's behaviour changed on purpose.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import sys
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import to_canonical_graph

from orexis_agent_progression import clock
from orexis_agent_progression.ontology import OREXIS, picks_graph
from orexis_agent_progression.store import Store

from orexis_agent_deliberation import pursuit
from orexis_agent_deliberation.desires import Desires
from orexis_agent_deliberation.wants import Wants

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
AGENT, ME = "keeper", "http://example.org/test#keeper"
WORLD, ACTIONS = "http://example.org/test#world", "http://example.org/test#actions"
UPDATE = "pytest packages/orexis-agent-deliberation/tests --update-snapshots"


def cases_in(directory: Path) -> list[Path]:
    """The cases of one directory — a snapshot is `<case>.snapshot.trig`, an actual `<case>.actual.trig`."""
    return sorted(p for p in directory.glob("*.trig") if "." not in p.stem)


def stand_in(case: Path, text: str | None = None):
    """An agent standing on the case — or on `text`, a snapshot of one: the store the file
    describes, and the two collections."""
    st = Store()
    st.put_graph(WORLD, text if text is not None else case.read_text(), dataset=True)
    st.agent_id, st.agent_uri, st.graph = AGENT, ME, picks_graph(AGENT)
    #  THE CASE SAYS WHAT ITS GRAPHS ARE, in a catalogue it names — `:catalogue` — found by what
    #  it says of itself, never by its spelling: which graphs are public, which graph is the
    #  vocabulary. The stub adds only the axioms, into whichever graph the case types as the
    #  vocabulary's, and they say what every graph class the road asks by is beneath — with
    #  what the closure entails of them, as a volume's entailed graph carries it, since a
    #  writer over the engine asks one `rdfs:subClassOf` step for every kind a row bears; a case
    #  with no catalogue is refused, since a store that says nothing of its graphs has no
    #  public knowledge to read, and one typing no vocabulary graph the same, since the axioms
    #  would have nowhere to go. No name in a case is the kernel's: every graph is called what
    #  the case likes and found by what the catalogue says of it, the readings included.
    assert st.catalogue is not None, f"{case.name} names no graph that describes itself as the catalogue"
    (ontology,) = st.graphs_of(OREXIS + "OntologyGraph") or [None]
    assert ontology is not None, f"{case.name} types no graph as the vocabulary's"
    st.update(f"""INSERT DATA {{ GRAPH <{ontology}> {{
        orexis:PublicGraph rdfs:subClassOf orexis:Graph . orexis:OntologyGraph rdfs:subClassOf orexis:PublicGraph .
        orexis:BeliefGraph rdfs:subClassOf orexis:Graph . orexis:StateGraph rdfs:subClassOf orexis:BeliefGraph .
        orexis:RecordGraph rdfs:subClassOf orexis:Graph .
        orexis:CatalogueGraph rdfs:subClassOf orexis:Graph . orexis:WorkingGraph rdfs:subClassOf orexis:Graph .
        orexis:PredictionGraph rdfs:subClassOf orexis:Graph . orexis:DesireGraph rdfs:subClassOf orexis:Graph .
        orexis:WantGraph rdfs:subClassOf orexis:Graph . deliberation:PursuedGraph rdfs:subClassOf orexis:WantGraph .
        deliberation:ScopeGraph rdfs:subClassOf orexis:WorkingGraph .
        orexis:OntologyGraph rdfs:subClassOf orexis:Graph . orexis:StateGraph rdfs:subClassOf orexis:Graph .
        deliberation:PursuedGraph rdfs:subClassOf orexis:Graph .
        deliberation:ScopeGraph rdfs:subClassOf orexis:Graph . }} }}""")
    st.close_catalogue()      # a case's rows say one class each; every kind stands on them now, as on a volume's
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


#  A block is one line holding its closing brace, or lines up to a line that is one — never
#  a one-line block that runs on to the next block's brace, which copied a catalogue twice.
BLOCK = re.compile(r"(?:^#[^\n]*\n)*^GRAPH (\S+) \{(?:[^\n]*\}[ \t]*\n|[ \t]*\n(?:.*?^\}\n)?)\n*", flags=re.S | re.M)


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


def held_to(case: Path, request, function: str, before: dict, after: dict) -> None:
    """Hold what `function` left on `case` to `<case>.snapshot.trig` beside it, writing it from
    the case's text under `--update-snapshots`; on a mismatch, what was actually left goes to
    `<case>.actual.trig` for `diff`."""
    path = case.with_suffix(".snapshot.trig")
    base = case.read_text()
    header = (f"# The whole store after `{function}` ran on {case.name}, in the case's own order:\n"
              f"# `diff {case.name} {path.name}` is what `{function}` did. Regenerated by\n"
              f"# `{UPDATE}` — review the diff; it is the claim.")
    text = trig_of(base, before, after, header)
    if request.config.getoption("--update-snapshots"):
        path.write_text(text)
    assert path.exists(), f"{case.name} has no snapshot: run `{UPDATE}` and review {path.name}"
    lines, expected = quad_lines(after), quad_lines(snapshot_read(path))
    left, missing = sorted(lines - expected), sorted(expected - lines)
    if left or missing:
        received = case.with_suffix(".actual.trig")
        received.write_text(trig_of(base, before, after, f"# What `{function}` actually left on {case.name}."))
    assert not left and not missing, (
        f"{case.name}: the store `{function}` left differs from {path.name}\n"
        + "".join(f"  left, unexpected:           {l}\n" for l in left)
        + "".join(f"  the snapshot says, missing: {l}\n" for l in missing)
        + f"  what was left is in {received.name}: `diff {path.name} {received.name}`;\n"
        + f"  if the change is on purpose: `{UPDATE}`, then review the diff")


def orphans_in(directory: Path) -> list[str]:
    """Snapshots whose case was deleted or renamed — a file that keeps saying something nobody checks."""
    return sorted(p.name for p in directory.glob("*.snapshot.trig")
                  if not (directory / (p.stem.split(".")[0] + ".trig")).exists())


@pytest.fixture
def snapshots():
    """The machinery above, for a test file in this directory — a sibling module is not
    importable here (only the root `tests/` is on the path), a conftest's names are."""
    return sys.modules[__name__]



def pytest_addoption(parser):
    parser.addoption("--update-snapshots", action="store_true", default=False,
                     help="rewrite the road cases' snapshots from what the road left, then review the diff")
