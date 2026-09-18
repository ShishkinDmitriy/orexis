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

COVERAGE IS EXACTLY WHAT THE SHIPPED SHAPES USE — the wants' fragment, and since #548 the
packages' shapes about an agent and the law a world ratifies (`report_select`,
`report_selects`) — and anything else REFUSES rather than compiling to something quiet: a
shape compiled to an empty pattern would read as met for ever, which is this repository's
signature way of being wrong. Held to the judge by parity in `tests/test_violation.py` and
`tests/test_legality.py`, the way the inference closure is held to pySHACL — two engines
reading one declaration is a disagreement this repository has closed once already.

The compiled text is COMPUTED and never stored (model-it-only-if-a-plan-would-branch-on-it:
anything the interpreter already knows is computed, never asserted). It carries no `GRAPH`
clause and no `$state`: the caller runs it with the world's graphs as the default graph —
`Store.query_over` — which is the same view the judge is handed as one flat text.

PROGRESSION'S, since #514: a pure function over RDF with no search in it, and the keeper —
which may not import the layer above — compiles a held condition authored as a shape
(`progression:until`, `progression:untilNot`). Deliberation and the container import it downward.
"""

from __future__ import annotations

from orexis_agent_progression.ontology import PROGRESSION

import itertools
import re

import rdflib
from rdflib import RDF, Literal, URIRef
from rdflib.collection import Collection

from .store import NAMESPACES, Raw, bind

#  Longest namespace first, so a prefix whose namespace extends another's wins.
_PREFIX_OF = dict(sorted(NAMESPACES.items(), key=lambda kv: -len(kv[1])))

SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
OREXIS = rdflib.Namespace("http://example.org/orexis#")

#  What a property shape and a node shape may carry in SHACL's OWN namespace beside a
#  constraint this compiles. A predicate outside `sh:` is an annotation — a label, a
#  provenance link, sensing's `ssn:forProperty`, the kernel's `orexis:violationIs` — and
#  constrains nothing; a `sh:` predicate this does not list is a constraint it does not know,
#  and refuses.
_PROPERTY_ANNOTATIONS = {SH.path, SH.message, SH.severity, SH.name, SH.description, SH.order,
                         SH.group}
_NODE_ANNOTATIONS = {SH.targetNode, SH.targetClass, SH.targetSubjectsOf, SH.targetObjectsOf,
                     SH.target, SH.property, SH.sparql, SH["not"], SH["or"], SH.xone,
                     SH.message, SH.severity, SH.name, SH.description, SH.deactivated,
                     SH["class"], SH.datatype, SH.nodeKind, SH["in"], SH.hasValue,
                     SH.minExclusive, SH.maxExclusive, SH.minInclusive, SH.maxInclusive}

#  What a `sh:nodeKind` refuses, as the filter that finds the offending value — AT THE
#  BORDER'S SEMANTICS, not the specification's. A blank node crosses into the judge as an
#  IRI (`judge.crossed` skolemizes every one), so the gates never tell the two apart and
#  `sh:IRI` there means "not a literal". The compiled form agrees with the gates rather than
#  with the letter of SHACL, because agreeing with the gates is what makes a world the search
#  accepts a world boot accepts; the two kinds the border makes meaningless are refused.
_NODE_KIND_VIOLATED = {
    SH.IRI: "isLiteral({v})", SH.BlankNodeOrIRI: "isLiteral({v})",
    SH.Literal: "!isLiteral({v})", SH.BlankNodeOrLiteral: "isIRI({v}) || isBlank({v})",
}
#  Value constraints a NODE shape may carry about its focus itself, beside its properties.
_NODE_VALUE_CONSTRAINTS = {SH["class"], SH.datatype, SH.nodeKind, SH["in"], SH.hasValue,
                           SH.minExclusive, SH.maxExclusive, SH.minInclusive, SH.maxInclusive}


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


def report_select(shapes: rdflib.Graph, shape, focus_node=None) -> str | None:
    """The select whose rows are `shape`'s VIOLATIONS — `?this`, the constraint's index
    `?_constraint` within the shape, and the `?_offending` value where the constraint has
    one — restricted
    to `focus_node` when given (#548). This is the judge's report as rows: what the search
    reads off a world instead of crossing it into rudof. Only what the shape states at
    `sh:Violation` is compiled, a shape's default; a warning shows and refuses nothing, so a
    shape stating only warnings answers None, as does a deactivated one."""
    return _Compiler(shapes).report(shape, focus_node)


def report_selects(shapes: rdflib.Graph, focus_node=None) -> dict:
    """Every TARGETED shape in `shapes` that states something at `sh:Violation`, each as its
    own report select — {shape: select} — so a world is held to a whole shapes graph by one
    query per shape (#548). A shape with no target is not judged, as the judge does not
    judge it. ONE SELECT PER SHAPE, measured: the same branches as a single UNION of every
    shape cost 843 ms on `world/simulation` where the selects asked one by one cost 65, so
    the engine is handed small questions.
    """
    c = _Compiler(shapes)
    out = {}
    for shape in set(shapes.subjects(RDF.type, SH.NodeShape)):
        if not c.targeted(shape):
            continue
        branches = c.report_branches(shape, focus_node)
        if branches:
            out[shape] = ("SELECT DISTINCT ?this ?_constraint ?_offending WHERE { "
                          + " UNION ".join(branches) + " }")
    return out


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

    def report(self, shape, focus_node=None) -> str | None:
        branches = self.report_branches(shape, focus_node)
        if not branches:
            return None
        #  `?_about` is unbound on a row whose constraint's block says nothing, and that is the
        #  reader's signal to fall back to the desire's own `orexis:about`.
        return "SELECT DISTINCT ?this ?_constraint ?_offending ?_about WHERE { " + " UNION ".join(branches) + " }"

    def targeted(self, shape) -> bool:
        return any((shape, t, None) in self.g for t in (
            SH.targetNode, SH.targetClass, SH.targetSubjectsOf, SH.targetObjectsOf, SH.target))

    def report_branches(self, shape, focus_node=None) -> list[str]:
        """One UNION branch per violation alternative of `shape` at `sh:Violation`, each
        carrying the target, the constraint's index and the offending value."""
        if self.g.value(shape, SH.deactivated) == Literal(True):
            return []
        target = self.target(shape)
        if focus_node is not None:
            target = f"VALUES ?this {{ {self.term(focus_node)} }} " + target
        severity = self.g.value(shape, SH.severity) or SH.Violation
        branches = []
        for k, (text, value, about) in enumerate(self.alternatives(shape, "?this", severity, SH.Violation)):
            #  Projected under UNDERSCORED names, reserved for the report — an authored body
            #  says `?shape`, and one that says `?_shape` is refused: a BIND onto a variable
            #  the branch already binds is a parse error the engine reports, never a quiet
            #  wrong row.
            for projected in ("?_constraint", "?_offending", "?_about"):
                if projected in text or projected in target:
                    raise Unsupported(f"{shape}: a select body binds {projected}, which the report projects")
            bound = f" BIND({value} AS ?_offending)" if value else ""
            #  WHICH PROPERTY, where the block says: the row can then name what is in trouble.
            #  `sh:this` is the focus node itself, for a desire whose instances are its rows.
            if about == SH.this:
                bound += " BIND(?this AS ?_about)"
            elif about is not None:
                bound += f" BIND({self.term(about)} AS ?_about)"
            branches.append(f"{{ {target} {text} BIND({k} AS ?_constraint){bound} }}")
        return branches

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
        sparql = []
        for t in self.g.objects(shape, SH.target):
            if (t, RDF.type, SH.SPARQLTarget) not in self.g:
                raise Unsupported(f"{shape}: a sh:target that is not a sh:SPARQLTarget")
            #  The target select's body, inlined as a group so its patterns and its filters
            #  see one another; `?this` is what it projects and what the branch binds.
            sparql.append("{ " + self.body_of(self.g.value(t, SH.select), t, "?this") + " }")
        if not (nodes or classes or subjects_of or objects_of or sparql):
            raise Unsupported(f"{shape} targets nothing — whose state is it about?")
        parts = sparql
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
        return [text for text, _, _ in self.alternatives(shape, focus)]

    def alternatives(self, shape, focus: str, severity=None, only=None) -> list[tuple]:
        """Each way `focus` can violate `shape`, as (pattern, the offending value's variable
        or None, what the constraint is ABOUT or None).

        THE THIRD MEMBER is `orexis:about` stated on the property block — the one kernel word a
        block may carry beside SHACL's own. A desire universal over several properties states it
        per block, and a violation row can then say WHICH property is in trouble, which is what
        lets a want be minted about that and not about everything the desire covers
        (one-road-derives-every-want). A block that states none yields None, and a reader falls
        back to the desire's own `orexis:about`. With `only`, an alternative whose severity is not `only` is left out; a
        conformance check passes neither.

        WHOSE SEVERITY, measured against the judge (#548) rather than read off the
        specification: a property shape's is its own, defaulting to `sh:Violation`, and the
        node shape's never reaches it; a `sh:sparql` constraint's is the NODE shape's, and
        one stated on the constraint itself is ignored; `sh:or`, `sh:not`, `sh:xone` and a
        value constraint on the node itself are the node shape's. The shipped shapes state
        it that way already — down on the property for a declarative constraint, up on the
        node for a SPARQL one — and the one that states it on a constraint node also
        states it on the node, so nothing shipped reads differently under either rule.
        """
        if (shape, SH.path, None) in self.g:
            #  A PROPERTY shape where a node shape was expected — a member of `sh:or`, which
            #  SHACL allows and the public-graph shape uses. Its constraints are its own.
            return self._about_each(shape, self.property_violations(shape, focus))
        for p in self.g.predicates(shape):
            if _is_shacl(p) and p not in _NODE_ANNOTATIONS:
                raise Unsupported(f"{shape}: {p.n3()} on a node shape is not compiled")
        out = []
        own = only is None or severity == only
        for prop in self.g.objects(shape, SH.property):
            if only is None or (self.g.value(prop, SH.severity) or SH.Violation) == only:
                out.extend(self._about_each(prop, self.property_violations(prop, focus)))
        if own:
            for constraint in self.g.objects(shape, SH.sparql):
                #  A SPARQL constraint may say what it is about, as a property block may — the
                #  ledger's desire says each of its is about the debt itself, `sh:this`.
                out.append((self.sparql_body(constraint, focus), None,
                            self.g.value(constraint, OREXIS.about)))
            out.extend((t, v, None) for t, v in self.value_violations(shape, focus))
            for negated in self.g.objects(shape, SH["not"]):
                #  Violated exactly where the negated shape is CONFORMED to.
                out.append((self.conforms(negated, focus), None, None))
            for members in self.g.objects(shape, SH["or"]):
                #  Violated where NO member is conformed to: every member violated.
                out.append((" ".join(f"FILTER({self.violated(m, focus)})"
                                     for m in Collection(self.g, members)), None, None))
            for members in self.g.objects(shape, SH.xone):
                shapes = list(Collection(self.g, members))
                if len(shapes) != 2:
                    raise Unsupported(f"{shape}: sh:xone over {len(shapes)} shapes — only two")
                a, b = (self.violated(m, focus) for m in shapes)
                #  Violated where both or neither conform: exactly one is what xone means.
                out.append((f"FILTER(({a} && {b}) || (!({a}) && !({b})))", None, None))
        return out

    def value_violations(self, shape, focus: str) -> list[tuple[str, str | None]]:
        """The constraints a node shape states about its focus itself — a qualified value
        shape's inner `[ sh:class X ]` is the shipped form — as filters on `focus`."""
        out = []
        for p, o in self.g.predicate_objects(shape):
            if p not in _NODE_VALUE_CONSTRAINTS:
                continue
            if p == SH["class"]:
                out.append((f"FILTER NOT EXISTS {{ {focus} a {self.term(o)} }}", None))
            elif p == SH.datatype:
                out.append((f"FILTER(!isLiteral({focus}) || datatype({focus}) != {self.term(o)})", None))
            elif p == SH.nodeKind:
                if o not in _NODE_KIND_VIOLATED:
                    raise Unsupported(f"{shape}: sh:nodeKind {o} means nothing at the border")
                out.append((f"FILTER({_NODE_KIND_VIOLATED[o].format(v=focus)})", None))
            elif p == SH["in"]:
                allowed = ", ".join(self.term(m) for m in Collection(self.g, o))
                out.append((f"FILTER({focus} NOT IN ({allowed}))", None))
            elif p == SH.hasValue:
                out.append((f"FILTER({focus} != {self.term(o)})", None))
            else:
                op = {SH.minExclusive: ">", SH.maxExclusive: "<",
                      SH.minInclusive: ">=", SH.maxInclusive: "<="}[p]
                out.append((f"FILTER(!({focus} {op} {self.term(o)}))", None))
        return out

    def violated(self, shape, focus: str) -> str:
        """`focus` violates `shape`, as one boolean expression — some alternative holds.
        EXISTS inside a FILTER is evaluated with the current solution substituted, so it
        sees `focus` where a UNION branch would not (AGENTS.md carries that trap)."""
        alternatives = self.violations(shape, focus)
        if not alternatives:
            raise Unsupported(f"{shape} states no constraint this compiler knows")
        return "(" + " || ".join(f"EXISTS {{ {alt} }}" for alt in alternatives) + ")"

    def conforms(self, shape, focus: str) -> str:
        """`focus` conforms to `shape`: every violation alternative absent, as filters."""
        clauses = []
        for alt in self.violations(shape, focus):
            if alt.startswith("FILTER NOT EXISTS "):
                clauses.append("FILTER EXISTS " + alt[len("FILTER NOT EXISTS "):])
            else:
                clauses.append(f"FILTER NOT EXISTS {{ {alt} }}")
        return " ".join(clauses)

    def _about_each(self, block, alternatives) -> list[tuple]:
        """Every alternative of one property block, tagged with what the block says it is
        about — `orexis:about` on the block, or None. `orexis:about sh:this` means the focus
        node ITSELF: a desire universal over instances — every debt of mine — says each
        constraint is about the instance it failed on, and the row carries that instance."""
        about = self.g.value(block, OREXIS.about)
        return [(text, value, about) for text, value in alternatives]

    def property_violations(self, prop, focus: str) -> list[tuple[str, str | None]]:
        path = self.path(self.g.value(prop, SH.path))
        out = []
        for p, o in self.g.predicate_objects(prop):
            v = self.fresh()
            if p in _PROPERTY_ANNOTATIONS or not _is_shacl(p):
                continue
            elif p == SH.hasValue:
                out.append((f"FILTER NOT EXISTS {{ {focus} {path} {self.term(o)} }}", None))
            elif p == SH.minCount:
                #  Fewer than n values: no n distinct ones exist. A count has no offending value.
                out.append((f"FILTER NOT EXISTS {{ {self.distinct(focus, path, int(o))} }}", None))
            elif p == SH.maxCount:
                out.append((self.distinct(focus, path, int(o) + 1), None))
            elif p == SH["class"]:
                out.append((f"{focus} {path} {v} . FILTER NOT EXISTS {{ {v} a {self.term(o)} }}", v))
            elif p == SH.datatype:
                out.append((f"{focus} {path} {v} . "
                            f"FILTER(!isLiteral({v}) || datatype({v}) != {self.term(o)})", v))
            elif p == SH.nodeKind:
                if o not in _NODE_KIND_VIOLATED:
                    raise Unsupported(f"{prop}: sh:nodeKind {o} means nothing at the border")
                out.append((f"{focus} {path} {v} . FILTER({_NODE_KIND_VIOLATED[o].format(v=v)})", v))
            elif p == SH["in"]:
                allowed = ", ".join(self.term(m) for m in Collection(self.g, o))
                out.append((f"{focus} {path} {v} . FILTER({v} NOT IN ({allowed}))", v))
            elif p == SH.node:
                #  A value that does not conform to the node shape.
                out.append((f"{focus} {path} {v} . FILTER({self.violated(o, v)})", v))
            elif p == SH.equals:
                other = self.path(o)
                out.append((f"{focus} {path} {v} . FILTER NOT EXISTS {{ {focus} {other} {v} }}", v))
                out.append((f"{focus} {other} {v} . FILTER NOT EXISTS {{ {focus} {path} {v} }}", v))
            elif p in (SH.lessThan, SH.lessThanOrEquals):
                w, op = self.fresh(), {SH.lessThan: "<", SH.lessThanOrEquals: "<="}[p]
                out.append((f"{focus} {path} {v} . {focus} {self.path(o)} {w} . "
                            f"FILTER(!({v} {op} {w}))", v))
            elif p in (SH.minExclusive, SH.maxExclusive, SH.minInclusive, SH.maxInclusive):
                op = {SH.minExclusive: ">", SH.maxExclusive: "<",
                      SH.minInclusive: ">=", SH.maxInclusive: "<="}[p]
                out.append((f"{focus} {path} {v} . FILTER(!({v} {op} {self.term(o)}))", v))
            elif p == SH.qualifiedValueShape:
                n_min = self.g.value(prop, SH.qualifiedMinCount)
                n_max = self.g.value(prop, SH.qualifiedMaxCount)
                if n_min is not None:
                    #  Fewer than n conforming values: no n distinct ones each conform.
                    out.append((f"FILTER NOT EXISTS {{ "
                                f"{self.distinct(focus, path, int(n_min), conforming=o)} }}", None))
                if n_max is not None:
                    if int(n_max) != 0:
                        raise Unsupported(f"{prop}: sh:qualifiedMaxCount {n_max} — only 0")
                    out.append((f"{focus} {path} {v} . {self.conforms(o, v)}", v))
                if n_min is None and n_max is None:
                    raise Unsupported(f"{prop}: a qualified value shape with no count")
            elif p in (SH.qualifiedMinCount, SH.qualifiedMaxCount):
                continue                         # read beside the shape they qualify
            else:
                raise Unsupported(f"{prop}: {p.n3()} is not a constraint this compiles")
        return out

    def distinct(self, focus: str, path: str, n: int, conforming=None) -> str:
        """`n` pairwise-distinct values of `path` at `focus`, each conforming to
        `conforming` when one is given — the pattern a count constraint is made of."""
        if n < 1:
            raise Unsupported(f"a count of {n} values is not a constraint")
        vs = [self.fresh() for _ in range(n)]
        parts = [f"{focus} {path} {v} ." for v in vs]
        if conforming is not None:
            parts += [self.conforms(conforming, v) for v in vs]
        parts += [f"FILTER({a} != {b})" for a, b in itertools.combinations(vs, 2)]
        return " ".join(parts)

    def sparql_body(self, constraint, focus: str) -> str:
        """A `sh:sparql` constraint's WHERE body, inlined so its filters see the focus.

        Inlined rather than embedded as a subquery: a subquery is evaluated on its own, so a
        constraint that only FILTERs — the freshness want is one — would leave `$this`
        unbound inside it and bind nothing. The body joins the target in the same group.
        """
        return self.body_of(self.g.value(constraint, SH.select), constraint, focus)

    def body_of(self, text, node, focus: str) -> str:
        """The WHERE body of a `SELECT … WHERE { … }` text, `$this` and `?this` both bound to
        `focus` — a constraint's or a target's, which project it either way."""
        text = str(text or "")
        head, brace, rest = text.partition("{")
        if "SELECT" not in head.upper() or "WHERE" not in head.upper() or not brace:
            raise Unsupported(f"{node}: a select must be SELECT … WHERE {{ … }}")
        body = rest[:rest.rfind("}")]
        for forbidden in ("$PATH", "$value", "$currentShape", "$shapesGraph"):
            if forbidden in body:
                raise Unsupported(f"{node}: {forbidden} is not compiled")
        return re.sub(r"\?this\b", focus, bind(body, this=Raw(focus))).strip()

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
