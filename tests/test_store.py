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


def test_a_review_rule_leans_on_the_stores_prefixes_like_any_other_query():
    """The opposite rule to the one below, and the difference is who sends it.

    A derivation rule is a standalone update applied to the store, so it carries its own
    prefixes. A review rule goes through `store.query`, which prepends `PREFIXES` — so declaring
    them again is a duplicate-prefix error, and using one that is not declared fails exactly the
    way a hand-written query would. Same trap, other side.
    """
    found = loader.review_rules()
    assert found, "no review.rq found — the glob has gone stale and this guard is checking nothing"
    for path in found:
        text = path.read_text()
        assert "PREFIX " not in text.upper(), (
            f"{path.name} declares its own prefixes, but store.query prepends them")
        used = {m.group(1) for m in _PREFIXED.finditer(text)}
        undeclared = used - store.DECLARED - {"http", "https", "urn"}
        assert not undeclared, (
            f"{path.name} uses {sorted(undeclared)}, which store.PREFIXES does not declare")


def test_the_prefixes_a_derivation_rule_needs_are_carried_by_the_rule():
    """Rules are standalone updates, so they declare their own — and must."""
    for path in loader.rule_files():
        text = path.read_text()
        used = {m.group(1) for m in _PREFIXED.finditer(text)}
        declared = {m.group(1) for m in re.finditer(r"PREFIX\s+([\w.-]*):", text)}
        assert not (used - declared - {"http", "https"}), (
            f"{path} uses a prefix it does not declare — it is sent as its own update"
        )


# --- the assembly itself ---------------------------------------------------------------------
#
# `store.PREFIXES` is no longer a list somebody maintains: the project-internal half is read off
# the ontologies that declare the terms. Everything above tests what a query may SAY; these test
# that the set it is held to is still the set the packages actually declare.

def test_every_package_namespace_reaches_the_prefixes_a_query_is_sent_with():
    """The guard on the assembly. If the collection silently returned nothing, every test above
    would still pass — they check that queries use only DECLARED prefixes, and an empty set with
    an empty codebase is vacuously fine. What would break is production, where `market:` is in
    the query text and no engine has heard of it.

    So this asserts the direction that cannot fail safely: every namespace a package declares is
    one a query may use.
    """
    found = loader.prefixes()
    assert found, "no project-internal namespaces found — the ontology glob has gone stale"
    assert "ag" in found, "the base vocabulary's own namespace is missing from the assembly"
    missing = set(found) - store.DECLARED
    assert not missing, (
        f"{sorted(missing)} are declared by a package's ontology.ttl but are not in "
        "store.PREFIXES — a query naming one would 400 against Fuseki"
    )


def test_a_prefix_meaning_two_things_is_refused(tmp_path, monkeypatch):
    """One label, one namespace. Two packages binding `market:` to different IRIs is the
    quietest bug available — both spellings are valid SPARQL, so one package's query would
    silently read the other's terms and no engine could tell anyone.
    """
    a, b = tmp_path / "a.ttl", tmp_path / "b.ttl"
    a.write_text("@prefix dup: <http://example.org/agora/one#> .\n")
    b.write_text("@prefix dup: <http://example.org/agora/two#> .\n")
    monkeypatch.setattr(loader, "ontology_files", lambda: (a, b))
    loader.prefixes.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="One label, one namespace"):
            loader.prefixes()
    finally:
        loader.prefixes.cache_clear()


def test_an_external_vocabulary_is_not_a_packages_to_move(monkeypatch):
    """`rdfs:` and friends stay in the kernel. They are standardised and stable, and a package
    that could rebind one could make `rdfs:subClassOf` mean whatever it liked — which is exactly
    the walk `agent/inference.py` materialises and every shape leans on.
    """
    assert {"rdfs", "owl", "xsd", "sosa", "prov", "rdf"} <= store.DECLARED
    assert not {"rdfs", "owl", "xsd", "sosa", "prov", "rdf"} & set(loader.prefixes())
