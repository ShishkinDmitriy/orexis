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


# --- the kernel namespace, spelled out ----------------------------------------------------
#
# `store.PREFIXES` catches an undeclared PREFIX. It cannot catch the opposite mistake, which is
# what the namespace sweep found seven ways of making: a term named by its FULL IRI in the
# kernel namespace, when the package that declares it has a namespace of its own.
#
#     <{AG}bidsIn>                interpolated in the sovereign's tooling
#     AG + "Sensor"               concatenated
#     "http://example.org/agora#SoilMoisture"   a plain constant
#     term("slowSleepS")          the kernel builder, imported into a package or a test
#
# Every one compiles. Every one names something no ontology declares once the term moves, and a
# pattern with an unknown IRI does not raise — it matches nothing. `tests/test_isolation.py`
# built `bidsIn` this way from the moment market took `market:`, so the voucher half of a
# privacy test asserted nothing for four merged PRs while passing, and its own `assert private`
# guard did not fire because a second query kept the dict non-empty.
# The three forms that spell the kernel namespace outright, whatever the file.
_KERNEL_IRI = re.compile(
    r'(?:\{AG\}|AG \+ "|"http://example\.org/agora#)([A-Za-z][A-Za-z0-9]*)')
# And the fourth, which is only the kernel's when the KERNEL's builder is the one in scope. A
# package's own `terms.py` defines a `term()` into its own namespace and every capability
# imports that one — same call, different answer, which is precisely the confusion this sweep
# was about.
_BUILT = re.compile(r'(?<![.\w])term\("([A-Za-z][A-Za-z0-9]*)"\)')
_KERNEL_BUILDER = re.compile(r"from agent\.ontology import [^\n]*\bterm\b")

_ALL_TREES = _SOURCES + sorted(loader.REPO_ROOT.glob("tests/*.py"))

# Deliberately unauthored: `test_metrics` asks what happens when a block names a term nobody
# declares, so these two MUST NOT resolve. Listed rather than pattern-matched, because the
# point of the test is that they look exactly like real ones.
_NOT_A_TERM = {"NoSuchTermAnyoneAuthored", "noSuchTerm"}


def _kernel_terms() -> set[str]:
    """What `vocabulary/agora` actually declares, read rather than listed."""
    text = (loader.REPO_ROOT / "vocabulary/agora/ontology.ttl").read_text()
    return set(re.findall(r"^ag:([A-Za-z][A-Za-z0-9]*)\b", text, re.M))


def test_the_kernel_vocabulary_is_still_found():
    """The guard on the guard, again: an empty set would make the scan below vacuous."""
    assert len(_kernel_terms()) > 20, "vocabulary/agora declares almost nothing — has it moved?"


@pytest.mark.parametrize("path", _ALL_TREES, ids=lambda p: p.name)
def test_no_source_names_a_moved_term_in_the_kernel_namespace(path):
    """A full IRI in `ag:` must name something `vocabulary/agora` declares.

    Instances are exempt and are the reason this is a name check rather than a ban: a world's
    `ag:moisture_sensor_fern` is a thing, not a term, and lives in `ag:` correctly. So the rule
    is not "never spell out the kernel namespace" — it is that when you do, the local name has
    to be one the kernel actually has.
    """
    if path.name == "test_store.py":
        pytest.skip("quotes the offending forms as examples, which is what makes it readable")

    text = path.read_text()
    names = set(_KERNEL_IRI.findall(text))
    if _KERNEL_BUILDER.search(text):
        names |= set(_BUILT.findall(text))

    kernel, offenders = _kernel_terms(), []
    for name in names:
        if name in kernel or name in _NOT_A_TERM:
            continue
        # An INSTANCE is a single lowercase word or has an underscore — `ag:fern`,
        # `ag:moisture_sensor_fern`. A TERM is Capitalised or camelCase. That is a convention
        # rather than a rule, which is why the message says what to do if it guesses wrong.
        if "_" in name or name.islower():
            continue
        offenders.append(name)
    assert not offenders, (
        f"{path.name} names {sorted(offenders)} in the kernel namespace, and "
        "vocabulary/agora declares no such term — whichever package owns it has a namespace "
        "of its own, and this pattern will match nothing rather than fail"
    )
