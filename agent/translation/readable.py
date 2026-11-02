"""`readable`: what a chat may read of the agent — the graphs of every kind the chat `speech:reads`, copied under
their names for the model's queries — and the two tools that read it, `vocabulary` and `query`
(knowledge/domain/speech/chat.md, knowledge/decisions/the-model-queries-what-its-chat-may-read.md).

**THE CHAT SAYS WHAT IT READS, AND THE MODEL NEVER CHOOSES A GRAPH.** A chat stating no kind reads nothing here, and
its model has the askables alone. One stating kinds — a sovereign's chat every graph, a broker's the market's — is
read as the graphs of those kinds in every store the agent holds, COPIED on the runtime's thread, each under its own
name with the catalogue's rows about it, so a query runs over what the chat admits and nothing else, whatever the
model writes, and a slow one stalls the model's thread and never a pass.

**A QUERY STATES THE KINDS IT READS, AS EVERY READER DOES.** Their graphs are its default graph and its `GRAPH`
range, and the catalogue is named beside them and never merged into them, since statements ABOUT graphs merged into
the data would answer open patterns that mean something else. Where a belief came from is a `GRAPH` away: the
graph's name is its document's, and the catalogue says its kinds, how it arrived, whose it is and when it holds.

**A QUERY IS READ, AND REFUSED BEFORE IT RUNS WHERE IT COULD DO ANYTHING BUT READ.** It is parsed with the store's
prefixes declared; anything but a SELECT or an ASK, and a `SERVICE` or a `FROM` anywhere in it, is refused
with the reason, as is a text the parser will not take, so the model may write it again. Its rows are capped at
`ROWS`.
"""

from __future__ import annotations

import io
import json
import re

import pyoxigraph as ox
from rdflib.plugins.sparql.parser import parseQuery
from rdflib.plugins.sparql.parserutils import CompValue

from agent.ontology import CLOSURE_GRAPH, OREXIS, local_of
from agent.store import NAMESPACES, catalogue_of, graphs_of

#  HOW MANY ROWS A QUERY HANDS THE MODEL: past these it is told how many there were, and asks again more narrowly.
ROWS = 50
ONTOLOGY = OREXIS + "OntologyGraph"
VOCABULARY, QUERY = "vocabulary", "query"
#  WHAT A QUERY MAY NOT HOLD: a graph of its own choosing, a service elsewhere, a dataset named.
_REFUSED = {"ServiceGraphPattern": "a SERVICE clause", "datasetClause": "a FROM"}
_KINDS = ("SelectQuery", "AskQuery")
_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
#  WHAT A NAME MAY BE AFTER A PREFIX, written plainly: where an IRI's tail is not one, it is written whole.
_LOCAL = re.compile(r"[A-Za-z0-9_](?:[A-Za-z0-9_.-]*[A-Za-z0-9_-])?")


class Readable:
    """What one chat may read: the graphs of its kinds, copied, and each vocabulary among them by its prefix — all
    read on the runtime's thread when it is made, and only the copy afterwards."""

    def __init__(self, stores, kinds, me: str | None = None):
        self.store = ox.Store()
        self.prefixes: dict[str, str] = dict(NAMESPACES)
        self.kinds: dict[str, set[ox.NamedNode]] = {}           # each kind a copied graph is, and the graphs it is
        self.catalogues: set[ox.NamedNode] = set()
        read: dict[str, list] = {}
        for store in {id(s): s for s in stores if s is not None}.values():
            ontologies = set(graphs_of(store, ONTOLOGY)) - {CLOSURE_GRAPH}      # derived, and no vocabulary
            catalogue = catalogue_of(store)
            for graph in graphs_of(store, *kinds):
                quads = list(store.quads_for_pattern(None, None, None, ox.NamedNode(graph)))
                self.store.extend(quads)                         # under its own name, so GRAPH says where a row is
                if catalogue is not None:
                    described = _described(store, ox.NamedNode(graph), ox.NamedNode(catalogue))
                    self.store.extend(described)
                    self.catalogues.add(ox.NamedNode(catalogue))
                    for q in described:
                        if q.subject == ox.NamedNode(graph) and q.predicate == _TYPE:
                            self.kinds.setdefault(q.object.value, set()).add(q.subject)
                if graph in ontologies and quads:
                    name, ns = _prefix_of(quads) or (local_of(graph), None)
                    while name in read:
                        name += "_"
                    read[name] = quads
                    if ns and ns not in self.prefixes.values() and name not in self.prefixes:
                        self.prefixes[name] = ns
        self.world = None                                        # the agent's world's names, by its namespace's word
        if me:
            ns = me[:max(me.rfind("#"), me.rfind("/")) + 1]
            self.world = _named(ns, set(self.prefixes) | set(read))
            self.prefixes[self.world] = ns
        self.vocabularies = {name: _glossary(quads, self.written) for name, quads in read.items()}

    def tools(self) -> list[dict]:
        """The two tools the model reads the chat's graphs with, each answered by `call`."""
        prefixes = ", ".join(sorted(self.prefixes))
        return [
            {"name": VOCABULARY, "description": "One vocabulary this chat lets you read, as a glossary: each class and "
             "property, a class with what it is beneath and a property with its domain and range, then the first "
             "sentence of what it means. Load the ones a question needs before querying their terms; a term's whole "
             "rdfs:comment, and anything else the vocabulary states, is read with the query tool.", "input_schema": {"type": "object", "properties": {"name": {
                 "type": "string", "description": "the vocabulary's name, as the briefing lists it"}}, "required": ["name"]}},
            {"name": QUERY, "description": "A SPARQL SELECT or ASK over the graphs of the kinds you name, of those the "
             "briefing lists: their union is the default graph, so name the kinds the question is about — "
             "observations, forecasts, the world's documents — and not more. GRAPH ?g ranges over those graphs, "
             "each named for its document, and over the catalogue, whose rows say of each graph its kinds (a), how it "
             "arrived (orexis:arrivedBy), whose it is (orexis:ownedBy) and when it holds (dcterms:temporal): where a "
             "belief came from is `GRAPH ?g { …the belief… } GRAPH ?c { ?g orexis:arrivedBy ?how }`. These prefixes "
             f"are declared for you: {prefixes}" + (f", {self.world}: naming the agent's own world" if self.world else "")
             + "; declare any other with PREFIX. The rows write a name with them, as the vocabularies do. Write no "
             f"SERVICE or FROM. At most {ROWS} rows come back.",
             "input_schema": {"type": "object", "properties": {
                 "kinds": {"type": "array", "items": {"type": "string"}, "minItems": 1,
                           "description": "the kinds of graph the query reads, as the briefing names them"},
                 "sparql": {"type": "string"}}, "required": ["kinds", "sparql"]}}]

    def call(self, name: str, inputs: dict) -> str | None:
        """What one of the two tools answers, or None where `name` is neither."""
        if name == VOCABULARY:
            return self.vocabulary(str(inputs.get("name") or ""))
        if name == QUERY:
            return self.query(str(inputs.get("sparql") or ""), list(inputs.get("kinds") or []))
        return None

    def listing(self) -> str:
        """What the model chooses from: each vocabulary the chat may read, by its prefix, with how many terms it has,
        then each kind of graph a query may name, with how many graphs are of it."""
        vocabularies = "\n".join(f" - {name} ({len(text.splitlines())} terms)"
                                 for name, text in sorted(self.vocabularies.items()))
        kinds = "\n".join(f" - {self.written({'type': 'uri', 'value': kind})} ({len(graphs)} graphs)"
                          for kind, graphs in sorted(self.kinds.items()))
        return f"Vocabularies, loaded by name:\n{vocabularies}\nKinds of graph, named by a query:\n{kinds}"

    def vocabulary(self, name: str) -> str:
        """One vocabulary the chat may read, as its glossary; told so where it reads none of that name."""
        found = self.vocabularies.get(name.strip().rstrip(":"))
        if found is None:
            return f"no vocabulary {name!r} in this chat; these are: {', '.join(sorted(self.vocabularies))}"
        return found

    def query(self, text: str, kinds: list[str]) -> str:
        """The model's SELECT or ASK over the graphs of `kinds`, the catalogue named beside them, its rows as lines;
        the reason, where it is refused."""
        refused = refusal(text, self.prefixes)
        if refused:
            return f"refused: {refused}"
        graphs: set[ox.NamedNode] = set()
        for kind in kinds:
            found = self.kinds.get(self.expanded(kind))
            if found is None:
                listed = ", ".join(self.written({"type": "uri", "value": k}) for k in sorted(self.kinds))
                return f"refused: no graph of kind {kind} in this chat; these are: {listed}"
            graphs |= found
        if not graphs:
            return "refused: name the kinds of graph the query reads"
        try:
            return answered(self.store.query(text, prefixes=self.prefixes, default_graph=sorted(graphs, key=str),
                                             named_graphs=sorted(graphs | self.catalogues, key=str)), self.written)
        except (SyntaxError, OSError, ValueError) as exc:
            return f"the engine would not run it: {exc}"

    def expanded(self, name: str) -> str:
        """A name the model wrote — `prefix:local`, `<iri>` or an IRI — as the IRI it is."""
        name = name.strip()
        if name.startswith("<") and name.endswith(">"):
            return name[1:-1]
        prefix, _, local = name.partition(":")
        return self.prefixes[prefix] + local if prefix in self.prefixes and not local.startswith("//") else name

    def written(self, value: dict) -> str:
        """One value of a row as the model reads it, with this chat's prefixes (`written`)."""
        return written(value, self.prefixes)


def _described(store, graph: ox.NamedNode, catalogue: ox.NamedNode) -> list:
    """What the catalogue says of one graph the chat reads — its kinds, how it arrived, whose it is, when it holds,
    the load that made it — and of each blank node it says that through, kept in the catalogue's name."""
    found, todo, seen = [], [graph], set()
    while todo:
        node = todo.pop()
        if node in seen:
            continue
        seen.add(node)
        for q in store.quads_for_pattern(node, None, None, catalogue):
            found.append(q)
            if isinstance(q.object, ox.BlankNode):
                todo.append(q.object)
    return found


def written(value: dict, prefixes: dict[str, str]) -> str:
    """One value of a SPARQL-JSON row as the model reads it: an IRI by the longest of `prefixes` it is under, whole
    where none fits; a literal by its text on one line, so a row stays one."""
    if value.get("type") != "uri":
        return " ".join(str(value.get("value", "")).split())
    iri = value["value"]
    for prefix, ns in sorted(prefixes.items(), key=lambda p: -len(p[1])):
        if iri.startswith(ns) and _LOCAL.fullmatch(iri[len(ns):]):
            return f"{prefix}:{iri[len(ns):]}"
    return f"<{iri}>"


def answered(result, write) -> str:
    """A query's result as the model reads it: an ASK's truth, or a row per line with each value `write`n, the rows
    capped at `ROWS` and their count said past it."""
    out = io.BytesIO()
    result.serialize(output=out, format=ox.QueryResultsFormat.JSON)
    answer = json.loads(out.getvalue())
    if "boolean" in answer:
        return str(answer["boolean"]).lower()
    found = answer.get("results", {}).get("bindings", [])
    shown = [", ".join(f"{k}: {write(v)}" for k, v in row.items()) for row in found[:ROWS]]
    more = f"\n(the first {ROWS} of {len(found)} rows: ask more narrowly)" if len(found) > ROWS else ""
    return ("\n".join(shown) or "(no rows)") + more


def refusal(text: str, prefixes: dict[str, str]) -> str | None:
    """Why a query may not run: not parsed, not a SELECT or an ASK, or holding what reads past the chat."""
    try:
        parsed = parseQuery("".join(f"PREFIX {p}: <{ns}>\n" for p, ns in prefixes.items()) + text)
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


def _prefix_of(quads) -> tuple[str, str] | None:
    """The name a vocabulary goes by, and its namespace: the store's prefix for the namespace most of its subjects are
    named in, or the namespace's last word where the store has none for it, as a domain's has not."""
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
    name = known.get(ns) or ns.rstrip("#/").rsplit("/", 1)[-1]
    return (name, ns) if name else None


def _named(ns: str, taken: set[str]) -> str:
    """A prefix for `ns`: its last word, made apart from every name in `taken`."""
    name = ns.rstrip("#/").rsplit("/", 1)[-1] or "world"
    while name in taken:
        name += "_"
    return name


def _glossary(quads, written) -> str:
    """A vocabulary as one line per class and property it declares: the term, what it is beneath or its domain and
    range, and the first sentence of its comment, each name `written` as a row writes it. Its shapes and rules are
    left to the query tool, since a question is about the terms."""
    vocabulary = ox.Store()
    vocabulary.extend(ox.Quad(q.subject, q.predicate, q.object) for q in quads)
    out = io.BytesIO()
    vocabulary.query(_GLOSSARY_Q, prefixes=NAMESPACES).serialize(output=out, format=ox.QueryResultsFormat.JSON)
    terms = []
    for row in json.loads(out.getvalue())["results"]["bindings"]:
        name = written(row["term"])
        kind = row["kind"]["value"]
        if kind == "class":
            about = f", beneath {written(row['above'])}" if "above" in row else ""
        else:
            ends = [written(row[k]) if k in row else "?" for k in ("domain", "range")]
            about = f", {ends[0]} → {ends[1]}" if ends != ["?", "?"] else ""
        said = _first_sentence(row["comment"]["value"]) if "comment" in row else ""
        terms.append(f"{name} ({kind}{about})" + (f": {said}" if said else ""))
    return "\n".join(sorted(terms))


#  WHAT A GLOSSARY SAYS OF A TERM: its kind, one class it is beneath or a property's domain and range, and its comment.
_GLOSSARY_Q = """
SELECT ?term (SAMPLE(?k) AS ?kind) (SAMPLE(?a) AS ?above) (SAMPLE(?d) AS ?domain) (SAMPLE(?r) AS ?range)
       (SAMPLE(?c) AS ?comment) WHERE {
  { ?term a ?t . VALUES ?t { owl:Class rdfs:Class } BIND("class" AS ?k)
    OPTIONAL { ?term rdfs:subClassOf ?a . FILTER(isIRI(?a)) } }
  UNION
  { ?term a ?t . VALUES ?t { owl:ObjectProperty owl:DatatypeProperty owl:AnnotationProperty rdf:Property }
    BIND("property" AS ?k)
    OPTIONAL { ?term rdfs:domain ?d . FILTER(isIRI(?d)) } OPTIONAL { ?term rdfs:range ?r . FILTER(isIRI(?r)) } }
  FILTER(isIRI(?term))
  OPTIONAL { ?term rdfs:comment ?c } } GROUP BY ?term"""
#  HOW LONG A GLOSSARY'S SENTENCE MAY RUN: past it the sentence is cut, and the query tool reads the rest.
SENTENCE = 200


def _first_sentence(text: str) -> str:
    """The first sentence of a comment, on one line, cut at `SENTENCE` characters."""
    flat = " ".join(text.split())
    first = re.split(r"(?<=[.!?])\s", flat, maxsplit=1)[0]
    return first if len(first) <= SENTENCE else first[:SENTENCE].rsplit(" ", 1)[0] + " …"
