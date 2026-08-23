"""The knowledge linker (#210) — no loaded package may reference a term nobody declares.

Dependencies between packages are deliberately not a manifest: Python imports are forbidden
(`lint-imports`), load order is eliminated (`$given`), and everything else is soft, by IRI.
Soft has a sharp edge — a query referencing a term nobody declares matches NOTHING, and an
empty result is not an error — so this is the link step: collect every project-namespace IRI
the loaded packages reference, subtract every one some loaded ontology declares, and refuse
the world naming what dangles. A check, never a resolver: it goes and finds nothing, on
purpose — the design's answer to "which packages does X need" stays "the terms it names",
made checkable instead of hopeful.

What is scanned, and what is tolerated, stated rather than implied:
- `.ttl` (package + firmware ontologies, shapes): every IRI in any position, plus full IRIs
  inside literals that look like SPARQL (a shape's sh:select is a reference like any other);
- `.rq` (review, affordances) and `.ru` (rules): full IRIs and prefixed names, the former
  resolved against the file's own PREFIX lines where it carries them (rules do) and against
  the loaded prefixes where it does not (store.query prepends them);
- `.py` under the package tree: complete project IRIs in string literals, and prefixed names
  inside triple-quoted blocks that look like SPARQL. A name built by concatenation
  (`NS + "Observe"`) is invisible to a static scan and stays the ontology-detector's problem;
- full-line comments are stripped first; a term in prose is not a reference;
- only project namespaces are checked (everything under the project root): sosa, ssn, schema
  and friends are other people's to declare.
"""

from __future__ import annotations

import re
from pathlib import Path

from agent import loader

# The project's namespace root. A constant in a LINTER, not in agent code: the check must
# say whose terms it polices, exactly as the prefix guard names store.PREFIXES.
PROJECT_ROOT_NS = "http://example.org/orexis"

_FULL_IRI = re.compile(r"<(" + re.escape(PROJECT_ROOT_NS) + r"[^>\s]*)>")
_BARE_IRI = re.compile(r'"(' + re.escape(PROJECT_ROOT_NS) + r'[^"\s<>]*)"')
_PREFIXED = re.compile(r"(?<![\w<:/])([A-Za-z][\w-]*):([A-Za-z_][\w.-]*)")
_PREFIX_LINE = re.compile(r"(?im)^\s*(?:@prefix|PREFIX)\s+([\w-]*):\s*<([^>]+)>")
# A keyword alone is not a query — module docstrings SAY "select" while describing one, and
# a prose mention of `water:hasTarget` in a docstring must not become a reference. A block is
# SPARQL when a keyword AND a brace appear; prose rarely opens a group.
_SPARQL_HINT = re.compile(r"\b(SELECT|INSERT|DELETE|CONSTRUCT|ASK)\b(?=[\s\S]*\{)", re.I)
_COMMENT_LINE = re.compile(r"(?m)^\s*#.*$")


def _strip_comments(text: str) -> str:
    return _COMMENT_LINE.sub("", text)


def declared_terms() -> set[str]:
    """Every project-namespace IRI some loaded ontology declares — i.e. says anything about.

    Subject position only: stating `water:capacityL rdfs:subPropertyOf market:lotCapacity`
    declares capacityL and merely references lotCapacity, which is the whole distinction
    this linker exists to check. Shapes files count as declarers too — a shape's own name is
    declared by being written, exactly as a term's is.
    """
    import rdflib

    declared: set[str] = set()
    for path in (*loader.ontology_files(), *loader.shapes_files()):
        g = rdflib.Graph()
        g.parse(path, format="turtle")
        for s in g.subjects():
            if isinstance(s, rdflib.URIRef) and str(s).startswith(PROJECT_ROOT_NS):
                declared.add(str(s))
    return declared


def _prefixes_of(text: str) -> dict[str, str]:
    own = {m.group(1): m.group(2) for m in _PREFIX_LINE.finditer(text)}
    return {**loader.prefixes(), **own} if own else dict(loader.prefixes())


def _resolve(text: str, prefixes: dict[str, str]) -> set[str]:
    """Full IRIs plus resolvable prefixed names, project namespace only."""
    refs = {m.group(1) for m in _FULL_IRI.finditer(text)}
    refs |= {m.group(1) for m in _BARE_IRI.finditer(text)}
    for m in _PREFIXED.finditer(text):
        ns = prefixes.get(m.group(1))
        if ns and ns.startswith(PROJECT_ROOT_NS):
            refs.add(ns + m.group(2))
    # Three tolerances, each a kind of non-reference: a bare namespace (a constant or a
    # prefix line), a minted-IRI base ("...#market." — a FUNCTION of an id, not a term; the
    # trailing dot is the tell), and the root itself.
    return {r for r in refs
            if r.startswith(PROJECT_ROOT_NS)
            and not r.endswith(("#", "/", "."))
            and r != PROJECT_ROOT_NS}


def referenced_terms() -> dict[str, set[str]]:
    """IRI -> the files that reference it, across everything the loader would load."""
    import rdflib

    refs: dict[str, set[str]] = {}

    def note(iri: str, path: Path) -> None:
        # repo-relative where possible; a package can live anywhere a test puts it
        try:
            shown = str(path.relative_to(loader.REPO_ROOT))
        except ValueError:
            shown = str(path)
        refs.setdefault(iri, set()).add(shown)

    for path in (*loader.ontology_files(), *loader.shapes_files()):
        g = rdflib.Graph()
        g.parse(path, format="turtle")
        for triple in g:
            for node in triple:
                if isinstance(node, rdflib.URIRef) and str(node).startswith(PROJECT_ROOT_NS):
                    note(str(node), path)
                if isinstance(node, rdflib.Literal) and _SPARQL_HINT.search(str(node)):
                    for iri in _resolve(str(node), dict(loader.prefixes())):
                        note(iri, path)

    for path in (*loader.rule_files(), *loader.review_rules(), *loader.affordance_files()):
        text = _strip_comments(path.read_text())
        for iri in _resolve(text, _prefixes_of(text)):
            note(iri, path)

    #  BOTH trees. This scanned `packages/` alone, which was true when every term-naming module
    #  lived there — and quietly stopped being true when the mind came into the kernel: the
    #  deliberator, the keeper, the menu and the planner all name IRIs, and none of them was
    #  ever read here. A dangling-term report that cannot see two thousand lines of terms is a
    #  report that says what it looked at, not what is true.
    #  ONE file is exempt, and it is the only one whose CONTENT is retired IRIs: the migration
    #  map records what a term used to be spelled, so every left-hand side in it is by
    #  definition declared nowhere. Scanning it reports the map's own purpose as six defects.
    #  Named rather than pattern-matched, because an exemption that can be met by accident is
    #  a hole in exactly the guard that caught this widening's first real find.
    RETIRED_BY_DESIGN = {"vocabulary.py"}

    for path in loader.sources("*.py"):
        if path.name in RETIRED_BY_DESIGN:
            continue
        text = path.read_text()
        for iri in _resolve(text, {}):
            note(iri, path)
        for block in re.findall(r'"""(.*?)"""', text, re.S):
            if _SPARQL_HINT.search(block):
                for iri in _resolve(_strip_comments(block), dict(loader.prefixes())):
                    note(iri, path)
    return refs


def dangling() -> dict[str, list[str]]:
    """What is referenced and declared nowhere — the linker's whole verdict."""
    declared = declared_terms()
    return {iri: sorted(paths) for iri, paths in sorted(referenced_terms().items())
            if iri not in declared}
