"""The FOOTPRINT of a text — what it reads and what it writes — read off the text itself.

Two sets per action, both derived and neither declared (#488):

- what it WRITES — the predicates of its effect's rules, the construct templates and the deletes;
- what it READS — the predicates of its `planning:precondition`.

A derivation rule is the same pair read off one INSERT: its template writes, its WHERE reads.
Nothing here is declared — a stated `orexis:touches` would be a second statement of what the
construct already settles — and nothing is stored: computed per call, parsed once per text.

ANYTHING UNREADABLE READS AS `ANYTHING`: a body the parser refuses, a template with a variable
predicate that nothing bounds. Over-approximation is safe wherever these sets are used and
under-approximation is not, which is why the unreadable case is a value rather than an error.

**A VARIABLE IN PREDICATE POSITION WRITES WHAT A `VALUES` BLOCK BINDS IT TO.** SPARQL's own way
of bounding a variable is a `VALUES` block in the text the engine runs, and that is the one
place a range is honoured: a template writing `?s ?p ?o` beside `VALUES ?p { a b }` writes
two predicates, not anything. A range declared beside the text — `rdfs:range` on a parameter
— would be a promise about the text that nothing holds the text to, and is not read. A row
leaving the variable `UNDEF`, or binding it to a literal, unbounds it again.

**AND WHAT A WANT READS**, off its met-test: every predicate its paths navigate and its
`sh:sparql` constraints mention. That is the question "which words is this want in play over",
answered by reading the shape rather than by a property somebody declared beside it — which is
the whole point, since a declared one narrows the planning problem before the planner has seen
it. A want whose shape the walker cannot read reads as ANYTHING and is in play over
everything, which is the safe direction.

**TWO KINDS OF FUNCTION, TOLD APART BY WHAT THEY ARE HANDED.** Over the STORE:
`actions_of(store)` and `stored_edges(store, graphs)`, which read what the store holds and
answer for every action and every derivation in it. Over a TEXT or a parsed shape:
`parseable`, `reads_of_select`, `writes_of_construct`, `reads_of_shape`, which own nothing and
ask nothing — hand one a string and it answers. The store-facing pair is written the way
everything else here is (a-function-over-the-store-is-handed-the-engine): `actions_of` took a
QUERY, a lambda closing over the store and the graphs to read, which is the caller deciding
what this reads and this deciding nothing.

**WHAT THIS ANSWERS FOR IS THE SCOPES.** `scope_actions` clusters the vocabulary by which
predicates move together, and a want belongs to the scope of what it reads. It returns with the thing that needs it (an-agent-is-four-things).

**AND A PREDICATE ON A KEY** (`atoms_of`, #593). A predicate alone separates a vocabulary and
never two instances of one: a pump and a heater both write `sensing:below` of a reading, and over
predicates they are one scope though nothing either does reaches the other's property. What tells
their writes apart is WHOM the reading is of — the subject and the property the precondition binds
it by, both public facts. So an action's footprint is read per FILLING: its precondition is asked
over the public graphs with every pattern optional, which binds what the world states and leaves
what the state would have bound unbound; each row is one filling as far as the world alone decides
it; and each pattern a filling reads or writes is an atom `(predicate, key)`, the key being the
subject's own value where the row binds it and otherwise the values of the variables that share a
pattern with the subject — a reading is keyed by its feature and its property, exactly as sensing
keys it. A subject the world binds nothing of is keyed by nothing and its atom joins every atom of
that predicate, which is the predicate partition again, the safe side.
"""

from __future__ import annotations

from datetime import datetime

import functools
import logging
import re

import pyoxigraph as ox
import rdflib
from rdflib import RDF, URIRef
from rdflib.collection import Collection
from rdflib.paths import AlternativePath, InvPath, MulPath, NegatedPath, SequencePath
from rdflib.plugins.sparql.algebra import translateQuery, translateUpdate, traverse
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate

#  WHAT A `$token` IS, from the module that BINDS one. It was spelled here too, a
#  character apart, which is two definitions of one thing waiting to disagree.
from agent import clock
from agent.ontology import ACTION, PUBLIC, SELF, local_of
from agent.store import _TOKEN, NAMESPACES, PREFIXES, graphs_of, rows

log = logging.getLogger("footprint")

SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
ANYTHING = None          # the set that contains every predicate: unreadable, so unfiltered

#  The tokens a rule text takes, each replaced with something that PARSES — a variable where
#  the token is a term, a row where it is a VALUES block, nothing where it is a USING list.
#  Parsing is all this is for: nothing is run, so the values are never right, only well-formed.
_PARSE_TOKENS = {
    "$given": "", "$derived": "<urn:parse:derived>", "$evidence": "<urn:parse:evidence>",
    "$wants": "(<urn:parse:want> <urn:parse:about>)", "$properties": "<urn:parse:property>",
    "$litres": "1.0", "$this": "?this",
}
_INTO = re.compile(r"\$into\([^)]*\)")

#  THE SELF IS NO FACT OF THE WORLD. A text asks for the agent as `?me a orexis:Self`, the one row
#  of the self graph its world authors for it (knowledge/domain/kernel/self.md): no public graph
#  holds it and no action writes it, so a footprint — a text read as the world alone would answer
#  it — reads the text without it, `?me` the free variable the agent always was here. Read with it,
#  the anchor binds nothing over the public graphs, stands first in rdflib's order since it is the
#  pattern with the fewest variables, and reorders the OPTIONAL chain a filling is asked as: measured
#  on the greenhouse, the dose came to be filled with the heater as its valve and the scopes moved.
_SELF_ANCHOR = re.compile(r"(\?\w+)\s+(?:a|rdf:type)\s+(?:orexis:Self|<" + re.escape(SELF) + r">)\s*(;|\.|(?=\}))")


def parseable(text: str) -> str:
    """The text with every `$token` made parseable — see `_PARSE_TOKENS` — and the self's anchor
    read as absent (`_SELF_ANCHOR`)."""
    text = _INTO.sub("<urn:parse:into>", text)
    for token, stand_in in _PARSE_TOKENS.items():
        text = text.replace(token, stand_in)
    text = _SELF_ANCHOR.sub(lambda m: m.group(1) if m.group(2) == ";" else "", text)
    return _TOKEN.sub(lambda m: "?" + m.group(1), text)


# --- predicates of a text ----------------------------------------------------------------------

def _path_iris(p) -> set | None:
    if isinstance(p, URIRef):
        return {p}
    if isinstance(p, (MulPath, InvPath)):
        return _path_iris(p.path if isinstance(p, MulPath) else p.arg)
    if isinstance(p, (SequencePath, AlternativePath)):
        out = set()
        for a in p.args:
            part = _path_iris(a)
            if part is None:
                return ANYTHING
            out |= part
        return out
    if isinstance(p, NegatedPath):
        return ANYTHING                                  # "anything but" is anything
    return ANYTHING                                      # a variable predicate


def _read(s, p, o) -> set | None:
    """What one triple pattern reads: its predicate's IRIs — or, for a type pattern whose class is
    an IRI, the CLASS. `?x a hanoi:Peg` and `?v a courier:Van` read two different things; keyed by
    `rdf:type` alone they read one, and every domain's actions joined one scope through it (#663).
    A type pattern whose class is a variable reads every type, `rdf:type` itself."""
    if p == RDF.type and isinstance(o, URIRef):
        return {o}
    return _path_iris(p)


_EXISTS = ("Builtin_EXISTS", "Builtin_NOTEXISTS")


def _triples_in(node) -> list[tuple] | None:
    """Every triple pattern under `node` as `(s, p, o)`, under its groups and under its EXISTS
    filters alike, in the order met and each once — or ANYTHING where a block will not read as
    triples.

    A PATTERN UNDER EXISTS / NOT EXISTS IS READ AS MUCH AS ONE IN THE GROUP — a want saying "unmet
    while this fact is absent" reads that fact's predicate (#523) — and rdflib hands it over in two
    places at once. The algebra's `traverse` walks a node's KEYS, and under the key `graph` an EXISTS
    node keeps the PARSE-TREE group: its `TriplesBlock`s, each entry one `TriplesSameSubjectPath`
    laid flat — `?c :calledBy ?me ; :calledOn ?v` is one entry of SIX terms, s p o s p o, as an
    object list `?c :p ?v , ?w` and a blank node `?c :p [ :q ?v ]` are — and its filters POPPED
    OUT, since `collectAndRemoveFilters` took them from that list to build the translated group.
    The translated group hangs beside the key as the ATTRIBUTE `graph`: `translateExists` set it
    with `n.graph = …`, which on rdflib's `CompValue` lands in the instance and not the dict, and
    rdflib's own evaluator reads it there. That is where a filter NESTED in the filter now lives,
    BGPs of three and a `Filter` whose expression is the inner EXISTS. Read only the key, an entry
    of six was unreadable and the inner filter invisible — the market's `Calling` read anything and
    `Tendering` with it, every world of a market agent was hashed whole, and had the entry alone
    been chunked both would have read every predicate but `answered` and `clearedAt`, the unsafe
    side (#908). So BOTH are read: the key's blocks three terms at a time, and the attribute's
    algebra as any group's, recursively; what each finds twice the set keeps once.
    """
    found: list = []
    seen: set = set()
    bad = [False]

    def keep(triple) -> None:
        if triple not in seen:
            seen.add(triple)
            found.append(triple)

    def visit(n):
        name = getattr(n, "name", None)
        if name == "BGP":
            for triple in n["triples"]:
                keep(tuple(triple))
        elif name == "TriplesBlock":
            for entry in n["triples"]:
                if len(entry) % 3:
                    bad[0] = True
                else:
                    for i in range(0, len(entry), 3):
                        keep(tuple(entry[i:i + 3]))
        elif name in _EXISTS:
            translated = vars(n).get("graph")
            inner = _triples_in(translated) if translated is not None else []
            if inner is None:
                bad[0] = True
            else:
                for triple in inner:
                    keep(triple)
        return n
    traverse(node, visitPost=visit)
    return ANYTHING if bad[0] else found


def _predicates_in(node, out: set) -> bool:
    """Collect the predicates of every triple pattern under `node`; False if any is unreadable."""
    triples = _triples_in(node)
    if triples is None:
        return False
    for triple in triples:
        iris = _read(*triple)
        if iris is None:
            return False
        out.update(iris)
    return True


@functools.lru_cache(maxsize=512)
def reads_of_select(text: str) -> frozenset | None:
    """The predicates a SELECT's or a CONSTRUCT's WHERE reads, or ANYTHING if unparseable."""
    try:
        alg = translateQuery(parseQuery(PREFIXES + parseable(text))).algebra
    except Exception as exc:                            # noqa: BLE001 — unreadable is a finding
        log.debug("could not parse a query for the predicates it reads: %s", exc)
        return ANYTHING
    out: set = set()
    where = alg.get("p", alg)
    return frozenset(out) if _predicates_in(where, out) else ANYTHING


def reads_of_shape(shapes: rdflib.Graph, shape) -> frozenset | None:
    """Every predicate a shape's paths and SPARQL constraints read, or ANYTHING.

    NOT MEMOISED ON THE GRAPH. It carried an `lru_cache` keyed on `shapes`, and an rdflib
    graph hashes by its identifier — a fresh blank node per `Graph()` — so a view crossed per
    pass never hit and the cache held up to 512 whole graphs alive in a long-running agent,
    measured: two fresh graphs neither compare nor hash equal. The walk is cheap; the crossing
    is what costs, and the caller keeps that.
    """
    out: set = set()
    for prop in shapes.objects(shape, SH.property):
        iris = _shacl_path_iris(shapes, shapes.value(prop, SH.path))
        if iris is None:
            return ANYTHING
        out |= iris
        for p, o in shapes.predicate_objects(prop):
            if p == SH.equals:
                out.add(o)
            if p == SH.qualifiedValueShape:
                inner = reads_of_shape(shapes, o)
                if inner is None:
                    return ANYTHING
                out |= inner
    for constraint in shapes.objects(shape, SH.sparql):
        inner = reads_of_select(str(shapes.value(constraint, SH.select) or ""))
        if inner is None:
            return ANYTHING
        out |= inner
    #  AN AVOIDED STATE carries its one select itself (#892): the node a `planning:unmetWhen`
    #  points at is no shape, and what its want reads is what that select reads.
    for text in shapes.objects(shape, SH.select):
        inner = reads_of_select(str(text))
        if inner is None:
            return ANYTHING
        out |= inner
    for negated in shapes.objects(shape, SH["not"]):
        inner = reads_of_shape(shapes, negated)
        if inner is None:
            return ANYTHING
        out |= inner
    for p in (SH.targetSubjectsOf, SH.targetObjectsOf):
        out |= set(shapes.objects(shape, p))
    out |= set(shapes.objects(shape, SH.targetClass))       # a class target reads that class
    return frozenset(out)

def terms_of_shape(shapes: rdflib.Graph, shape) -> frozenset:
    """Every TERM a shape names as what it is about or holds a value to — `planning:about` on its
    blocks and constraints, `sh:hasValue` and `sh:class` on them and inside their qualified value
    shapes, and a class it targets — the quantity kinds a scope holds as members, which is how a want
    reading a predicate two scopes share is placed by the property it reads it of (#593)."""
    about = URIRef("http://example.org/orexis/planning#about")
    out: set = set()
    for p in (SH.property, SH.sparql):
        for block in shapes.objects(shape, p):
            for q in (about, SH.hasValue, SH["class"]):
                out |= {o for o in shapes.objects(block, q) if isinstance(o, URIRef)}
            for inner in shapes.objects(block, SH.qualifiedValueShape):
                out |= terms_of_shape(shapes, inner)
    for negated in shapes.objects(shape, SH["not"]):
        out |= terms_of_shape(shapes, negated)
    out |= {o for o in shapes.objects(shape, SH.targetClass) if isinstance(o, URIRef)}
    #  An avoided state says what it is about on the node itself (#892); `sh:this` names the
    #  instance and no term.
    out |= {o for o in shapes.objects(shape, about) if isinstance(o, URIRef) and o != SH.this}
    return frozenset(out)


def _shacl_path_iris(g: rdflib.Graph, node) -> set | None:
    if node is None:
        return ANYTHING
    if isinstance(node, URIRef):
        return {node}
    if (node, RDF.first, None) in g:
        out = set()
        for part in Collection(g, node):
            iris = _shacl_path_iris(g, part)
            if iris is None:
                return ANYTHING
            out |= iris
        return out
    for pred in (SH.inversePath, SH.oneOrMorePath, SH.zeroOrMorePath, SH.zeroOrOnePath):
        inner = g.value(node, pred)
        if inner is not None:
            return _shacl_path_iris(g, inner)
    alternatives = g.value(node, SH.alternativePath)
    if alternatives is not None:
        return _shacl_path_iris(g, alternatives)
    return ANYTHING


def writes_of_construct(text: str) -> frozenset | None:
    """The predicates a CONSTRUCT's template writes, or ANYTHING if unparseable — or if a
    template predicate is a variable that no `VALUES` block in the WHERE bounds to IRIs."""
    try:
        alg = translateQuery(parseQuery(PREFIXES + parseable(text))).algebra
    except Exception as exc:                            # noqa: BLE001
        log.debug("could not parse a construct for the predicates it writes: %s", exc)
        return ANYTHING
    out: set = set()
    bounded = None
    for _, p, o in alg.get("template") or ():
        if p == RDF.type and isinstance(o, URIRef):
            out.add(o)                                   # a type written is its class, as read
            continue
        if isinstance(p, URIRef):
            out.add(p)
            continue
        if bounded is None:
            bounded = _values_in(alg.get("p"))
        iris = bounded.get(p)
        if not iris:
            return ANYTHING
        out |= iris
    return frozenset(out)


def _values_in(node) -> dict:
    """Every variable a `VALUES` block under `node` binds, to the IRIs it binds it to — None
    where any row leaves it `UNDEF` or binds it to something that is not an IRI. Two blocks
    binding one variable are unioned, which over-approximates the join and is the safe side."""
    found: dict = {}
    def visit(n):
        if getattr(n, "name", None) == "values":
            for row in n["res"]:
                for var, term in row.items():
                    if var in found and found[var] is None:
                        continue
                    if isinstance(term, URIRef):
                        found.setdefault(var, set()).add(term)
                    else:
                        found[var] = None
        return n
    if node is not None:
        traverse(node, visitPost=visit)
    return found


# --- the footprint of each action and each derivation -----------------------------------------------

#  ONE ROW PER RULE OF AN ACTION'S EFFECT, with the action's precondition on each.
_ACTIONS_Q = """
SELECT ?action ?precondition ?construct ?update WHERE {
  ?action a orexis:Action .
  OPTIONAL { ?action planning:precondition ?precondition }
  OPTIONAL { ?action planning:effect/sh:rule ?r . OPTIONAL { ?r sh:construct ?construct } OPTIONAL { ?r planning:update ?update } }
}"""

def written(store, at: datetime | None = None) -> frozenset[str]:
    """Every predicate some action's effect can write, as strings — what a world can change. An
    action whose writes cannot be read writes anything, and then nothing is left out."""
    out: set[str] = set()
    for _, writes in actions_of(store, at).values():
        if writes is ANYTHING:
            return frozenset()
        out |= {str(w) for w in writes}
    return frozenset(out)


def actions_of(store, at: datetime | None = None) -> dict[str, tuple]:
    """Every action the store holds as `iri -> (reads, writes)`, each ANYTHING where unreadable.

    A FUNCTION OVER THE STORE, handed the engine and nothing else. It took a QUERY — a lambda
    closing over the store and the graphs to read — which is the caller deciding what this
    reads and this deciding nothing; the graphs an action is declared in are public knowledge,
    which is this module's to ask for, as `stored_edges` beside it already asks.
    """
    out = {}
    effects: dict[str, dict] = {}
    for row in rows(store, _ACTIONS_Q, graphs_of(store, ACTION, at=at or clock.now())):
        held = effects.setdefault(row["action"], {"precondition": row.get("precondition"), "constructs": [], "updates": []})
        if row.get("construct"):
            held["constructs"].append(row["construct"])
        if row.get("update"):
            held["updates"].append(row["update"])
    for action, effect in effects.items():
        if not effect["constructs"]:
            #  AN ACTION STATING NO EFFECT is an action an event adopts (#506) — never on a
            #  admitted by any world, never simulated — and has no place in a closure that
            #  simulated. Reading it as ANYTHING-writes-ANYTHING collapsed every want's
            #  closure to everything, for the market's Presenting.
            continue
        #  No precondition text is a lever with nothing to widen the want by — a world
        #  yields it no rows, but a construct it does carry says what it would write.
        reads = reads_of_select(effect["precondition"]) if effect["precondition"] else frozenset()
        writes = frozenset()
        for text in effect["constructs"]:
            part = writes_of_construct(text)
            writes = ANYTHING if part is ANYTHING or writes is ANYTHING else frozenset(writes | part)
        for text in effect["updates"] if writes is not ANYTHING else ():
            part = writes_of_construct(text)
            if part is not ANYTHING:
                writes = frozenset(writes | part)
            #  else: A DELETE WITH A VARIABLE PREDICATE beside a construct — `?standing ?p
            #  ?o`, every shipped reading-replacing lever — removes the node the construct
            #  replaces, the readings graph's upsert, and so writes what the construct
            #  writes. Read as ANYTHING it made every such lever relevant to every want, and
            #  every want's view the whole world (#554, #565).
        row = {"action": action}
        out[row["action"]] = (reads, writes)
    return out


#  THE EDGES AS THE STORE HOLDS THEM: one `planning:Derivation` per INSERT, its sides as
#  predicates or as `planning:Anything`. Asked of the graphs of derivations by class.
_EDGES_Q = """
SELECT ?d ?reads ?writes WHERE {
  ?d a planning:Derivation .
  OPTIONAL { ?d planning:reads ?reads }
  OPTIONAL { ?d planning:writes ?writes } }"""


def stored_edges(store, graphs) -> tuple:
    """The derivations' (reads, writes) edges, read back from `graphs` — what genesis wrote
    from the rule files. A side saying `planning:Anything` is ANYTHING; a side saying
    nothing at all is empty, which is what a rule reading or writing no named predicate is."""
    from agent.store import rows

    from .ontology import ANYTHING as ANYTHING_IRI

    sides: dict = {}
    for row in rows(store, _EDGES_Q, graphs):
        reads, writes = sides.setdefault(row["d"], (set(), set()))
        for side, key in ((reads, "reads"), (writes, "writes")):
            if row.get(key):
                side.add(row[key])
    out = []
    for _name, (reads, writes) in sorted(sides.items()):
        out.append((ANYTHING if ANYTHING_IRI in reads else frozenset(URIRef(p) for p in reads),
                    ANYTHING if ANYTHING_IRI in writes else frozenset(URIRef(p) for p in writes)))
    return tuple(out)


# --- the footprint per filling: predicates on keys ----------------------------------------------

#  A FILLING AS THE WORLD ALONE DECIDES IT: the precondition's patterns, each OPTIONAL, asked over
#  the public graphs — what the world states binds, what the state would have bound stays unbound.
_PUBLIC_P_Q = "SELECT DISTINCT ?p WHERE { ?s ?p ?o }"


def atoms_of(store, at: datetime | None = None) -> dict[str, list | None]:
    """Every action the store holds as `iri -> fillings`, each filling `(atoms, terms)`: the atoms
    `(predicate, key)` the filling reads of what some action writes and the atoms it writes, and
    the public terms its key values are. ANYTHING where the action's texts cannot be read so.

    The KEY of a pattern's subject is its own value where the filling binds it — a disk, a venue,
    the agent — and otherwise the values of the variables sharing a pattern with it that the filling
    does bind — a reading's feature and property — and None where it binds none, which joins every
    atom of the predicate. Over-approximation is the safe side throughout: a filling the world
    alone cannot narrow is every filling, and an atom keyed by nothing is every atom.

    AND A ROW THE WORLD HAS ANSWERED "NONE" IS NO FILLING: one leaving unbound a parameter the
    world alone decides (`_decided_by_the_world`). An action every row of which is that maps to no
    filling at all, and is in no scope (#913).
    """
    out: dict = {}
    effects = _effects(store, at)
    if not effects:
        return out
    public = graphs_of(store, PUBLIC, at=at or clock.now())
    changeable = {str(p) for _, writes in actions_of(store, at).values() if writes is not ANYTHING for p in writes}
    takes: dict = {}
    for row in rows(store, _TAKES_Q, graphs_of(store, ACTION, at=at or clock.now())):
        takes.setdefault(row["action"], set()).add(local_of(row["takes"]))
    written = {action: _written_subjects(effect["constructs"], effect["updates"])
               for action, effect in effects.items() if effect["constructs"]}
    #  WHAT ANY EFFECT TOUCHES, written or deleted — the state's predicates, as against the world's.
    touched = set(changeable)
    for subjects in written.values():
        if subjects is not ANYTHING:
            touched |= {p for predicates in subjects.values() for p in predicates}
    for action, effect in effects.items():
        if not effect["constructs"]:
            continue
        parsed = _patterns(effect["precondition"]) if effect["precondition"] else []
        if parsed is ANYTHING or written[action] is ANYTHING:
            out[action] = ANYTHING
            continue
        decided = _decided_by_the_world(parsed, written[action], touched, takes.get(action, ()))
        out[action] = _fillings(store, public, parsed, written[action], changeable, decided)
        if decided and not out[action]:
            log.info("%s takes %s, of which this world states none: it has no filling here, and is in no scope",
                     action, ", ".join(sorted(decided)))
    return out


#  WHAT AN ACTION TAKES, by local part — the variable its precondition projects (`orexis:takes`).
_TAKES_Q = "SELECT ?action ?takes WHERE { ?action a orexis:Action ; orexis:takes ?takes }"


def _decided_by_the_world(patterns: list, written: dict, touched: set, takes) -> frozenset[str]:
    """The parameters an action takes that the WORLD ALONE decides: each stands in some pattern of
    the precondition, is no subject the effect writes, and stands in no pattern reading a predicate
    any effect writes or deletes — the valve, the heater, the cell a van drives to, as against the
    reading a dose moves or the van that drives. Asked over the public graphs, such a parameter is
    bound wherever the world holds one; left unbound, the world has said it holds none."""
    out = set()
    for param in takes:
        var = rdflib.Variable(param)
        stands = [(s, p, o) for s, p, o in patterns if var in (s, o)]
        if not stands or param in written:
            continue
        reads: set = set()
        for triple in stands:
            reads |= {str(x) for x in (_read(*triple) or ())}
        if not reads & touched:
            out.add(param)
    return frozenset(out)


def _effects(store, at: datetime | None) -> dict[str, dict]:
    effects: dict[str, dict] = {}
    for row in rows(store, _ACTIONS_Q, graphs_of(store, ACTION, at=at or clock.now())):
        held = effects.setdefault(row["action"], {"precondition": row.get("precondition"), "constructs": [], "updates": []})
        if row.get("construct"):
            held["constructs"].append(row["construct"])
        if row.get("update"):
            held["updates"].append(row["update"])
    return effects


def _patterns(text: str) -> list | None:
    """The triple patterns a SELECT reads, under its groups and under its EXISTS filters alike, as
    `(s, p, o)` of rdflib terms — the variables named, tokens among them — or ANYTHING."""
    try:
        alg = translateQuery(parseQuery(PREFIXES + parseable(text))).algebra
    except Exception as exc:                            # noqa: BLE001
        log.debug("could not parse a precondition for its patterns: %s", exc)
        return ANYTHING
    triples = _triples_in(alg.get("p", alg))
    if triples is None or any(_read(*triple) is None for triple in triples):
        return ANYTHING
    return triples


def _written_subjects(constructs: list[str], updates: list[str]) -> dict | None:
    """What an effect writes, as `subject variable -> predicates` off its CONSTRUCT templates and
    its DELETE templates — a type written is its class — or ANYTHING where a template's predicate
    is a variable or its subject is not one."""
    out: dict = {}
    for text in constructs:
        try:
            alg = translateQuery(parseQuery(PREFIXES + parseable(text))).algebra
        except Exception:                                   # noqa: BLE001
            return ANYTHING
        if _collect(alg.get("template") or (), out) is ANYTHING:
            return ANYTHING
    for text in updates:
        try:
            ops = translateUpdate(parseUpdate(PREFIXES + parseable(text))).algebra
        except Exception:                                   # noqa: BLE001
            return ANYTHING
        for op in ops:
            delete = getattr(op, "delete", None)
            if delete is None:
                continue
            if _collect(getattr(delete, "triples", ()) or (), out) is ANYTHING:
                return ANYTHING
    return out


def _collect(triples, out: dict):
    for s, p, o in triples:
        if not isinstance(s, rdflib.Variable):
            return ANYTHING
        if p == RDF.type and isinstance(o, URIRef):
            out.setdefault(str(s), set()).add(str(o))
        elif isinstance(p, URIRef):
            out.setdefault(str(s), set()).add(str(p))
        else:
            return ANYTHING
    return out


def _fillings(store, public, patterns: list, written: dict, changeable: set, decided=frozenset()) -> list:
    """Each filling the world alone decides, as `(atoms, terms)`: the public graphs asked the
    precondition's patterns, every one OPTIONAL and no filter, so a row binds what the world states
    and nothing else; then the atoms each filling reads of what some action writes, and writes.

    A ROW LEAVING UNBOUND A PARAMETER THE WORLD ALONE DECIDES IS NO FILLING (#913). The allotment
    imports the climate domain and holds no heater, so the heating's rows bound a grower and a plot
    and nothing the heating could be done with, and each made a scope of its own that admitted
    nothing and minted nothing, at an imaginarium a pass apiece — about as dear as a real scope's,
    measured. A row is kept where the query could not run, since then nothing was decided."""
    variables = sorted({str(t) for triple in patterns for t in triple if isinstance(t, rdflib.Variable)}
                       | set(written))
    rows_: list[dict] = [{}]
    if patterns:
        text = "SELECT DISTINCT * WHERE { " + " ".join(f"OPTIONAL {{ {_n3(s)} {_n3(p)} {_n3(o)} . }}" for s, p, o in patterns) + " }"
        try:
            found = store.query(text, prefixes=NAMESPACES, default_graph=[ox.NamedNode(g) for g in public])
            names = [v.value for v in found.variables]
            rows_ = [{n: solution[n] for n in names if solution[n] is not None} for solution in found] or [{}]
            rows_ = [bound for bound in rows_ if decided.issubset(bound)]
            if not rows_:
                return []
        except Exception as exc:                            # noqa: BLE001
            log.debug("a precondition's patterns would not run over the public graphs: %s", exc)
            rows_ = [{}]
    #  WHAT A SUBJECT IS KEYED BY where the world binds it nothing: the other end of every pattern
    #  it stands in — a variable the filling binds, or a constant the text states, which keys a
    #  reading `sosa:observedProperty :Moisture` as surely as one bound to a variable does.
    links: dict = {}
    for s, _, o in patterns:
        for a, b in ((s, o), (o, s)):
            if isinstance(a, rdflib.Variable) and isinstance(b, (rdflib.Variable, URIRef, rdflib.Literal)):
                links.setdefault(str(a), set()).add(b)
    fillings = []
    for bound in rows_ or [{}]:
        iris: set = set()

        def value(term) -> str:
            """A key value as text; an IRI among them is a TERM a scope may hold as a member, a
            literal — a topic's name, a figure — keys as well and is nobody's member."""
            if isinstance(term, (ox.NamedNode, URIRef)):
                iris.add(str(term.value if isinstance(term, ox.NamedNode) else term))
            return str(term.value if isinstance(term, (ox.NamedNode, ox.Literal)) else term)

        def key(var: str):
            if var in bound:
                return (value(bound[var]),)
            linked = set()
            for other in links.get(var, ()):
                if isinstance(other, rdflib.Variable):
                    if str(other) in bound:
                        linked.add(value(bound[str(other)]))
                else:
                    linked.add(value(other))
            return tuple(sorted(linked)) or None
        atoms = set()
        for s, p, o in patterns:
            if not isinstance(s, rdflib.Variable):
                continue
            for pred in _read(s, p, o):
                if str(pred) in changeable:
                    atoms.add((str(pred), key(str(s))))
        for subject, predicates in written.items():
            for pred in predicates:
                atoms.add((pred, key(subject)))
        #  THE FILLING'S TERMS: every IRI the world binds in it — the valve as much as the property it
        #  moves — so a scope can hold the valve as a member and a candidate filled with it is known
        #  for that scope's; a value two scopes' fillings both bind, the agent or the bed, is nobody's.
        for term in bound.values():
            value(term)
        fillings.append((frozenset(atoms), frozenset(iris)))
    return fillings


def _n3(term) -> str:
    """One rdflib term as the SPARQL text it is — a variable, an IRI, a literal; a blank node as a
    variable of its own, since a pattern's blank node is one."""
    if isinstance(term, rdflib.Variable):
        return f"?{term}"
    if isinstance(term, rdflib.BNode):
        return f"?_b{term}"
    return term.n3()
