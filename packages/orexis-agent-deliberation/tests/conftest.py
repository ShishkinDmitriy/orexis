"""The deliberation package's own test options, and the snapshot machinery its two case
tests share (`test_derive_wants.py`, `test_scope_actions.py`).

`--update-snapshots` rewrites every case's snapshot (`<function>/<case>.snapshot.trig`) from
what the function actually left in the store, instead of holding the store to it. Registered here, beside the
tests that read it, so it is recognised when these tests are named on the command line:

    pytest packages/orexis-agent-deliberation/tests --update-snapshots

A regenerated snapshot is reviewed by eyes before it is committed — the diff IS the claim
that the derivation's behaviour changed on purpose.
"""

from __future__ import annotations

import difflib
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
    #  AND WHAT ITS VOCABULARY SAYS, if it needs one to say anything. A writer that classifies
    #  a graph asks ONE `rdfs:subClassOf` step for every kind the row it writes is beneath — a
    #  real store has those because genesis materialises the closure into it, and a case has
    #  them because the case declares them. They used to be injected here, which meant a case
    #  did not say what it was loaded with and a reader of one could not tell what the
    #  function had been given: the sovereign's word for it was a hack, and it was.
    #
    #  THE CASE SAYS WHAT ITS GRAPHS ARE, in a catalogue it names — `:catalogue` — found by what
    #  it says of itself, never by its spelling: which graphs are public, which graph is the
    #  vocabulary. The stub adds only the axioms, into whichever graph the case types as the
    #  vocabulary's, and they say what every graph class the derivation asks by is beneath — with
    #  what the closure entails of them, as a volume's entailed graph carries it, since a
    #  writer over the engine asks one `rdfs:subClassOf` step for every kind a row bears; a case
    #  with no catalogue is refused, since a store that says nothing of its graphs has no
    #  public knowledge to read, and one typing no vocabulary graph the same, since the axioms
    #  would have nowhere to go. No name in a case is the kernel's: every graph is called what
    #  the case likes and found by what the catalogue says of it, the readings included.
    assert st.catalogue is not None, f"{case.name} names no graph that describes itself as the catalogue"
    (ontology,) = st.graphs_of(OREXIS + "OntologyGraph") or [None]
    assert ontology is not None, f"{case.name} types no graph as the vocabulary's"
    st.close_catalogue()      # a case's rows say one class each; every kind stands on them now, as on a volume's
    desires, wants = Desires(st), Wants(st)
    #  ENOUGH TO RUN A SEARCH, and no more. `Actions` and `Steps` take this store and no
    #  agent, so a case can have both; `desire_urgency` is the CHOIR, which a case has no
    #  members to ask — it answers None, and the planner then judges a compiled want the way
    #  the puzzle worlds are judged, binary from the store: unmet 1, met 0 (`planner._urgency_in`).
    #  A case whose goal is a shape therefore needs no capability loaded, and its whole
    #  objective is in the store, which is what makes a search snapshot-shaped at all.
    from orexis_agent_deliberation.actions import Actions
    from orexis_agent_deliberation.steps import Steps
    return SimpleNamespace(id=AGENT, me=SimpleNamespace(uri=ME, acts_for=None), beliefs=st, desires=desires,
                           wants=wants, ask=lambda *a, **k: [], keeper=None,
                           actions=Actions(st), steps=Steps(st), picks=picks_graph(AGENT),
                           desire_urgency=lambda *a, **k: None)


RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
DECIMAL = URIRef("http://www.w3.org/2001/XMLSchema#decimal")
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
    return dict(re.findall(r"^@prefix ([\w-]*): <([^>]*)> \.", case.read_text(), flags=re.M))


#  A block is one line holding its closing brace, or lines up to a line that is one — never
#  a one-line block that runs on to the next block's brace, which copied a catalogue twice.
BLOCK = re.compile(r"(?:^#[^\n]*\n)*^GRAPH (\S+) \{(?:[^\n]*\}[ \t]*\n|[ \t]*\n(?:.*?^\}\n)?)\n*", flags=re.S | re.M)


def segments_of(text: str) -> tuple[str, list[tuple[str, str]]]:
    """A case's text — or a snapshot's, which is a case's with changes in it — as its preamble,
    the header comment and the prefixes, and one segment per `GRAPH` block: the graph's IRI and
    the block's text with the comment lines above it, in the order written. What the writer
    copies verbatim, and the order it keeps."""
    prefixes = dict(re.findall(r"^@prefix ([\w-]*): <([^>]*)> \.", text, flags=re.M))
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
                #  A DECIMAL KEEPS ITS POINT. Turtle's bare forms are typed by their spelling —
                #  `1` is an integer and `1.0` a decimal — so a decimal whose value happens to
                #  be whole came back from the snapshot as an INTEGER and the comparison saw a
                #  quad that was never written. No case had one until a pass wrote `standsAt`
                #  and a plan wrote `takes`.
                if term.datatype == DECIMAL and "." not in str(term):
                    return f"{term}.0"
                return str(term)                  # Turtle's own short form
            text = term.n3()
            #  THE DATATYPE, NEVER THE CONTENT. This asked whether `^^<ns` appeared ANYWHERE
            #  in the literal's text and replaced it there — so a literal whose content
            #  mentions a datatype IRI had the mention rewritten instead of its own datatype,
            #  and the `[:-1]` that was meant to drop the datatype IRI's `>` chopped the
            #  literal's closing quote instead, leaving a snapshot no parser would read. The
            #  trace's compiled select is exactly such a literal: a SELECT carrying
            #  `"10"^^<…XMLSchema#integer>` inside it. Abbreviate what `term.datatype` says
            #  and only where the text ends with it.
            tail = f"^^<{term.datatype}>"
            if term.datatype is not None and text.endswith(tail):
                for prefix, ns in longest:
                    local = str(term.datatype)[len(ns):]
                    if str(term.datatype).startswith(ns) and re.fullmatch(r"[\w.\-]*", local):
                        return text[:-len(tail)] + f"^^{prefix}:{local}"
            return text
        return f"_:{term}"

    def render(iri: str, graph: Graph) -> str:
        """One graph as a TriG block: ONE LINE PER STATEMENT, sorted, nested nodes inlined.

        FLAT AT THE TOP, because Turtle's `;` and `,` make every line depend on the one after
        it — adding a statement flips its neighbour's `;` to `.`, so a one-statement change is a
        three-line diff and no diff over grouped Turtle can ever be minimal. Written one to a
        line, adding a statement adds a line.

        AND NESTED WHERE NESTING IS THE MEANING. A blank node used once is inlined `[ … ]` and
        an RDF list is `( … )`, as they were: a shape is a TREE of blank nodes, and flattening
        one gives `_:b11 rdf:rest _:b1` sorted lexically so `_:b10` precedes `_:b2` — every
        quad on its own line and the shape unreadable. One quad a line is worth having where a
        subject has a name a reader can hold, and worth nothing where it does not.
        """
        as_object: dict = {}
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
                body = " ; ".join(f"{name(p_)} {term(o_, depth + 1)}" for p_, o_ in sorted(
                    pairs, key=lambda po: (name(po[0]), term(po[1], depth + 1))))
                return f"[ {body} ]"
            return name(t)

        lines = [f"GRAPH {name(URIRef(iri))} {{"]
        lines += sorted(f"  {name(s_)} {name(p_)} {term(o_, 0)} ."
                        for s_, p_, o_ in graph
                        if not (isinstance(s_, BNode) and s_ in inlined))
        lines.append("}\n")
        return "\n".join(lines)
    return render


def trig_of(base: str, before: dict[str, Graph], after: dict[str, Graph], header: str) -> str:
    """The store after a function ran, as the base text — the case's, or the previous
    snapshot's — with the function's changes in it."""
    preamble, segments = segments_of(base)
    render = renderer(dict(re.findall(r"^@prefix ([\w-]*): <([^>]*)> \.", base, flags=re.M)))
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
            #  `rstrip` because `render` ends its block with a newline and `spacing` IS the
            #  newlines the author left after it — added raw, every re-rendered graph gained a
            #  blank line the case did not have, and every diff carried it.
            out.append(f"{comments}# CHANGED, re-rendered:\n"
                       + render(iri, after[iri]).rstrip("\n") + spacing)
    written = [iri for iri in sorted(after) if iri not in {iri for iri, _ in segments}]
    if written:
        out.append("\n# --- WRITTEN (the first snapshot also holds the loader's own vocabulary stub) ---\n\n")
        out.append("\n".join(render(iri, after[iri]) for iri in written))
    return "".join(out)


def snapshot_of(st: Store) -> dict[str, Graph]:
    return canonical_graphs({g: st.dump_nt(g) for g in st.graph_names()})


def text_read(text: str) -> dict[str, Graph]:
    """One TriG document read through the same door a case is loaded by — the store's own
    engine — so what is compared is what that engine makes of the text, on both sides."""
    st = Store()
    st.put_graph(WORLD, text, dataset=True)
    return canonical_graphs({g: st.dump_nt(g) for g in st.graph_names()})


def snapshot_read(path: Path) -> dict[str, Graph]:
    """A snapshot file, read the same way."""
    return text_read(path.read_text())


def without_comments(text: str) -> str:
    """The lines that say something, for a patch to be about.

    A case is mostly prose — the header this machinery writes, and the argument the case makes
    for itself — and none of it is what a function did. Stripped from both sides, a patch
    carries data and nothing else; the comparison is over quads either way, so a comment is
    never what a case is held to.
    """
    return "".join(l for l in text.splitlines(True) if not l.lstrip().startswith("#"))


def patch_of(case: str, expected: str) -> str:
    """The unified diff that turns one into the other, comments left out of both.

    Stored INSTEAD of the whole expected store, for a directory where the diff is the thing a
    reader wants: `<case>.trig` and `<case>.patch`, and what the function must leave is what
    applying one to the other gives. The other directories keep their snapshots — opening a
    file and reading the store is worth having where a case is large, and this is the
    experiment that says whether it is worth having everywhere.
    """
    return "".join(difflib.unified_diff(
        without_comments(case).splitlines(True), without_comments(expected).splitlines(True),
        "case", "expected", n=3))


def patched(case: str, patch: str) -> str:
    """`case` with `patch` applied — a strict applier, by line number and nothing else.

    No fuzz and no context search, deliberately: this only ever applies a patch this module
    wrote, against the case it was written from, so a hunk that does not land where it says it
    lands is a stale patch rather than something to guess at. `patch(1)` and `git apply` would
    both do it; neither is a dependency worth taking for thirty lines that cannot drift.
    """
    lines = without_comments(case).splitlines(True)
    out, at, started = [], 0, False
    for line in patch.splitlines(True):
        head = re.match(r"^@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@", line)
        if head:
            started = True
            start = int(head.group(1)) - 1
            out += lines[at:start]
            at = start
            continue
        if not started:                      # the `---`/`+++` file names
            continue
        if line.startswith("+"):
            out.append(line[1:])
        elif line.startswith(("-", " ")):
            assert lines[at] == line[1:], f"stale patch at line {at + 1}: {lines[at]!r}"
            if line.startswith(" "):
                out.append(lines[at])
            at += 1
    return "".join(out + lines[at:])


def held_to_patch(case: Path, request, function: str, after: dict) -> None:
    """Hold what `function` left to `<case>.patch` beside it — the case plus the patch
    IS the expected store, and the comparison is over every quad, as it is for a snapshot.
    """
    path = case.with_suffix(".patch")
    rendered = trig_of(case.read_text(), {}, after, f"# what `{function}` leaves on {case.name}")
    if request.config.getoption("--update-snapshots"):
        path.write_text(patch_of(case.read_text(), rendered))
    assert path.exists(), f"{case.name} has no patch: run `{UPDATE}` and review {path.name}"
    expected = quad_lines(text_read(patched(case.read_text(), path.read_text())))
    lines = quad_lines(after)
    left, missing = sorted(lines - expected), sorted(expected - lines)
    if left or missing:
        #  WHAT WAS ACTUALLY LEFT, on a mismatch and never otherwise. The quads above say what
        #  DIFFERS and this says what the store IS, which is what somebody fixing it wants to
        #  diff against. A green run leaves nothing behind, and `.gitignore` refuses the file
        #  either way.
        case.with_suffix(".actual.trig").write_text(rendered)
    assert not left and not missing, (
        f"{case.name}: the store `{function}` left differs from case + {path.name}\n"
        + "".join(f"  left, unexpected:           {l}\n" for l in left)
        + "".join(f"  the patch says, missing:    {l}\n" for l in missing)
        + f"  what was left is in {case.stem}.actual.trig: `diff {case.name} {case.stem}.actual.trig`;\n"
        + f"  if the change is on purpose: `{UPDATE}`, then review the patch")


def held_worlds_to(case: Path, request, forks: list, knows: dict) -> None:
    """Hold the worlds a pass FORKED to `<case>.worlds.trig` beside it, in the order they were
    made — one `GRAPH` block per world, named as the imaginarium named it.

    A second kind of snapshot, and it needs one because a forked world is not in the store
    afterwards: a node's graph is dropped once it is expanded and again when the pass ends, to
    be re-made from the nearest kept graph when a rule next runs against it. So these are
    caught as they are made rather than read off the store at the end, and what is held is the
    SEQUENCE — which is the thing worth holding, since an iteration of the search is exactly
    "one node off the open list, one world per step its world admits".

    Each block holds that node's OWN readings and not a copy of the world: what the step added
    and what it retracted, against a parent the block names. That is the imaginarium's whole
    arrangement (`cone.py`), and the reason it is worth seeing.
    """
    path = case.with_suffix(".worlds.trig")
    base = case.read_text()
    render = renderer(dict(re.findall(r"^@prefix ([\w-]*): <([^>]*)> \.", base, flags=re.M)))
    graphs = canonical_graphs({to: nt for _, to, nt in forks})
    out = [f"# Every world `{case.name}` forked, in the order the search made them — {len(forks)} of them.\n"
           f"# Regenerated by `{UPDATE}`; review the diff, it is the claim.\n\n"
           + segments_of(base)[0]]
    for n, (frm, to, _) in enumerate(forks):
        out.append(f"#  {n + 1}. from {frm.rsplit('/', 1)[-1]}\n" + render(to, graphs[to]))
    #  AND WHAT THE PASS KNOWS ABOUT THEM, which is the half that makes the rest usable: a
    #  world's parent, what the path spent, what the want read there and how far it still is.
    #  With this a reader coming to the store cold can ask for the frontier and take the next
    #  iteration; without it the worlds are a heap of graphs with no edges between them.
    for iri, graph in sorted(knows.items()):
        caption = ("#  The plan it decided on." if "/plan/" in iri
                   else "#  What the pass knows about every world it made.")
        out.append(caption + "\n" + render(iri, graph))
    text = "\n".join(out)
    if request.config.getoption("--update-snapshots"):
        path.write_text(text)
    assert path.exists(), f"{case.name} has no worlds file: run `{UPDATE}` and review {path.name}"
    assert text == path.read_text(), (
        f"{case.name}: the worlds this pass forked differ from {path.name}\n"
        f"  if the change is on purpose: `{UPDATE}`, then review the diff")


def orphans_in(directory: Path, suffix: str = ".patch") -> list[str]:
    """Files whose case was deleted or renamed — one that keeps saying something nobody checks."""
    return sorted(p.name for p in directory.glob("*" + suffix)
                  if not (directory / (p.name[:-len(suffix)] + ".trig")).exists())


@pytest.fixture
def snapshots():
    """The machinery above, for a test file in this directory — a sibling module is not
    importable here (only the root `tests/` is on the path), a conftest's names are."""
    return sys.modules[__name__]



def pytest_addoption(parser):
    parser.addoption("--update-snapshots", action="store_true", default=False,
                     help="rewrite the cases' snapshots from what each function left, then review the diff")
