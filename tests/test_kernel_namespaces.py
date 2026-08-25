"""The kernel may not quietly learn another package's word — a ratchet, counted down to zero.

`lint-imports` holds the Python direction: `agent` may not import `packages`, and a capability
may not import another. Nothing held the RDF namespaces, so the kernel could — and does — spell
out `market#Raises` or `sensing#polls` as a string and speak vocabulary the trees below it own.
Every one of those compiles, and a pattern naming a term whose package has moved matches nothing
rather than failing, which is the quiet-failure family this repo has been bitten by four times.

Issue #334 counts the occurrences and says what removes each. This file pins them. It is a
RATCHET rather than a prohibition: the list below is what was there on the day it was written,
every entry annotated with why it is there and what will take it away, and the test fails two
ways — on an occurrence that is not on the list, and on a list entry that no longer occurs. The
second half matters as much as the first. `tests/test_store.py` records two globs that emptied
and took cases off a guard while it went on passing; an allowlist entry for a line somebody has
since deleted is the same defect wearing a different hat, so it is a failure with instructions
to delete the entry, and the list shrinks honestly as the work in #334 lands.

WHAT IS IN SCOPE, and why it is wider than the issue asked. #334 counted `agent/*.py`. This
scans every file kind the kernel actually ships that can carry an IRI — `*.py`, `*.rq`, `*.ru`
and `*.ttl` — because the objection is about what the kernel SAYS, and the kernel says most of
what it says in RDF. Widening it was not free: it found nine more references, in the kernel's
shapes, its ontology's prefix block and the desire derivation, which none of the issue's three
kinds describe. They sat on the list marked unclassified until #337 ruled on them; they are
kind 4 below, all nine of them debt like everything else here, ordered by how dangerous each one
is. The rule is `knowledge/decisions/the-kernel-names-no-package-word.md`, and it has no
exceptions: the kernel names no package's word, in RDF as in Python, because a package is
optional and the core depends on none of them.

BOTH FORMS, SINCE #378. The scan first counted the spelled-out IRI alone, and said so: a kernel
query saying `market:bidsIn` with the prefix declared for it was invisible, and `agent/world.py`
was full of them. The wiring left the kernel for the packages before this widened, so what the
prefixed scan found on the day it landed was four `mqtt:` terms in one query — the bus. It looks
for the prefixed form where a prefixed form MEANS something: a query string in Python (found by
the tokenizer, never a docstring or a comment), and a rule or a Turtle file with its comments
and its string literals stripped. Prose that names a package's word is not a dependency on it.

AND EVERY NAMESPACE OF OURS, not five families by hand. `loader.prefixes()` is what the ratchet
scans for, less `ag:`, so a transport's or a part's namespace in the kernel counts exactly as a
capability's does — which is what the rule says.

AND IT RESOLVES (#344). A count cannot see a term that is merely misspelled: a package renames a
word in its own namespace, the kernel goes on naming the old one, the pattern matches nothing
and no engine says so. So every term found here, in either form, must be a subject some ontology
declares — except the retired spellings `vocabulary.MOVED` carries on its left-hand side, which
are listed as such below and are the one kind of reference that is SUPPOSED to name nothing.

The trees are asked of `loader.sources()` rather than globbed, for the reason that function
exists: a glob is a layout, and layouts move. Each kind is asserted non-empty below.
"""

from __future__ import annotations

import io
import re
import tokenize
from collections import Counter

import rdflib

import pytest

from agent import loader

# Every namespace of ours that is not the kernel's own, label -> IRI, asked of the loader
# rather than listed: a sixth capability, a new transport or a new part is scanned for the day
# it declares a prefix. The allowlist keys carry only the `label#term` tail, which is what a
# reader is actually checking. A bare `family#` with no local name is a namespace constant or
# a PREFIX line, and counts: it is the kernel holding another tree's namespace, which is the
# thing being ratcheted down.
_NAMESPACES = {label: iri for label, iri in loader.prefixes().items() if label != "ag"}
_LABEL_OF = {iri: label for label, iri in _NAMESPACES.items()}

_PACKAGE_IRI = re.compile(
    "(" + "|".join(re.escape(iri) for iri in sorted(_NAMESPACES.values(), key=len, reverse=True))
    + ")([A-Za-z][A-Za-z0-9]*)?")

# The prefixed form: `market:bidsIn`. Not preceded by anything that would make it part of a
# longer token — an IRI's scheme, a path, a fragment.
_PREFIXED = re.compile(
    r"(?<![\w/#:.-])(" + "|".join(re.escape(l) for l in sorted(_NAMESPACES, key=len, reverse=True))
    + r"):([A-Za-z][A-Za-z0-9]*)")

_QUERY_WORDS = ("SELECT", "INSERT", "DELETE", "CONSTRUCT", "ASK", "WHERE", "GRAPH", "PREFIX")

# Every file kind the kernel ships that can carry an IRI, with what it is doing here. `*.ttl`
# and `*.ru` are in for the reason the docstring gives; `*.rq` carries none today and is in
# anyway, so that the day a kernel query grows one, this says so rather than the query silently
# depending on a package.
#  No `*.rq` any more: the kernel's last query file was `desires.rq`, and it went to sensing
#  with the stake (the-stake-is-sensings-want). A kind the kernel legitimately ships none of
#  is not a kind the ratchet has lost sight of.
_KINDS = ("*.py", "*.ru", "*.ttl")

# PARTITIONED out of the loader's union, exactly as `test_store.py` does: the kernel is what is
# left when `packages/` is taken away, so a tree nobody here has heard of lands on one side or
# the other rather than outside both.
_KERNEL_FILES = {
    kind: [p for p in loader.sources(kind) if "packages" not in p.parts]
    for kind in _KINDS
}


def _tail(match: re.Match) -> str:
    """`market#Raises`, or `market#` for a bare namespace — the same key for either form."""
    return f"{_LABEL_OF[match.group(1)]}#{match.group(2) or ''}"


def _query_strings(text: str) -> list[str]:
    """The string literals of a Python file that carry SPARQL — never a docstring, never a
    comment. An f-string is joined back from its pieces, because `{{` splits one and a piece
    may then hold the term without the keyword that marks it as a query."""
    toks = list(tokenize.generate_tokens(io.StringIO(text).readline))

    def is_docstring(i: int) -> bool:
        j = i - 1
        while j >= 0 and toks[j].type in (tokenize.NL, tokenize.COMMENT):
            j -= 1
        return j < 0 or toks[j].type in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT,
                                         tokenize.ENCODING)

    out, i = [], 0
    while i < len(toks):
        tok = toks[i]
        if tok.type == tokenize.STRING and not is_docstring(i):
            out.append(tok.string)
        elif tok.type == getattr(tokenize, "FSTRING_START", -1):
            doc, pieces = is_docstring(i), []
            i += 1
            while toks[i].type != tokenize.FSTRING_END:
                if toks[i].type == tokenize.FSTRING_MIDDLE:
                    pieces.append(toks[i].string)
                i += 1
            if not doc:
                out.append("".join(pieces))
        i += 1
    return [s for s in out if any(w in s.upper() for w in _QUERY_WORDS)]


def _without_prose(text: str) -> str:
    """A rule or a Turtle file with its comments and its string literals blanked, so that a
    prefixed name found in it is one the parser would read as a term."""
    text = re.sub(r'"""(?:.|\n)*?"""', '""', text)
    text = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', text)
    return re.sub(r"#[^\n]*", "", text)


def _occurrences() -> Counter[tuple[str, str]]:
    """Every package-namespace term the kernel names, by (file, tail), with multiplicity —
    spelled out anywhere in the file, or prefixed where a prefixed form means something.

    Counted rather than set-collected so that a SECOND use of an already-allowed term is still a
    new reference. The ratchet is about the number going down.
    """
    found: Counter[tuple[str, str]] = Counter()
    for kind, paths in _KERNEL_FILES.items():
        for path in paths:
            rel = path.relative_to(loader.REPO_ROOT).as_posix()
            text = path.read_text()
            for match in _PACKAGE_IRI.finditer(text):
                found[(rel, _tail(match))] += 1
            haystacks = _query_strings(text) if kind == "*.py" else [_without_prose(text)]
            for hay in haystacks:
                for match in _PREFIXED.finditer(hay):
                    found[(rel, f"{match.group(1)}#{match.group(2)}")] += 1
    return found


# --- the allowlist ----------------------------------------------------------------------------
#
# (file, tail) -> (how many, why it is here and what removes it). Grouped by #334's three kinds,
# then by the fourth thing the widened scan found and the issue does not classify.

ALLOWED: dict[tuple[str, str], tuple[int, str]] = {

    # KIND 1 and KIND 2 ARE EMPTY. The keeper's copy of the direction went when the actor that
    # opens a watch began saying which way (`rises`), and the look-once and the seeing window
    # went with it — the actor nudges its own sensing and passes the cadence it keeps. #334's
    # first two bullets, arrived.

    # A migration DESTINATION. `vocabulary.MOVED` records where a retired spelling
    # went, and the first means to leave the kernel for a package (market:Offer, with
    # a-round-is-a-fact-and-offering-is-an-action) makes a package word the destination of two
    # kernel spellings. The map is a record of where things went and cannot avoid naming the
    # place; it leaves when no volume older than that change can exist to migrate.
    ("agent/vocabulary.py", "market#Offering"): (
        1, "migration: where every older spelling of the host's move went — removable with the last pre-#363 volume"),
    ("agent/vocabulary.py", "sensing#Observing"): (1, "migration: the look's destination"),
    ("agent/vocabulary.py", "sensing#Aim"): (1, "migration: the aim's destination (#377)"),
    ("agent/vocabulary.py", "sensing#aims"): (1, "migration: the aim's destination (#377)"),
    ("agent/vocabulary.py", "actuation#Dosing"): (1, "migration: the dose's destination"),
    ("agent/vocabulary.py", "market#Acquiring"): (1, "migration: buying's destination"),
    ("agent/vocabulary.py", "market#Presenting"): (1, "migration: the held claim's destination"),
    ("agent/vocabulary.py", "sensing#Observe"): (1, "migration: a retired spelling on the left-hand side"),
    ("agent/vocabulary.py", "actuation#Actuate"): (1, "migration: a retired spelling on the left-hand side"),
    ("agent/vocabulary.py", "market#Offer"): (1, "migration: a retired spelling on the left-hand side"),
    ("agent/vocabulary.py", "market#Acquire"): (1, "migration: a retired spelling on the left-hand side"),
    ("agent/vocabulary.py", "market#Apply"): (1, "migration: a retired spelling on the left-hand side"),

    # KIND 3 — `agent/ontology.py`'s namespace constants. Self-aware in place ("these are NOT a
    # prefix registry") and consumed mainly by `onboarding/`, which legitimately knows packages
    # because it reads the ratified files directly rather than through a Store carrying
    # `store.PREFIXES`. #334's fourth bullet: they move to their consumers, or their staying is
    # argued here. Neither has happened yet, so this comment is the placeholder and not the
    # argument.
    ("agent/ontology.py", "market#"): (1, "namespace constant, for onboarding's interpolation"),
    ("agent/ontology.py", "sensing#"): (1, "namespace constant, same"),
    ("agent/ontology.py", "actuation#"): (1, "namespace constant, same"),
    ("agent/ontology.py", "review#"): (1, "namespace constant, same"),
    #  And the eight the widened scan (#378) found beside them — a transport, a bus, five parts
    #  and a microcontroller — all interpolated by onboarding's generators and by nothing in the
    #  kernel. `SOSA` was the first of the block to move to `onboarding/namespaces.py`; these
    #  follow it the same way, and each removal is one entry off this list.
    ("agent/ontology.py", "mqtt#"): (1, "namespace constant, for onboarding's interpolation"),
    ("agent/ontology.py", "mc#"): (1, "namespace constant, same"),
    ("agent/ontology.py", "dht11#"): (1, "namespace constant, same"),
    ("agent/ontology.py", "esp32#"): (1, "namespace constant, same"),
    ("agent/ontology.py", "i2c#"): (1, "namespace constant, same"),
    ("agent/ontology.py", "onewire#"): (1, "namespace constant, same"),
    ("agent/ontology.py", "probe#"): (1, "namespace constant, same"),
    ("agent/ontology.py", "rgbled#"): (1, "namespace constant, same"),

    # KIND 5 — the BUS. `agent/world.py` asks the world where the broker is before any package's
    # Python has loaded, in the transport's own words, and `ag:SimulatedDeviceShape` says a
    # stand-in must be reachable the way a real device is — on a bus, or sharing a reading topic.
    # Found by the prefixed scan (#378), which is what made them visible; they were the whole of
    # what "agent/world.py is full of market:bidsIn" had left once the wiring went to the
    # packages. What removes them: the transport package answering "where is the bus" itself,
    # and the reachability shape living with it — a seam, not yet an issue.
    ("agent/world.py", "mqtt#MessageBus"): (1, "the bus: where the broker is, asked before any package loads"),
    ("agent/world.py", "mqtt#brokerHost"): (1, "the bus, same"),
    ("agent/world.py", "mqtt#brokerPort"): (1, "the bus, same"),
    ("agent/world.py", "mqtt#brokerTlsPort"): (1, "the bus, same"),
    ("agent/shapes.ttl", "mqtt#onBus"): (2, "a stand-in must be reachable like a real device — the transport's words for reachable"),
    ("agent/shapes.ttl", "mqtt#readingTopic"): (2, "same shape, the shared-topic half"),

    # KIND 4 — the kernel's RDF, found by widening the scan past `agent/*.py`. #334's three
    # kinds are all Python and none of them covers these, so they sat here marked UNCLASSIFIED
    # until #337 settled what rule the project actually holds:
    #
    #     knowledge/decisions/the-kernel-names-no-package-word.md
    #
    # THE KERNEL NAMES NO PACKAGE'S WORD. Not in Python, where `lint-imports` has held it since
    # the mind came home, and not in RDF, where nothing held it at all. A package is optional and
    # the core depends on none of them, and that claim does not survive being true of imports and
    # negotiable for vocabulary. So every entry below is debt, exactly like kinds 1-3, and this
    # list is the tolerated relaxation rather than a set of permissions: it must reach zero, and
    # #334's last bullet — the ratchet flipping to a prohibition — is unchanged.
    #
    # THAT RULING OVERTURNED A LOOSER ONE, which is worth knowing because the looser one is the
    # first thing a reader re-derives. It permitted a borrowing whose absence fails LOUDLY — a
    # shape that starts refusing more, a warning that starts firing — on the reasoning that only
    # a SILENT loss is a real dependency. The measurements behind it stand and are in the record.
    # The permission does not: optionality is the claim the architecture rests on, and a claim
    # with a carve-out cannot carry it.
    #
    # What survived the demotion is the ORDER. The loudness analysis no longer licenses anything;
    # it says which of these is dangerous and which is merely untidy, so the entries are grouped
    # first-to-go rather than by file. Measured on pySHACL 0.40.1 with the sensing predicates
    # renamed into a namespace nothing declares, which is what a removed package looks like to a
    # shape.

    # 1 THROUGH 4 ARE PAID, and by one change rather than four: `agent/desires.ru`'s whole
    # relationship with `sensing:` was the FRESHNESS WANT, and that want is derived by
    # `packages/capability/sensing/desires.ru` now (#331). Its premise is an instrument, which
    # is that package's fact, so the horizon term is spelled where it is owned and the three
    # prefix lines had nothing left to bind. Worth reading in the order this list put them:
    #
    #   1, THE JUDGE (#342) — the met-test named the horizon in a REQUIRED triple pattern, so
    #     the term decided pass or fail: spelled wrong, the query returned no rows and pySHACL
    #     reported conformance, and the want read MET for ever with nothing red anywhere. It is
    #     dissolved rather than moved. The shape now says what the agent WANTS — a reading of
    #     this exists, made by this instrument, taken within the horizon — so a term that stops
    #     resolving takes the inner pattern with it, the NOT EXISTS holds, and the want reports
    #     UNMET. Which is the direction #337's ruling asks for, arrived at by stating the goal
    #     positively rather than by guarding the borrowing.
    #   2 and 3, SPELLINGS (#343) — `market:` and `actuation:` were named by no pattern in the
    #     file, and went with the rule that had left them behind. `agent/ontology.ttl`'s
    #     `sensing:` was the last of the three and is now gone too, which closes #343: it
    #     declared a prefix the kernel ontology used in prose only, so no triple needed it.
    #   4, THE SELECTOR — `sensing:polls` and `sensing:monitors` in the rule's WHERE, which is
    #     exactly the "somewhere for the knowledge to go" this entry said it was waiting for.
    #     The mind's own derivation is no longer the thing reaching into a capability's
    #     vocabulary for its premise; the capability derives the want its equipment implies.
    #
    # 5 — the last shape entry. 6 IS PAID: the "no sensor for this desire" warning that joined
    #   through `sensing:polls` and `sensing:monitors` is `sensing:BeyondSurvivalShape` now,
    #   beside `sensing:DesirerShape`, both targeted on the stake's premise in the package that
    #   states it (the-stake-is-sensings-want). What remains is one WIDENER inside
    #   DeviceModelShape's OPTIONAL — without it COALESCE falls back to 1.0, the ceiling drops,
    #   and an initial value of 45.0 that conformed now VIOLATES. It wants a kernel-owned way
    #   to say "the range this thing is measured against".
    ("agent/shapes.ttl", "sensing#monitors"): (
        1, "debt, later (widener): a model's initial value is checked against the subject it "
           "monitors — losing it makes validation stricter and noisier, never quieter"),

    # 7 — the SELECTOR went to actuation: `SimulatedActuatorShape` targets `actuation:actuates`
    # and lives in `packages/capability/actuation/shapes.ttl` now.
}


# --- the guards on the guard ------------------------------------------------------------------

@pytest.mark.parametrize("kind", _KINDS)
def test_every_kernel_file_kind_is_still_found(kind):
    """If a kind's glob empties, the scan below simply reads fewer files and the ratchet passes
    while watching less. That is how coverage was lost twice before."""
    assert _KERNEL_FILES[kind], (
        f"the kernel ships no {kind} — the tree has moved, and the ratchet is no longer "
        "reading that kind of file")


def test_the_scan_pattern_matches_the_shape_it_is_looking_for():
    """A self-test on the needle, not the haystack.

    Once #334 empties the allowlist the scan will legitimately find nothing, and a broken regex
    would look exactly like success. This pins both forms the scan must recognise — a term and
    a bare namespace — against literals, so the pattern is known to work whatever the kernel
    happens to contain.
    """
    stem = "http://example.org/orexis/"
    assert [_tail(m) for m in _PACKAGE_IRI.finditer(f'"{stem}market#Bidding"')] == \
        ["market#Bidding"]
    assert [_tail(m) for m in _PACKAGE_IRI.finditer(f"PREFIX sensing: <{stem}sensing#>")] == \
        ["sensing#"]
    assert not _PACKAGE_IRI.findall("http://example.org/orexis#Intention"), \
        "the kernel's own namespace is not a package's and must not be swept up"
    #  The prefixed form, and the three places it must NOT fire: inside an IRI, on the
    #  kernel's own prefix, and in prose the tokenizer keeps out of a query string.
    assert [m.group(1, 2) for m in _PREFIXED.finditer("?a market:bidsIn ?v ; ag:localId ?i")] == \
        [("market", "bidsIn")]
    assert not _PREFIXED.findall(f"<{stem}market#bidsIn>")
    assert _query_strings('_Q = f"""SELECT ?b WHERE {{ ?b a mqtt:MessageBus }}"""') == \
        ["SELECT ?b WHERE { ?b a mqtt:MessageBus }"]
    assert _query_strings('def f():\n    """A SELECT over mqtt:MessageBus rows."""\n') == []
    assert _without_prose('x sh:message "sensing:polls" . # sensing:polls\n') == 'x sh:message "" . \n'


def test_every_capability_package_on_disk_is_among_the_namespaces_scanned_for():
    """#334 named five families by hand; the scan asks the loader now, so a sixth is covered
    the day it declares a prefix. This holds the two together: a capability package whose
    namespace the loader does not report is one the ratchet cannot see."""
    on_disk = {p.name for p in (loader.PACKAGES_ROOT / "capability").iterdir()
               if p.is_dir() and not p.name.startswith("__")}
    assert on_disk, "no capability packages found — the tree has moved and this checks nothing"
    assert on_disk <= set(_NAMESPACES), (
        f"{sorted(on_disk - set(_NAMESPACES))} declare no namespace the loader reports, so the "
        "kernel could name their words unseen")
    assert len(_NAMESPACES) > len(on_disk), \
        "only the capability families are scanned for — the transports and the parts are not"


# --- every term named still exists (#344) -----------------------------------------------------

#  The left-hand side of `vocabulary.MOVED`: spellings that were RETIRED, which the kernel names
#  precisely because nothing declares them any more. The one kind of reference that is supposed
#  to resolve to nothing.
RETIRED = frozenset(
    key for key, (_, why) in ALLOWED.items() if why.startswith("migration: a retired spelling"))


def _declared() -> set[str]:
    """Every subject any ontology or actions file declares — the union T-Box, read off the
    files. An action node (`market:Offering`) is declared in its package's `actions.ttl`."""
    out: set[str] = set()
    for path in loader.ontology_files() + loader.files(loader.ACTIONS):
        out.update(str(s) for s in rdflib.Graph().parse(path, format="turtle").subjects()
                   if isinstance(s, rdflib.URIRef))
    return out


def test_every_package_term_the_kernel_names_is_one_its_package_declares():
    """A rename in a package's own namespace must not leave the kernel naming the old word: the
    pattern would match nothing, and no engine says so — the failure every-term-in-its-own-house
    records biting four times in one sweep. So each term found, in either form, is resolved
    against what the ontologies declare, and the retired spellings are the only ones excused."""
    found = _occurrences()
    assert found, "the scan found nothing at all — it is not reading the kernel"
    declared = _declared()
    assert declared, "no ontology declared a subject — the loader found no files"
    unresolved = sorted(
        (rel, tail) for rel, tail in found
        if tail.split("#", 1)[1] and (rel, tail) not in RETIRED
        and _NAMESPACES[tail.split("#", 1)[0]] + tail.split("#", 1)[1] not in declared)
    assert not unresolved, (
        f"the kernel names package terms no ontology declares: {unresolved}. Either the "
        "package renamed its word and the kernel kept the old spelling, or the term never "
        "existed — both match nothing, silently."
    )
    #  The check can fail: a spelling nothing declares is seen as such.
    assert _NAMESPACES["sensing"] + "NotAThingAnyPackageDeclares" not in declared


# --- the ratchet itself -----------------------------------------------------------------------

def test_the_kernel_names_no_package_namespace_that_is_not_allowed():
    """The half that stops the number going up.

    A new reference is either a genuinely new dependency of the kernel on a package's
    vocabulary — which is what #334 says should stop — or a move of one that is already here,
    in which case the old entry needs deleting in the same change.
    """
    found = _occurrences()
    unknown = sorted(key for key in found if key not in ALLOWED)
    assert not unknown, (
        f"the kernel names package vocabulary nowhere on the allowlist: {unknown}. This is a "
        "ratchet (#334): the kernel is meant to be BDI structure, and a package owns its own "
        "words. Either ask the graph instead, or — if the reference is genuinely unavoidable "
        "— add it to ALLOWED with what will remove it again."
    )
    grown = sorted(key for key in found if key in ALLOWED and found[key] > ALLOWED[key][0])
    assert not grown, (
        f"{grown} occur more often than the allowlist permits — the kernel leaned harder on a "
        "package's vocabulary than it did, and the ratchet only turns one way"
    )


def test_no_allowlist_entry_has_quietly_stopped_guarding():
    """The half that makes the number go down, and the reason this is not just a grep.

    An entry for a line that no longer exists is an exemption nobody can see is spent: it
    exempts nothing, so nothing fails, and the next reference to the same term in the same file
    slides in under it. Same family as the emptied globs in `tests/test_store.py`.
    """
    found = _occurrences()
    stale = sorted(key for key in ALLOWED if found[key] < ALLOWED[key][0])
    assert not stale, (
        f"delete these from ALLOWED — they no longer occur: {stale}. Something in #334 has "
        "landed and the allowlist has not been told. When it empties altogether, the last "
        "bullet of #334 applies: the ratchet becomes a prohibition and this file loses its "
        "list."
    )
