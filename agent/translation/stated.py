"""`stated`: what a person may state in a chat, in the words the world's vocabularies declare — a statement made of it,
the belief it is taken as, and a statement the agent makes, as the model reads it to say it to a person.

**A WORD A CHAT ALLOWS IS A PROPERTY A VOCABULARY DECLARES.** `speech:allows` names a property, or `rdf:Property` for
every one a vocabulary the agent holds declares; a chat allowing none hears questions alone. A person states triples
in those words, and the vocabulary bounds what they may say of them: the subject a thing the world states of the
property's `rdfs:domain`, the object of its `rdfs:range` — a thing the world states of that class, or a literal of that
datatype — and either anything where the vocabulary says nothing. A triple outside those bounds is refused, and the
statement with it, and the model is told why; no shape per statement is authored, since the words already say what
may be said of what (knowledge/decisions/a-person-states-what-the-chat-allows-in-the-worlds-words.md).

**ONE STATEMENT PER SUBJECT AND PROPERTY**, a graph named by the two, so a thing said again of a subject replaces what
was said of it, and unsaid it is a statement of nothing — as a prediction supersedes by key. Inside it the triples,
the prose they were made from (`speech:prose`) and who said them (`speech:saidBy`), so the journal keeps the words with
the statement; speech's `heard` keeps it as any peer's document.

**BELIEVED AS THE WORLD'S WORD.** A person a chat allows a word speaks for the world in it, so what the statement says
is a belief no agent owns, derived from the statement and holding from when it was said: what revision reads beside
the world's documents, a common belief as theirs are. It is written here and not by an extraction, since speech hears
every peer's document alike and only this module checked the bounds — a peer's document saying a person said it is
believed of nothing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

import pyoxigraph as ox

from agent.hash_named_graph import hash_named_graph
from agent.ontology import BELIEF, DERIVED, local_of
from agent.store import Raw, add_quads, catalogue_of, entry, forget_graph, graphs_of, rows, update

SPEECH = "http://example.org/orexis/speech#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
XSD = "http://www.w3.org/2001/XMLSchema#"
#  EVERY PROPERTY, where a chat allows it: the class every property is.
PROPERTY = RDF + "Property"
_TYPE = ox.NamedNode(RDF + "type")
_PROSE, _SAID_BY = ox.NamedNode(SPEECH + "prose"), ox.NamedNode(SPEECH + "saidBy")
#  THE MOST THINGS OF A WORD'S DOMAIN THE MODEL IS TOLD OF, where the chat lets it read none.
THINGS = 40

#  EVERY PROPERTY A VOCABULARY DECLARES, with what it is said of and what it says.
_WORDS_Q = """
SELECT ?p (SAMPLE(?l) AS ?label) (SAMPLE(?c) AS ?comment) (SAMPLE(?d) AS ?domain) (SAMPLE(?r) AS ?range) WHERE {
  ?p a ?t . VALUES ?t { rdf:Property owl:ObjectProperty owl:DatatypeProperty }
  OPTIONAL { ?p rdfs:label ?l } OPTIONAL { ?p rdfs:comment ?c }
  OPTIONAL { ?p rdfs:domain ?d } OPTIONAL { ?p rdfs:range ?r } } GROUP BY ?p ORDER BY ?p"""
#  WHETHER THE WORLD STATES A THING OF A CLASS, or of a class beneath it, the closure holding every step.
_OF_Q = """SELECT ?c WHERE { $thing a ?c . FILTER(?c = $class || EXISTS { ?c rdfs:subClassOf $class }) } LIMIT 1"""
#  THE THINGS OF A CLASS, by their labels, for a model that reads nothing of the store.
_THINGS_Q = """SELECT DISTINCT ?i ?label WHERE { ?i a ?c . FILTER(isIRI(?i))
  FILTER(?c = $class || EXISTS { ?c rdfs:subClassOf $class }) OPTIONAL { ?i rdfs:label ?label } } ORDER BY ?i"""
_START_Q = """SELECT ?start WHERE { GRAPH $cat { $g dcterms:temporal ?p . ?p orexis:start ?start } } LIMIT 1"""

#  A LITERAL OF A DATATYPE, written plainly by the model: whether its text is one.
_LEXICAL = {"integer": int, "decimal": float, "double": float, "float": float,
            "boolean": lambda v: {"true": True, "false": False}[v], "dateTime": datetime.fromisoformat,
            "date": lambda v: datetime.fromisoformat(v).date()}


@dataclass(frozen=True)
class Word:
    iri: str
    label: str
    comment: str
    domain: str | None
    range: str | None


def words(store: ox.Store, allows) -> list[Word]:
    """The words a chat allowing `allows` lets a person state: each property a vocabulary declares that it names, or
    every one where it allows `rdf:Property`."""
    if not allows:
        return []
    every = PROPERTY in allows
    return [Word(r["p"], r.get("label") or local_of(r["p"]), " ".join((r.get("comment") or "").split()),
                 r.get("domain"), r.get("range"))
            for r in rows(store, _WORDS_Q, graphs_of(store, BELIEF, common=True))
            if every or r["p"] in allows]


def written(iri: str, prefixes: dict[str, str]) -> str:
    """`iri` as Turtle writes it: by a prefix that covers it, or whole."""
    for name, ns in sorted(prefixes.items(), key=lambda p: -len(p[1])):
        tail = iri[len(ns):]
        if iri.startswith(ns) and tail and all(ch.isalnum() or ch in "_-" for ch in tail):
            return f"{name}:{tail}"
    return f"<{iri}>"


def listing(store: ox.Store, allowed: list[Word], every: bool, prefixes: dict[str, str], things: bool) -> str:
    """What the briefing says a person may state: each word, what it is said of and what it says, then the things
    of its domain where the model reads nothing to find them by — or that any word a vocabulary declares may be."""
    if every:
        return ("A person may state here anything in a word a vocabulary declares, of what its domain says it is "
                "said of, a value its range says it takes.")
    out = []
    for w in allowed:
        line = f" - {written(w.iri, prefixes)} ({w.label})"
        if w.domain:
            line += f", of a {written(w.domain, prefixes)}"
        if w.range:
            line += f", a {written(w.range, prefixes)}"
        out.append(line + (f": {w.comment}" if w.comment else ""))
        if things and w.domain:
            found = rows(store, _THINGS_Q, graphs_of(store, BELIEF, common=True), **{"class": w.domain})[:THINGS]
            out += [f"     {written(t['i'], prefixes)}" + (f" ({t['label']})" if t.get("label") else "") for t in found]
    return "A person may state here, in these words alone:\n" + "\n".join(out)


def tool(prefixes: dict[str, str]) -> dict:
    """The tool the model states what a person says with: triples in the words the chat allows, and keys unsaid."""
    names = ", ".join(sorted(prefixes))
    return {"name": STATE, "description": (
        "State what the person says, that the agent then believes as the world's word: triples in Turtle, in the "
        "words the briefing says a person may state here, of a thing the world names; and unsay what was said of a "
        "subject in a word. Saying a word of a subject again replaces what was said of it. The agent answers what "
        f"it kept, or why it refused. These prefixes are declared for you: {names}."),
        "input_schema": {"type": "object", "properties": {
            "says": {"type": "string", "description": "the triples, in Turtle, without @prefix lines"},
            "unsays": {"type": "array", "items": {"type": "string"},
                       "description": "each 'subject word' pair what was said of is taken back, as Turtle names"}},
            "additionalProperties": False}}


STATE = "state"


def statement_of(store: ox.Store, allowed: list[Word], every: bool, prefixes: dict[str, str], inputs: dict,
                 *, by: str, prose: str, at: datetime) -> tuple[bytes | None, list[str]]:
    """The statements a person makes, as the TriG a peer's document is — one graph per subject and word, each triple
    held to its word's bounds — and the reasons it is refused, where any triple is outside them."""
    head = "".join(f"@prefix {name}: <{ns}> .\n" for name, ns in sorted(prefixes.items()))
    said, why = ox.Store(), []
    try:
        if str(inputs.get("says") or "").strip():
            said.load(input=(head + str(inputs["says"])).encode(), format=ox.RdfFormat.TURTLE)
        unsaid = ox.Store()
        for pair in inputs.get("unsays") or []:
            unsaid.load(input=(head + f"{pair} [] .").encode(), format=ox.RdfFormat.TURTLE)
    except (SyntaxError, ValueError) as exc:
        return None, [f"not Turtle: {exc}"]
    by_word = {w.iri: w for w in allowed}
    keys: dict[tuple[str, str], list[ox.Triple]] = {}
    for q in said:
        why += _outside(store, q, by_word, every)
        word = by_word.get(q.predicate.value)
        keys.setdefault((q.subject.value, q.predicate.value), []).append(
            ox.Triple(q.subject, q.predicate, _typed(q.object, word.range if word else None)))
    for q in unsaid:
        why += [w for w in _outside(store, q, by_word, every) if not w.startswith("its object")]
        keys.setdefault((q.subject.value, q.predicate.value), [])
    if why or not keys:
        return None, why or ["nothing is said"]
    doc = ox.Store()
    for (subject, predicate), triples in sorted(keys.items()):
        g = ox.NamedNode(f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, subject + ' ' + predicate)}")
        doc.extend(ox.Quad(t.subject, t.predicate, t.object, g) for t in triples)
        doc.add(ox.Quad(g, _PROSE, ox.Literal(prose), g))
        doc.add(ox.Quad(g, _SAID_BY, ox.NamedNode(by), g))
        period = ox.BlankNode()
        doc.add(ox.Quad(g, _TYPE, ox.NamedNode(SPEECH + "StatementGraph"), ox.DefaultGraph()))
        doc.add(ox.Quad(g, ox.NamedNode("http://purl.org/dc/terms/temporal"), period, ox.DefaultGraph()))
        doc.add(ox.Quad(period, _TYPE, ox.NamedNode("http://purl.org/dc/terms/PeriodOfTime"), ox.DefaultGraph()))
        doc.add(ox.Quad(period, ox.NamedNode("http://example.org/orexis#start"),
                        ox.Literal(at.isoformat(), datatype=ox.NamedNode(XSD + "dateTime")), ox.DefaultGraph()))
    return doc.dump(format=ox.RdfFormat.TRIG), []


def _outside(store: ox.Store, q: ox.Quad, by_word: dict[str, Word], every: bool) -> list[str]:
    """Why one triple is outside what the chat allows and its word's bounds: nothing, where it is within them."""
    p, s, o = q.predicate.value, q.subject, q.object
    word = by_word.get(p)
    if word is None:
        return [f"{local_of(p)} is no word a person may state here" + ("" if every else ": " + ", ".join(
            sorted(local_of(w) for w in by_word)))]
    stated = graphs_of(store, BELIEF, common=True)
    if not isinstance(s, ox.NamedNode):
        return [f"{local_of(p)} is said of no thing the world names"]
    if word.domain and not rows(store, _OF_Q, stated, thing=s.value, **{"class": word.domain}):
        return [f"{local_of(s.value)} is no {local_of(word.domain)}, which {local_of(p)} is said of"]
    if not word.range or word.range == RDFS + "Literal":
        return []
    if word.range.startswith(XSD):
        if not isinstance(o, ox.Literal):
            return [f"its object for {local_of(p)} is no {local_of(word.range)}"]
        kind = local_of(word.range)
        if o.datatype.value != word.range and kind in _LEXICAL:
            try:
                _LEXICAL[kind](o.value)
            except (KeyError, ValueError):
                return [f"its object for {local_of(p)}, {o.value!r}, is no {kind}"]
        return []
    if not isinstance(o, ox.NamedNode) or not rows(store, _OF_Q, stated, thing=o.value, **{"class": word.range}):
        return [f"its object for {local_of(p)} is no {local_of(word.range)} the world names"]
    return []


def believed_of(statement: str) -> str:
    """Where what a person's statement says is believed: a graph derived from it."""
    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, statement + ' believed')}"


def believe(store: ox.Store, statement: str) -> list[str]:
    """What `statement` says, believed as the world's word: its triples in a belief no agent owns, derived from it and
    holding from when it was said, replacing what was believed of it before. The graph written, or none where it
    says nothing."""
    target = believed_of(statement)
    forget_graph(store, target)
    cat = catalogue_of(store)
    node = ox.NamedNode(statement)
    found = [q for q in store.quads_for_pattern(None, None, None, node) if q.subject != node]
    if cat is None or not found:
        return []
    add_quads(store, (ox.Quad(q.subject, q.predicate, q.object, ox.NamedNode(target)) for q in found))
    start = next(iter(rows(store, _START_Q, (), cat=cat, g=statement)), {}).get("start")
    update(store, f"""INSERT DATA {{ {entry(store, target, BELIEF, DERIVED, None, start)}
  GRAPH <{cat}> {{ <{target}> prov:wasDerivedFrom <{statement}> }} }}""")
    hash_named_graph(store, target)
    return [target]


def _typed(term, range_: str | None):
    """A plain literal of a word whose range is another datatype, as that datatype, so a person's "18:00" said of
    an instant is believed as one."""
    if (isinstance(term, ox.Literal) and range_ and range_.startswith(XSD) and range_ != XSD + "string"
            and term.datatype.value == XSD + "string"):
        return ox.Literal(term.value, datatype=ox.NamedNode(range_))
    return term


#  THE WORDS A STATEMENT IS IN, as a person reads them: each predicate's label and comment, and each thing's label.
_LABELS_Q = """SELECT ?t ?label ?comment WHERE { VALUES ?t { $terms } OPTIONAL { ?t rdfs:label ?label }
  OPTIONAL { ?t rdfs:comment ?comment } } ORDER BY ?t"""


def rendered(store: ox.Store, doc: ox.Store, prefixes: dict[str, str]) -> str:
    """A statement as the model reads it to say it to a person: its graphs' triples in Turtle, then what each word and
    thing in it is, by its label and the first sentence of its comment."""
    out = ox.Store()
    out.extend(ox.Quad(q.subject, q.predicate, q.object) for q in doc if q.graph_name != ox.DefaultGraph())
    terms = sorted({t.value for q in out for t in (q.subject, q.predicate, q.object) if isinstance(t, ox.NamedNode)})
    found = rows(store, _LABELS_Q, graphs_of(store, BELIEF, common=True),
                 terms=Raw(" ".join(f"<{t}>" for t in terms))) if terms else []
    words = [f" - {local_of(r['t'])}: {r.get('label') or ''}" + (f" — {(r.get('comment') or '').split('. ')[0]}"
                                                                    if r.get("comment") else "")
             for r in found if r.get("label") or r.get("comment")]
    return ox.serialize(out, format=ox.RdfFormat.TURTLE, prefixes=prefixes).decode() + (
        "\nThe words in it:\n" + "\n".join(words) if words else "")
