"""Every query must stand on its own prefixes.

This exists because of a bug that passed every test and failed in production: `provider()`
used `rdfs:subClassOf*`, which `store.PREFIXES` did not declare. rdflib pre-binds rdfs and
Fuseki does not, so the tests were green while every bidder 400'd on every offer.

The lesson is not "remember to add the prefix" — it is that the test harness was more
forgiving than the store, so a whole class of query bug could not be caught by testing
behaviour. This checks the text instead.
"""

import re
from pathlib import Path

import pytest

from agent import loader, store

# `?s ag:foo ?o` — a prefixed name in a query. Deliberately loose; false positives are
# filtered by requiring the prefix to look like one, and a false positive here is a
# prefix somebody should have declared anyway.
_PREFIXED = re.compile(r"(?<![\w:<#/-])([a-zA-Z][\w.-]*):[a-zA-Z_]")

# A string literal is only interesting if it is SPARQL at all.
_KEYWORDS = ("SELECT ", "INSERT ", "DELETE ", "CONSTRUCT ", "ASK ")

# Every tree that may contain a SPARQL query, as a NAMED group. Twice now, moving files has
# silently emptied one of these globs and taken cases off this guard without failing anything:
# once when the onboarding tools left the agora package, and again when the repo went flat.
# A guard that quietly stops guarding is worse than none, so each group is asserted non-empty
# below rather than trusted.
_GROUPS = {
    # agent/ is recursive: it carries capabilities/ and transports/ as subpackages now, so
    # their queries are swept up with it rather than needing globs of their own.
    "agent": sorted((Path(store.__file__).parent).rglob("*.py")),
    # the operator's half — `compose` and `mqtt` both carry SPARQL
    "onboarding": sorted(loader.REPO_ROOT.glob("onboarding/*.py")),
}

_SOURCES = sorted(p for group in _GROUPS.values() for p in group)


@pytest.mark.parametrize("group", sorted(_GROUPS))
def test_every_source_group_is_still_found(group):
    """The guard on the guard. If a tree moves and its glob goes stale, the parametrised test
    below simply runs fewer cases and passes — which is how this coverage was lost twice."""
    assert _GROUPS[group], (
        f"no Python found for the {group!r} group — its path has moved and "
        "test_queries_use_only_declared_prefixes is no longer checking it"
    )


def _queries(text: str) -> list[str]:
    """Triple-quoted blocks that look like SPARQL."""
    return [
        block for block in re.findall(r'"""(.*?)"""', text, re.S)
        if any(k in block.upper() for k in _KEYWORDS)
    ]


@pytest.mark.parametrize("path", _SOURCES, ids=lambda p: p.name)
def test_queries_use_only_declared_prefixes(path):
    for query in _queries(path.read_text()):
        if "PREFIX " in query.upper():
            continue  # a standalone update that carries its own, like a rules file
        used = {m.group(1) for m in _PREFIXED.finditer(query)}
        undeclared = used - store.DECLARED - {"http", "https", "urn"}
        assert not undeclared, (
            f"{path.name} sends a query using {sorted(undeclared)}, which store.PREFIXES "
            f"does not declare. rdflib would let this pass; Fuseki returns 400."
        )


def test_the_prefixes_a_derivation_rule_needs_are_carried_by_the_rule():
    """Rules are standalone updates, so they declare their own — and must."""
    for path in loader.rule_files():
        text = path.read_text()
        used = {m.group(1) for m in _PREFIXED.finditer(text)}
        declared = {m.group(1) for m in re.finditer(r"PREFIX\s+([\w.-]*):", text)}
        assert not (used - declared - {"http", "https"}), (
            f"{path} uses a prefix it does not declare — it is sent as its own update"
        )
