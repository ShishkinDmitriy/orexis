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

from agora import loader, store

# `?s ag:foo ?o` — a prefixed name in a query. Deliberately loose; false positives are
# filtered by requiring the prefix to look like one, and a false positive here is a
# prefix somebody should have declared anyway.
_PREFIXED = re.compile(r"(?<![\w:<#/-])([a-zA-Z][\w.-]*):[a-zA-Z_]")

# A string literal is only interesting if it is SPARQL at all.
_KEYWORDS = ("SELECT ", "INSERT ", "DELETE ", "CONSTRUCT ", "ASK ")

_SOURCES = sorted(
    [p for p in (Path(store.__file__).parent).rglob("*.py")]
    + [p for p in loader.REPO_ROOT.glob("capabilities/*/*.py")]
    + [p for p in loader.REPO_ROOT.glob("transports/*/*.py")]
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
