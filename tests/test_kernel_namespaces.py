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
kinds describe. They are on the list marked unclassified rather than folded into a kind that
does not fit, because deciding their fate is not this change's business.

WHAT IS NOT IN SCOPE, said plainly so a green run is not read as more than it is: the SPELLED-OUT
IRI, and only that. A kernel query saying `market:bidsIn` with the prefix declared for it is
invisible here, and `agent/world.py` is full of them — it loads an agent's own view of itself
through the market vocabulary, which predates #334 and is untouched by it. That is the larger
surface and a different argument, so this guard does not quietly start making it. What the
spelled-out form has that the prefixed one does not is silence on the way out: a prefixed name is
at least text a rename can grep for, while an interpolated IRI goes on matching nothing.

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

    # UNCLASSIFIED — the kernel's RDF, found by widening the scan past `agent/*.py`. #334's
    # three kinds are all Python and none of them covers these. Reported rather than folded in:
    # what should happen to them has not been decided, and this file is not the place to decide
    # it. Worth knowing while it is: `agent/shapes.ttl` carries a comment arguing that the
    # keeper shape cannot name `actuation:hasActuator` or `sensing:polls` without the kernel
    # depending on three packages — and the same file names two sensing terms and targets an
    # actuation one a few shapes away.
    ("agent/shapes.ttl", "actuation#"): (
        1, "UNCLASSIFIED: prefix declaration, used by the shape targeting actuation:actuates"),
    ("agent/shapes.ttl", "sensing#monitors"): (
        2, "UNCLASSIFIED: a model's initial value is checked against the subject it monitors, "
           "and a desire warns when no sensor watches the subject"),
    ("agent/shapes.ttl", "sensing#polls"): (
        1, "UNCLASSIFIED: the same desire warning, the agent's half of the join"),
    ("agent/ontology.ttl", "sensing#"): (
        1, "UNCLASSIFIED: prefix declaration; the kernel ontology uses sensing: in prose only"),
    #  AND THE DESIRE DERIVATION'S FOUR ARE GONE, which is the second time this list has
    #  shrunk by a change rather than by an argument. `agent/desires.ru` declared `market:`,
    #  `actuation:` and `sensing:` and spelled `sensing#staleAfterS` into a query string,
    #  because the freshness want's met-test had to name the horizon term and no prefix
    #  reaches inside a literal. The want is derived by `packages/capability/sensing/
    #  desires.ru` now — its premise is an instrument, which is that package's fact — so the
    #  term is spelled where it is owned and the three prefixes had nothing left to bind
    #  (#343's deletions, arriving from the change that made them dead rather than as a sweep).
    #  What the kernel kept is the whole of the mind: what a want is, when one is met, and the
    #  region derivation, none of which names a package.
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
