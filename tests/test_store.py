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

from orexis_progression import store

from assembly import loader

# `?s ag:foo ?o` — a prefixed name in a query. Deliberately loose; false positives are
# filtered by requiring the prefix to look like one, and a false positive here is a
# prefix somebody should have declared anyway.
_PREFIXED = re.compile(r"(?<![\w:<#/-])([a-zA-Z][\w.-]*):[a-zA-Z_]")

# A string literal is only interesting if it is SPARQL at all.
_KEYWORDS = ("SELECT ", "INSERT ", "DELETE ", "CONSTRUCT ", "ASK ")

# Every tree that may contain a SPARQL query, as a NAMED group. Twice now, moving files has
# silently emptied one of these globs and taken cases off this guard without failing anything:
# once when the onboarding tools left the orexis package, and again when the repo went flat.
# A guard that quietly stops guarding is worse than none, so each group is asserted non-empty
# below rather than trusted.
_GROUPS = {
    # agent/ is recursive: it carries capabilities/ and transports/ as subpackages now, so
    # their queries are swept up with it rather than needing globs of their own.
    # `packages/` as its own group. The kernel's rglob used to reach capability Python because
    # capabilities were subpackages of `agent`; after the move it still matched plenty of files,
    # so the non-empty guard stayed green while every capability's SPARQL silently left the scan.
    # PARTITIONED from `loader.sources()`, not globbed. The two names stay, because a group that
    # goes empty should say WHICH tree moved — but the union is the loader's, so a tree nobody
    # here has heard of is covered rather than silently outside both globs.
    "agent": [p for p in loader.sources("*.py") if "packages" not in p.parts],
    "packages": [p for p in loader.sources("*.py") if "packages" in p.parts],
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
    a.write_text("@prefix dup: <http://example.org/orexis/one#> .\n")
    b.write_text("@prefix dup: <http://example.org/orexis/two#> .\n")
    monkeypatch.setattr(loader, "ontology_files", lambda: (a, b))
    loader.prefixes.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="One label, one namespace"):
            loader.prefixes()
    finally:
        loader.prefixes.cache_clear()


def test_the_kernels_own_vocabularies_are_its_own_and_the_rest_are_discovered(monkeypatch):
    """`rdfs:` and its five companions stay hard-coded: standardised, stable, and the language
    the kernel's own structure is written in — a package that could rebind one could make
    `rdfs:subClassOf` mean whatever it liked, which is exactly the walk `agent/inference.py`
    materialises. Everything else external — `sosa:` first of all — is READ off whichever
    ontology declares it (#378): the kernel speaks no reading, so it does not declare the
    vocabulary readings are written in; sensing does, and the label reaches a query that way.
    """
    assert {"rdf", "rdfs", "owl", "xsd", "sh", "prov"} <= set(store._KERNEL)
    assert not set(store._KERNEL) & set(loader.prefixes())
    assert "sosa" not in store._KERNEL
    assert {"sosa", "ssn-system", "unit", "schema"} <= set(loader.external_prefixes())
    assert {"sosa", "ssn-system", "unit", "schema", "rdf"} <= store.DECLARED


def test_one_external_label_bound_two_ways_is_refused(tmp_path, monkeypatch):
    """The whole of the ownership argument, mechanised: a package cannot rebind `unit:` past
    this, so the kernel need not hold the label to keep it honest."""
    a = tmp_path / "a.ttl"; b = tmp_path / "b.ttl"
    a.write_text("@prefix unit: <http://qudt.org/vocab/unit/> .\n")
    b.write_text("@prefix unit: <http://example.com/not-qudt/> .\n")
    monkeypatch.setattr(loader, "ontology_files", lambda: (a, b))
    loader.external_prefixes.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="One label, one namespace"):
            loader.external_prefixes()
    finally:
        loader.external_prefixes.cache_clear()


# --- the kernel namespace, spelled out ----------------------------------------------------
#
# `store.PREFIXES` catches an undeclared PREFIX. It cannot catch the opposite mistake, which is
# what the namespace sweep found seven ways of making: a term named by its FULL IRI in the
# kernel namespace, when the package that declares it has a namespace of its own.
#
#     <{AG}bidsIn>                interpolated in the sovereign's tooling
#     AG + "Sensor"               concatenated
#     "http://example.org/orexis#SoilMoisture"   a plain constant
#     term("slowSleepS")          the kernel builder, imported into a package or a test
#
# Every one compiles. Every one names something no ontology declares once the term moves, and a
# pattern with an unknown IRI does not raise — it matches nothing. `tests/test_isolation.py`
# built `bidsIn` this way from the moment market took `market:`, so the claim half of a
# privacy test asserted nothing for four merged PRs while passing, and its own `assert private`
# guard did not fire because a second query kept the dict non-empty.
# The three forms that spell the kernel namespace outright, whatever the file.
_KERNEL_IRI = re.compile(
    r'(?:\{AG\}|AG \+ "|"http://example\.org/orexis#)([A-Za-z][A-Za-z0-9]*)')
# And the fourth, which is only the kernel's when the KERNEL's builder is the one in scope. A
# package's own `terms.py` defines a `term()` into its own namespace and every capability
# imports that one — same call, different answer, which is precisely the confusion this sweep
# was about.
_BUILT = re.compile(r'(?<![.\w])term\("([A-Za-z][A-Za-z0-9]*)"\)')
_KERNEL_BUILDER = re.compile(r"from orexis_progression\.ontology import [^\n]*\bterm\b")

_ALL_TREES = _SOURCES + sorted(loader.REPO_ROOT.glob("tests/*.py"))

# Deliberately unauthored: `test_metrics` asks what happens when a block names a term nobody
# declares, so these two MUST NOT resolve. Listed rather than pattern-matched, because the
# point of the test is that they look exactly like real ones.
_NOT_A_TERM = {"NoSuchTermAnyoneAuthored", "noSuchTerm"}

# The two files where naming a moved term IS the subject. Exempt by name and with a reason
# each, rather than by a pattern: an exemption that could be met accidentally is a hole, and
# the whole value of this guard is that a moved term cannot be spelled the old way by mistake.
_QUOTES_THE_OLD_SPELLINGS = {
    "test_store.py":
        "quotes the offending forms as examples, which is what makes it readable",
    "vocabulary.py":
        "IS a table of moves, and a move names where a term CAME FROM — a retired kernel word "
        "on the left of every row. A guard that refused those would refuse the one file whose "
        "job is to remember them",
    "test_vocabulary.py":
        "IS the old spellings — it authors a belief base the way the code wrote them before "
        "the sweep, then opens it with the code that came after. A fixture generated from the "
        "current vocabulary would move whenever the vocabulary did and stop being the old world",
}


_AG = "http://example.org/orexis#"


def _kernel_terms() -> set[str]:
    """What the kernel actually declares — PARSED, not grepped.

    Asked of the loader rather than spelled as a path: the kernel's vocabulary has moved once
    already (`packages/core/orexis/` -> `agent/`), and a hardcoded path is how a guard like this
    one goes quiet — it would read an empty file, declare nothing, and pass every case below.

    And parsed rather than pattern-matched, which is the other half and was learnt the hard way.
    This read `^ag:(\w+)` off the file's TEXT, so a block of Turtle sitting INSIDE an
    `rdfs:comment` literal counted as declarations: the lines begin at column zero and look
    exactly right. That is not hypothetical — five terms were inserted into the middle of
    `ag:Intention`'s comment, the file parsed, the suite went green, and the terms were prose.
    A reader that greps cannot tell a declaration from a description of one, which is the same
    objection AGENTS.md already records against the vendored OKF check.
    """
    import rdflib

    g = rdflib.Graph()
    g.parse(loader.KERNEL.file(loader.ONTOLOGY), format="turtle")
    return {str(s)[len(_AG):] for s in g.subjects() if str(s).startswith(_AG)}


def test_the_vocabulary_declares_what_it_appears_to_declare():
    """Every `ag:Term` at the start of a line is a term the PARSER sees too.

    The specific shape of the bug above, named so it cannot come back quietly: Turtle nested in
    a literal is invisible to rdflib and indistinguishable to a regex. Anything the text offers
    as a declaration must survive parsing, or it is documentation wearing a declaration's
    clothes.
    """
    text = loader.KERNEL.file(loader.ONTOLOGY).read_text()
    looks_declared = set(re.findall(r"^ag:([A-Za-z][A-Za-z0-9]*)\b", text, re.M))
    really_declared = _kernel_terms()
    assert looks_declared, "the declaration pattern stopped matching — this guard is vacuous"
    swallowed = sorted(looks_declared - really_declared)
    assert not swallowed, (
        f"{swallowed} are written as declarations but the parser does not see them — almost "
        "certainly inside an rdfs:comment literal, where Turtle is just text"
    )


def test_the_kernel_vocabulary_is_still_found():
    """The guard on the guard, again: an empty set would make the scan below vacuous."""
    assert len(_kernel_terms()) > 20, "the kernel declares almost nothing — has it moved?"


@pytest.mark.parametrize("path", _ALL_TREES, ids=lambda p: p.name)
def test_no_source_names_a_moved_term_in_the_kernel_namespace(path):
    """A full IRI in `ag:` must name something the kernel declares.

    Instances are exempt and are the reason this is a name check rather than a ban: a world's
    `<http://example.org/orexis/world/simulation#moisture_sensor_fern>` is a thing, not a term, and lives in `ag:` correctly. So the rule
    is not "never spell out the kernel namespace" — it is that when you do, the local name has
    to be one the kernel actually has.
    """
    if (why := _QUOTES_THE_OLD_SPELLINGS.get(path.name)):
        pytest.skip(why)

    text = path.read_text()
    names = set(_KERNEL_IRI.findall(text))
    if _KERNEL_BUILDER.search(text):
        names |= set(_BUILT.findall(text))

    kernel, offenders = _kernel_terms(), []
    for name in names:
        if name in kernel or name in _NOT_A_TERM:
            continue
        # An INSTANCE is a single lowercase word or has an underscore — `<http://example.org/orexis/world/simulation#fern>`,
        # `<http://example.org/orexis/world/simulation#moisture_sensor_fern>`. A TERM is Capitalised or camelCase. That is a convention
        # rather than a rule, which is why the message says what to do if it guesses wrong.
        if "_" in name or name.islower():
            continue
        offenders.append(name)
    assert not offenders, (
        f"{path.name} names {sorted(offenders)} in the kernel namespace, and "
        "the kernel declares no such term — whichever package owns it has a namespace "
        "of its own, and this pattern will match nothing rather than fail"
    )


def test_an_ontology_gives_its_own_terms_the_default_prefix():
    """#179: inside an ontology, an unprefixed term is the file's own and a prefixed one is
    borrowed — which is the more useful thing for a prefix to say than restating the file's
    identity on every line. Two declarations per file, and both are load-bearing: the empty
    prefix carries the convention, and the NAMED one is what `loader.prefixes()` discovers
    (its regex requires a label), so a query can still say `bme280:` for a namespace the
    store never listed. Checked for every ontology that declares itself, so the next package
    follows by failing until it does."""
    import re

    import rdflib

    from assembly import loader

    checked = 0
    for path in loader.ontology_files():
        text = path.read_text()
        g = rdflib.Graph()
        g.parse(data=text, format="turtle")
        onts = list(g.subjects(rdflib.RDF.type, rdflib.OWL.Ontology))
        if len(onts) != 1:
            continue
        if str(onts[0]) == "http://example.org/orexis/core":
            # The kernel is the deliberate exception: ag: is the one namespace every world
            # and every package speaks, so 'unprefixed means mine' would be a false signal —
            # and the kernel-term census two tests up reads its spellings as written.
            continue
        own = re.search(r"^@prefix : <([^>]+)>", text, re.M)
        assert own, f"{path} declares no default prefix for its own namespace"
        assert re.search(
            rf"^@prefix [A-Za-z][\w.-]*:\s+<{re.escape(own.group(1))}>", text, re.M), (
            f"{path} must keep a NAMED declaration of <{own.group(1)}> beside the default "
            "one — the loader's discovery reads labels, and a query needs a name to use")
        checked += 1
    assert checked >= 20, f"only {checked} ontologies checked — the glob has gone quiet"


def test_an_availability_query_leans_on_the_stores_prefixes_like_a_review_rule():
    """Same contract, third file kind (#207): an action's `ag:available` goes through
    `store.query`, which prepends PREFIXES — declaring them again is a duplicate-prefix error,
    and using an undeclared one fails exactly as a hand-written query would. Non-empty asserted
    first, because a glob that quietly empties has taken cases off a guard twice already."""
    import rdflib

    found = loader.action_files()
    assert found, "no action files found — the glob has gone stale and this checks nothing"
    available = rdflib.URIRef("http://example.org/orexis#available")
    checked = 0
    for path in found:
        g = rdflib.Graph().parse(path)
        for action, text in g.subject_objects(available):
            text = str(text)
            checked += 1
            assert "PREFIX " not in text.upper(), (
                f"{path.name} {action} declares its own prefixes, but store.query prepends them")
            used = {m.group(1) for m in _PREFIXED.finditer(text)}
            undeclared = used - store.DECLARED - {"http", "https", "urn"}
            assert not undeclared, (
                f"{path.name} {action} uses {sorted(undeclared)}, which store.PREFIXES does not declare")
    assert checked >= 4, "the actions stopped carrying availability queries"


