"""A want's shape, compiled into the one select whose rows are its violations.

A want is authored as a SHACL shape (a-desire-is-a-shape): positive, universal, a picture of
the met world. The search judges every candidate world, and a shape goes through the judge,
whose reader has a fixed floor of tens of milliseconds per call — where a select on the
store's own engine costs about a millisecond. That gap is why the two puzzle worlds wrote
their goals as `orexis:unmetWhen` patterns by hand, and why those patterns read as a double
negative: rows are existential, the want is universal, so "every parcel delivered" had to be
said as "some parcel astray".

This module says it for them. A shape's Core constraints are each defined by the SHACL
specification as a violation condition, and a violation condition is a pattern: the compiled
select is the union of them, one branch per constraint, each branch carrying the target so
that a `FILTER` inside it can see `?this` (a BIND or a FILTER inside a UNION branch cannot see
a variable bound outside it — AGENTS.md carries the trap). Rows are the focus nodes that
violate, which is exactly what the kernel already reads as UNMET.

COVERAGE IS EXACTLY WHAT THE SHIPPED WANTS USE, and anything else REFUSES rather than
compiling to something quiet: a shape compiled to an empty pattern would read as met for
ever, which is this repository's signature way of being wrong. Held to the judge by parity
in `tests/test_violation.py`, the way the inference closure is held to pySHACL — two engines
reading one declaration is a disagreement this repository has closed once already.

The compiled text is COMPUTED and never stored (model-it-only-if-a-plan-would-branch-on-it:
anything the interpreter already knows is computed, never asserted). It carries no `GRAPH`
clause and no `$state`: the caller runs it with the world's graphs as the default graph —
`Store.query_over` — which is the same view the judge is handed as one flat text.
"""

from __future__ import annotations

import itertools
import re

import rdflib
from rdflib import RDF, Literal, URIRef
from rdflib.collection import Collection

from orexis_agent_progression.store import NAMESPACES, Raw, bind

#  Longest namespace first, so a prefix whose namespace extends another's wins.
_PREFIX_OF = dict(sorted(NAMESPACES.items(), key=lambda kv: -len(kv[1])))

SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")

#  What a property shape and a node shape may carry in SHACL's OWN namespace beside a
#  constraint this compiles. A predicate outside `sh:` is an annotation — a label, a
#  provenance link, sensing's `ssn:forProperty`, the kernel's `orexis:violationIs` — and
#  constrains nothing; a `sh:` predicate this does not list is a constraint it does not know,
#  and refuses.
_PROPERTY_ANNOTATIONS = {SH.path, SH.message, SH.severity, SH.name, SH.description, SH.order,
                         SH.group}
_NODE_ANNOTATIONS = {SH.targetNode, SH.targetClass, SH.targetSubjectsOf, SH.targetObjectsOf,
                     SH.property, SH.sparql, SH["not"],
                     SH.message, SH.severity, SH.name, SH.description, SH.deactivated}


def _is_shacl(p) -> bool:
    return str(p).startswith(str(SH))


_LOCAL = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def qname(iri) -> str:
    """The IRI as a prefixed name where the store declares the prefix and the local part is
    plain, else in full. Readability alone (#500): the store hands the engine the same
    dictionary, so the compiled text runs either way and reads the way its shape was written."""
    text = str(iri)
    for prefix, ns in _PREFIX_OF.items():
        if text.startswith(ns) and _LOCAL.match(text[len(ns):]):
            return f"{prefix}:{text[len(ns):]}"
    return f"<{text}>"


class Unsupported(ValueError):
    """A SHACL feature this compiler does not cover — named, so the shape can be rewritten
    or the compiler widened, and never so a want silently reads as met."""


def unmet_select(shapes: rdflib.Graph, shape) -> str:
    """The select whose rows are the focus nodes of `shape` that violate it, in `shapes`."""
    return _Compiler(shapes).select(shape)


def entered_select(shapes: rdflib.Graph, shape) -> str:
    """The select whose rows are the focus nodes that CONFORM to `shape` — the negative twin
    (#499). An aversion under `orexis:unmetWhen` is authored as the avoided state itself, so
    its want is unmet exactly where a focus node conforms; the two terms keep their polarity
    and the compiler reads either. Same fragment, same refusals, same parity."""
    return _Compiler(shapes).select(shape, entered=True)


class _Compiler:
    def __init__(self, g: rdflib.Graph):
        self.g = g
        self._vars = itertools.count()

    def fresh(self) -> str:
        return f"?v{next(self._vars)}"

    # --- the whole ----------------------------------------------------------------------------

    def select(self, shape, entered: bool = False) -> str:
        target = self.target(shape)
        alternatives = self.violations(shape, "?this")
        if not alternatives:
            raise Unsupported(f"{shape} states no constraint this compiler knows — a want "
                              "with nothing to violate would read as met for ever")
        if entered:
            return f"SELECT DISTINCT ?this WHERE {{ {target} {self.conforms(shape, '?this')} }}"
        branches = " UNION ".join(f"{{ {target} {alt} }}" for alt in alternatives)
        return f"SELECT DISTINCT ?this WHERE {{ {branches} }}"

    def target(self, shape) -> str:
        nodes = list(self.g.objects(shape, SH.targetNode))
        classes = list(self.g.objects(shape, SH.targetClass))
        subjects_of = list(self.g.objects(shape, SH.targetSubjectsOf))
        objects_of = list(self.g.objects(shape, SH.targetObjectsOf))
        if (shape, SH.target, None) in self.g:
            raise Unsupported(f"{shape}: sh:target (a SPARQL target) is not compiled")
        if not (nodes or classes or subjects_of or objects_of):
            raise Unsupported(f"{shape} targets nothing — whose state is it about?")
        parts = []
        if nodes:
            parts.append("VALUES ?this { " + " ".join(self.term(n) for n in nodes) + " }")
        for cls in classes:
            parts.append(f"?this a {self.term(cls)} .")
        for p in subjects_of:
            parts.append(f"?this {self.term(p)} {self.fresh()} .")
        for p in objects_of:
            parts.append(f"{self.fresh()} {self.term(p)} ?this .")
        return " ".join(parts)

    # --- a node shape's violations, each an alternative --------------------------------------

    def violations(self, shape, focus: str) -> list[str]:
        for p in self.g.predicates(shape):
            if _is_shacl(p) and p not in _NODE_ANNOTATIONS:
                raise Unsupported(f"{shape}: {p.n3()} on a node shape is not compiled")
        out = []
        for prop in self.g.objects(shape, SH.property):
            out.extend(self.property_violations(prop, focus))
        for constraint in self.g.objects(shape, SH.sparql):
            out.append(self.sparql_body(constraint, focus))
        for negated in self.g.objects(shape, SH["not"]):
            #  Violated exactly where the negated shape is CONFORMED to.
            out.append(self.conforms(negated, focus))
        return out

    def conforms(self, shape, focus: str) -> str:
        """`focus` conforms to `shape`: every violation alternative absent, as filters."""
        clauses = []
        for alt in self.violations(shape, focus):
            if alt.startswith("FILTER NOT EXISTS "):
                clauses.append("FILTER EXISTS " + alt[len("FILTER NOT EXISTS "):])
            else:
                clauses.append(f"FILTER NOT EXISTS {{ {alt} }}")
        return " ".join(clauses)

    def property_violations(self, prop, focus: str) -> list[str]:
        path = self.path(self.g.value(prop, SH.path))
        out = []
        for p, o in self.g.predicate_objects(prop):
            v = self.fresh()
            if p in _PROPERTY_ANNOTATIONS or not _is_shacl(p):
                continue
            elif p == SH.hasValue:
                out.append(f"FILTER NOT EXISTS {{ {focus} {path} {self.term(o)} }}")
            elif p == SH.minCount:
                if int(o) != 1:
                    raise Unsupported(f"{prop}: sh:minCount {o} — only 1 is compiled")
                out.append(f"FILTER NOT EXISTS {{ {focus} {path} {v} }}")
            elif p == SH.maxCount:
                if int(o) != 0:
                    raise Unsupported(f"{prop}: sh:maxCount {o} — only 0 is compiled")
                out.append(f"{focus} {path} {v} .")
            elif p == SH["class"]:
                out.append(f"{focus} {path} {v} . FILTER NOT EXISTS {{ {v} a {self.term(o)} }}")
            elif p == SH.equals:
                other = self.path(o)
                out.append(f"{focus} {path} {v} . FILTER NOT EXISTS {{ {focus} {other} {v} }}")
                out.append(f"{focus} {other} {v} . FILTER NOT EXISTS {{ {focus} {path} {v} }}")
            elif p in (SH.minExclusive, SH.maxExclusive, SH.minInclusive, SH.maxInclusive):
                op = {SH.minExclusive: ">", SH.maxExclusive: "<",
                      SH.minInclusive: ">=", SH.maxInclusive: "<="}[p]
                out.append(f"{focus} {path} {v} . FILTER(!({v} {op} {self.term(o)}))")
            elif p == SH.qualifiedValueShape:
                n_min = self.g.value(prop, SH.qualifiedMinCount)
                n_max = self.g.value(prop, SH.qualifiedMaxCount)
                inner = self.conforms(o, v)
                if n_min is not None:
                    if int(n_min) != 1:
                        raise Unsupported(f"{prop}: sh:qualifiedMinCount {n_min} — only 1")
                    out.append(f"FILTER NOT EXISTS {{ {focus} {path} {v} . {inner} }}")
                if n_max is not None:
                    if int(n_max) != 0:
                        raise Unsupported(f"{prop}: sh:qualifiedMaxCount {n_max} — only 0")
                    out.append(f"{focus} {path} {v} . {inner}")
                if n_min is None and n_max is None:
                    raise Unsupported(f"{prop}: a qualified value shape with no count")
            elif p in (SH.qualifiedMinCount, SH.qualifiedMaxCount):
                continue                         # read beside the shape they qualify
            else:
                raise Unsupported(f"{prop}: {p.n3()} is not a constraint this compiles")
        return out

    def sparql_body(self, constraint, focus: str) -> str:
        """A `sh:sparql` constraint's WHERE body, inlined so its filters see the focus.

        Inlined rather than embedded as a subquery: a subquery is evaluated on its own, so a
        constraint that only FILTERs — the freshness want is one — would leave `$this`
        unbound inside it and bind nothing. The body joins the target in the same group.
        """
        text = str(self.g.value(constraint, SH.select) or "")
        head, brace, rest = text.partition("{")
        if "SELECT" not in head.upper() or "WHERE" not in head.upper() or not brace:
            raise Unsupported(f"{constraint}: a sh:sparql constraint must be SELECT … WHERE {{ … }}")
        body = rest[:rest.rfind("}")]
        for forbidden in ("$PATH", "$value", "$currentShape", "$shapesGraph"):
            if forbidden in body:
                raise Unsupported(f"{constraint}: {forbidden} is not compiled")
        return bind(body, this=Raw(focus)).strip()

    # --- terms and paths ----------------------------------------------------------------------

    def term(self, node) -> str:
        if isinstance(node, URIRef):
            return qname(node)
        if isinstance(node, Literal):
            return node.n3()
        raise Unsupported(f"a blank node ({node}) cannot be named in a compiled select")

    def path(self, node) -> str:
        if node is None:
            raise Unsupported("a property shape with no sh:path")
        if isinstance(node, URIRef):
            return qname(node)
        if (node, RDF.first, None) in self.g:               # a sequence
            return "(" + "/".join(self.path(p) for p in Collection(self.g, node)) + ")"
        for pred, form in ((SH.inversePath, "^({})"), (SH.oneOrMorePath, "({})+"),
                           (SH.zeroOrMorePath, "({})*"), (SH.zeroOrOnePath, "({})?")):
            inner = self.g.value(node, pred)
            if inner is not None:
                return form.format(self.path(inner))
        alternatives = self.g.value(node, SH.alternativePath)
        if alternatives is not None:
            return "(" + "|".join(self.path(p) for p in Collection(self.g, alternatives)) + ")"
        raise Unsupported(f"a path this compiler does not know: {node}")
