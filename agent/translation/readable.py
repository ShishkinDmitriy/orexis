"""`readable`: what a chat may read of the agent — the graphs of every kind the chat `speech:reads`, copied into one
graph for the model's queries — and the two tools that read it, `vocabulary` and `query`
(knowledge/domain/speech/chat.md, knowledge/decisions/the-model-queries-what-its-chat-may-read.md).

**THE CHAT SAYS WHAT IT READS, AND THE MODEL NEVER CHOOSES A GRAPH.** A chat stating no kind reads nothing here, and
its model has the askables alone. One stating kinds — a sovereign's chat every graph, a broker's the market's — is
read as the graphs of those kinds in every store the agent holds, COPIED on the runtime's thread into one default
graph, so a query runs over what the chat admits and nothing else, whatever the model writes, and a slow one stalls
the model's thread and never a pass.

**A QUERY IS READ, AND REFUSED BEFORE IT RUNS WHERE IT COULD DO ANYTHING BUT READ.** It is parsed with the store's
prefixes declared; anything but a SELECT or an ASK, and a `GRAPH`, `SERVICE` or `FROM` anywhere in it, is refused
with the reason, as is a text the parser will not take, so the model may write it again. Its rows are capped at
`ROWS`.
"""

from __future__ import annotations

import io
import json

import pyoxigraph as ox
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue

from agent.ontology import CLOSURE_GRAPH, OREXIS, local_of
from agent.store import NAMESPACES, bindings, graphs_of

#  HOW MANY ROWS A QUERY HANDS THE MODEL: past these it is told how many there were, and asks again more narrowly.
ROWS = 50
ONTOLOGY = OREXIS + "OntologyGraph"
VOCABULARY, QUERY = "vocabulary", "query"
_HEADER = "".join(f"PREFIX {p}: <{ns}>\n" for p, ns in NAMESPACES.items())
#  WHAT A QUERY MAY NOT HOLD: a graph of its own choosing, a service elsewhere, a dataset named.
_REFUSED = {"GraphGraphPattern": "a GRAPH clause", "ServiceGraphPattern": "a SERVICE clause", "datasetClause": "a FROM"}
_KINDS = ("SelectQuery", "AskQuery")


class Readable:
    """What one chat may read: the graphs of its kinds, copied, and each vocabulary among them by its prefix — all
    read on the runtime's thread when it is made, and only the copy afterwards."""

    def __init__(self, stores, kinds):
        self.store = ox.Store()
        self.vocabularies: dict[str, str] = {}
        for store in {id(s): s for s in stores if s is not None}.values():
            ontologies = set(graphs_of(store, ONTOLOGY)) - {CLOSURE_GRAPH}      # derived, and no vocabulary
            for graph in graphs_of(store, *kinds):
                quads = list(store.quads_for_pattern(None, None, None, ox.NamedNode(graph)))
                self.store.extend(ox.Quad(q.subject, q.predicate, q.object) for q in quads)
                if graph in ontologies and quads:
                    name = _prefix_of(quads) or local_of(graph)
                    while name in self.vocabularies:
                        name += "_"
                    self.vocabularies[name] = _turtle(quads)

    def tools(self) -> list[dict]:
        """The two tools the model reads the chat's graphs with, each answered by `call`."""
        prefixes = ", ".join(sorted(NAMESPACES))
        return [
            {"name": VOCABULARY, "description": "One vocabulary this chat lets you read, as Turtle: its classes and "
             "properties, with comments saying what each means. Load the ones a question needs before querying their "
             "terms.", "input_schema": {"type": "object", "properties": {"name": {
                 "type": "string", "description": "the vocabulary's name, as the briefing lists it"}}, "required": ["name"]}},
            {"name": QUERY, "description": "A SPARQL SELECT or ASK over every graph this chat lets you read, merged into "
             f"one default graph. These prefixes are declared for you: {prefixes}; declare any other with PREFIX, as "
             f"the vocabulary's Turtle does. Write no GRAPH, SERVICE or FROM. At most {ROWS} rows come back.",
             "input_schema": {"type": "object", "properties": {"sparql": {"type": "string"}}, "required": ["sparql"]}}]

    def call(self, name: str, inputs: dict) -> str | None:
        """What one of the two tools answers, or None where `name` is neither."""
        if name == VOCABULARY:
            return self.vocabulary(str(inputs.get("name") or ""))
        if name == QUERY:
            return self.query(str(inputs.get("sparql") or ""))
        return None

    def listing(self) -> str:
        """Each vocabulary the chat may read, by its prefix, with its size: what the model chooses from."""
        return "\n".join(f" - {name} ({text.count(chr(10))} lines)" for name, text in sorted(self.vocabularies.items()))

    def vocabulary(self, name: str) -> str:
        """One vocabulary the chat may read, as Turtle; told so where it reads none of that name."""
        found = self.vocabularies.get(name.strip().rstrip(":"))
        if found is None:
            return f"no vocabulary {name!r} in this chat; these are: {', '.join(sorted(self.vocabularies))}"
        return found

    def query(self, text: str) -> str:
        """The model's SELECT or ASK over what the chat reads, its rows as lines; the reason, where it is refused."""
        refused = _refusal(text)
        if refused:
            return f"refused: {refused}"
        out = io.BytesIO()
        try:
            self.store.query(text, prefixes=NAMESPACES).serialize(output=out, format=ox.QueryResultsFormat.JSON)
        except (SyntaxError, OSError, ValueError) as exc:
            return f"the engine would not run it: {exc}"
        answer = json.loads(out.getvalue())
        if "boolean" in answer:
            return str(answer["boolean"]).lower()
        found = bindings(answer)
        shown = [", ".join(f"{k}: {v}" for k, v in row.items() if v is not None) for row in found[:ROWS]]
        more = f"\n(the first {ROWS} of {len(found)} rows: ask more narrowly)" if len(found) > ROWS else ""
        return ("\n".join(shown) or "(no rows)") + more


def _refusal(text: str) -> str | None:
    """Why a query may not run: not parsed, not a SELECT or an ASK, or holding what reads past the chat."""
    try:
        parsed = parseQuery(_HEADER + text)
    except Exception as exc:                                     # noqa: BLE001 — the parser's own errors
        return f"it does not parse: {exc}"
    query = parsed[1]
    if getattr(query, "name", None) not in _KINDS:
        return "only a SELECT or an ASK is run"
    found = _holds(query)
    return f"it holds {found}, and a query reads only what the chat reads" if found else None


def _holds(node) -> str | None:
    if isinstance(node, CompValue):
        if node.name in _REFUSED:
            return _REFUSED[node.name]
        if "datasetClause" in node.keys():                       # `get` answers a missing key with its name
            return _REFUSED["datasetClause"]
        children = node.values()
    elif isinstance(node, (list, tuple)):
        children = node
    else:
        return None
    for child in children:
        if (found := _holds(child)) is not None:
            return found
    return None


def _prefix_of(quads) -> str | None:
    """The name a vocabulary goes by: the store's prefix for the namespace most of its subjects are named in, or the
    namespace's last word where the store has none for it, as a domain's has not."""
    counts: dict[str, int] = {}
    for q in quads:
        if isinstance(q.subject, ox.NamedNode):
            iri = q.subject.value
            ns = iri[:max(iri.rfind("#"), iri.rfind("/")) + 1]
            counts[ns] = counts.get(ns, 0) + 1
    if not counts:
        return None
    ns = max(counts, key=counts.get)
    known = {iri: prefix for prefix, iri in NAMESPACES.items()}
    return known.get(ns) or ns.rstrip("#/").rsplit("/", 1)[-1] or None


def _turtle(quads) -> str:
    out = ox.Store()
    out.extend(ox.Quad(q.subject, q.predicate, q.object) for q in quads)
    return ox.serialize(out, format=ox.RdfFormat.TURTLE, prefixes=NAMESPACES).decode()
