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

WHAT IS NOT IN SCOPE, said plainly so a green run is not read as more than it is: the SPELLED-OUT
IRI, and only that. A kernel query saying `market:bidsIn` with the prefix declared for it is
invisible here, and `agent/world.py` is full of them — it loads an agent's own view of itself
through the market vocabulary, which predates #334 and is untouched by it. That is the larger
surface and a different argument, so this guard does not quietly start making it. What the
spelled-out form has that the prefixed one does not is silence on the way out: a prefixed name is
at least text a rename can grep for, while an interpolated IRI goes on matching nothing.

That exclusion still holds, and #337 sharpened it rather than overturning it. The rule now covers
the prefixed form too — it covers every form — but this guard is a COUNT, and a count is the wrong
instrument for a term that is merely misspelled. `agent/readings.rq:23` reads `sensing:staleAfterS`
prefixed: zero occurrences here, and the same dependency as the spelled-out one two files away. So
what the prefixed form needs first is a check that the term still RESOLVES against the package
declaring it (#344), and widening this scan to `agent/world.py`'s market vocabulary stays the
larger, later argument.

The trees are asked of `loader.sources()` rather than globbed, for the reason that function
exists: a glob is a layout, and layouts move. Each kind is asserted non-empty below.
"""

from __future__ import annotations

import re
from collections import Counter

import pytest

from agent import loader

# The namespace every package of ours hangs off. Spelled once; the allowlist keys carry only
# the `family#term` tail, which is what a reader is actually checking.
_STEM = "http://example.org/orexis/"

# The five capability families, from #334. A bare `family#` with no local name is a namespace
# constant or a PREFIX line, and counts: it is the kernel holding another tree's namespace,
# which is the thing being ratcheted down.
_FAMILIES = ("actuation", "market", "reporting", "review", "sensing")

_PACKAGE_IRI = re.compile(
    re.escape(_STEM) + "(" + "|".join(_FAMILIES) + ")#([A-Za-z][A-Za-z0-9]*)?")

# Every file kind the kernel ships that can carry an IRI, with what it is doing here. `*.ttl`
# and `*.ru` are in for the reason the docstring gives; `*.rq` carries none today and is in
# anyway, so that the day a kernel query grows one, this says so rather than the query silently
# depending on a package.
_KINDS = ("*.py", "*.rq", "*.ru", "*.ttl")

# PARTITIONED out of the loader's union, exactly as `test_store.py` does: the kernel is what is
# left when `packages/` is taken away, so a tree nobody here has heard of lands on one side or
# the other rather than outside both.
_KERNEL_FILES = {
    kind: [p for p in loader.sources(kind) if "packages" not in p.parts]
    for kind in _KINDS
}


def _tail(match: re.Match) -> str:
    """`market#Raises`, or `market#` for a bare namespace."""
    return f"{match.group(1)}#{match.group(2) or ''}"


def _occurrences() -> Counter[tuple[str, str]]:
    """Every package-namespace IRI the kernel spells out, by (file, tail), with multiplicity.

    Counted rather than set-collected so that a SECOND use of an already-allowed term is still a
    new reference. The ratchet is about the number going down.
    """
    found: Counter[tuple[str, str]] = Counter()
    for paths in _KERNEL_FILES.values():
        for path in paths:
            rel = path.relative_to(loader.REPO_ROOT).as_posix()
            for match in _PACKAGE_IRI.finditer(path.read_text()):
                found[(rel, _tail(match))] += 1
    return found


# --- the allowlist ----------------------------------------------------------------------------
#
# (file, tail) -> (how many, why it is here and what removes it). Grouped by #334's three kinds,
# then by the fourth thing the widened scan found and the issue does not classify.

ALLOWED: dict[tuple[str, str], tuple[int, str]] = {

    # KIND 1 — reflex machinery, and it has already shrunk once. The deliberator's three
    # entries — the direction query's two answers and the dealer's shop query — went with the
    # reflex itself (#339), which is #334's third bullet arriving exactly as this list said it
    # would. What survives is the KEEPER's copy of the direction, and it is not reflex leftovers:
    # the verification arc writes the expected direction into the expectation row, so this pair
    # outlives the deliberator that used to share it and leaves on some other change.
    ("agent/keeper.py", "market#Raises"): (
        1, "reflex: the keeper's copy of the direction, written into the expectation row"),
    ("agent/keeper.py", "market#Lowers"): (
        1, "reflex: the keeper's copy of the other half"),

    # KIND 2 — provider-family dispatch. `_dose` dispatches by means (Acquire -> ask Bidding,
    # Actuate -> ask Actuation), and the keeper and the regions ask sensing to look once. A
    # means->family table inside the kernel is the registry smell #207 dissolved for menu kinds.
    # These leave when the sizing declaration moves into the graph: #334's second bullet.
    ("agent/planner.py", "actuation#Actuation"): (
        1, "sizing dispatch: the family asked to size an Actuate"),
    ("agent/planner.py", "market#Bidding"): (
        1, "sizing dispatch: the family asked to size an Acquire"),
    ("agent/keeper.py", "sensing#SensingCapability"): (
        1, "the milder cousin: sensing asked to look once, so the baseline is the freshest "
           "thing on record"),
    ("agent/regions.py", "sensing#SensingCapability"): (
        1, "the same lookup, from the regions side"),

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
    # `agent/readings.rq:23` still reads `sensing:staleAfterS` prefixed, where this scan cannot
    # see it, and #344 is the check that would.
    # 5 and 6 — the shapes. Both measured, both loud, both still debt:
    #   l.108, a WIDENER inside DeviceModelShape's OPTIONAL — without it COALESCE falls back to
    #     1.0, the ceiling drops, and an initial value of 45.0 that conformed now VIOLATES. It
    #     wants a kernel-owned way to say "the range this thing is measured against";
    #   ll.375-376, an EXCUSE inside FILTER NOT EXISTS — without it the "no sensor for this
    #     desire" warning fires for every region instead of none. The warning is arguably
    #     sensing's to raise rather than the kernel's.
    ("agent/shapes.ttl", "sensing#monitors"): (
        2, "debt, later (widener at l.108, excuse at l.376): a model's initial value is checked "
           "against the subject it monitors, and a desire warns when no sensor watches the "
           "subject — losing either makes validation stricter and noisier, never quieter"),
    ("agent/shapes.ttl", "sensing#polls"): (
        1, "debt, later (excuse): the desire warning's agent half — its loss fires the warning "
           "rather than suppressing it"),

    # 7 — a SELECTOR, and the one waiting on a package that does not exist. Removing actuation
    # empties `ag:SimulatedActuatorShape`'s target set and removes every simulated actuator it
    # was checking, together — so nothing false is concluded, and it is still the kernel holding
    # a word it did not declare. What it really wants is the simulation package that
    # every-term-in-its-own-house says has not been written. NOTE THE TRAP for whoever pays this
    # one down: re-targeting `sosa:Actuator` would turn this scan green while changing nothing,
    # because a world types its valve as `actuation:Valve` and reaches `sosa:Actuator` only
    # through the subclass axiom actuation's own ontology declares.
    ("agent/shapes.ttl", "actuation#"): (
        1, "debt, later (selector): prefix declaration, used by the shape targeting "
           "actuation:actuates — its loss empties the target set and the population together, "
           "and the knowledge wants a simulation package to live in"),
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
    assert [_tail(m) for m in _PACKAGE_IRI.finditer(f'"{_STEM}market#Bidding"')] == \
        ["market#Bidding"]
    assert [_tail(m) for m in _PACKAGE_IRI.finditer(f"PREFIX sensing: <{_STEM}sensing#>")] == \
        ["sensing#"]
    assert not _PACKAGE_IRI.findall("http://example.org/orexis#Actuate"), \
        "the kernel's own namespace is not a package's and must not be swept up"


def test_the_families_scanned_for_are_still_the_capability_packages_on_disk():
    """#334 named five families by hand. If a sixth capability package lands, or one is
    renamed, the pattern above goes on matching and silently stops covering it — so the list is
    held to the tree rather than trusted. Widening `_FAMILIES` is the fix, and deciding whether
    the new package's namespace belongs in the kernel is the point of being asked."""
    on_disk = {p.name for p in (loader.PACKAGES_ROOT / "capability").iterdir()
               if p.is_dir() and not p.name.startswith("__")}
    assert on_disk, "no capability packages found — the tree has moved and this checks nothing"
    assert on_disk == set(_FAMILIES), (
        f"the capability families are {sorted(on_disk)} but this file scans for "
        f"{sorted(_FAMILIES)} — reconcile them, and say in the allowlist what the kernel may "
        "do with the difference")


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
