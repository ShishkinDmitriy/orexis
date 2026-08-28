"""Discovery. There is no list of packages anywhere — there are directories, and one kernel.

A **package** is one self-contained thing the society is made of, and it is a directory ONE
level under `packages/`, named `orexis-<family>-<name>/` — which is also its distribution name
and, with underscores, its module. The family is read off that name; there is no directory
above it to read it from:

    orexis-capability-<n>/   what an agent can DO. The extendable axis.
    orexis-transport-<n>/    how a device is REACHED.
    orexis-codec-<n>/        how its bytes become a DOCUMENT.
    orexis-scaling-<n>/      how a raw value becomes a QUANTITY, with a unit.
    orexis-part-, -plant-,
           -bus-, -tool-     the things a world names, and the vocabularies they layer on

**The kernel is not one of them, because it is what finds them.** `agent/` carries its own
`ontology.ttl`, `shapes.ttl` and `rules.ru` beside the Python that reads them, and it is
prepended to `packages()` as a record rather than discovered by walking a tree. That is not the
two-tree arrangement `one-tree-and-one-mechanic` collapsed: those were two systems that looked
alike and were discovered differently. A tree and its loader are not two trees.

It used to be `packages/core/orexis/` — a family with exactly one member, forever, that every
other package layers on and that nothing can remove. That is not a package, it is the base, and
`kind="core"` classified nothing. Now every family left is one an agent can hold zero members
of, which is what "a package is optional" was always supposed to mean.

Onboarding reads every package's `ontology.ttl`, `shapes.ttl` and `rules.ru` through here —
the kernel's included — and never imports a module from any of them.

**The families are one mechanism split by BEARER, not by importance.** Every one of them is a
family with interchangeable members registered by `PROVIDES`, which is what rule 2 calls a
capability. What differs is what carries the conclusion: `ag:hasCapability` on an AGENT for the
first, a predicate on the SENSOR for the rest. Both are derived at genesis from a premise the
world states, because both are known before anything runs — a board's protocol and its wire
format are hardware, not discoveries.

The transport family is the exception and is known to be one: `MqttDriver.claims()` still
re-decides at every boot what genesis could have written down. See the seams in
knowledge/decisions/bytes-become-a-quantity-in-stages.md.

Inside a package, the same names mean the same things every time:

    ontology.ttl   the vocabulary — what its terms mean
    shapes.ttl     the rules — what an agent must believe to hold it
    rules.ru       the derivation — what wiring GIVES an agent it
    review.rq      the second thought — how an agent re-picks one of these beliefs
    __init__.py    the manifest — `PROVIDES = (…)`, the classes this package contributes

Every one of them is optional, and what a package omits is a statement: a domain with no
`__init__.py` contributes no code; a transport with no `rules.ru` grants no capability, which
is exactly the point of it not being one.

Adding a capability is therefore adding a directory. Nothing here, and nothing anywhere else,
learns its name — which is the property the whole layout exists to have.

See knowledge/decisions/capability-packages.md.
"""

from __future__ import annotations

import importlib
import logging
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import terms
from .contribute import answer
from .inject import offers_of

#  Assembly computes this itself rather than importing the kernel's: nothing here may import
#  `agent`, which is what lets the kernel be one of the things assembled.
REPO_ROOT = Path(__file__).resolve().parent.parent

log = logging.getLogger("loader")

# This package's own directory, and the one tree every package lives in. `packages/` sits beside
# `agent/` rather than under it: a package is not the runtime's, it is the project's, and
# onboarding reads the TTL of every one without importing a line of Python from any.
AGENT_ROOT = REPO_ROOT / "agent"
ASSEMBLY_ROOT = Path(__file__).resolve().parent
PACKAGES = "packages"
PACKAGES_ROOT = REPO_ROOT / PACKAGES

# Every package's distribution, directory and module begin with this. It is the only thing that
# marks a directory under `packages/` as one, now that there is no family directory to sit in.
DIST_PREFIX = "orexis"

# The families. NOT a registry — `packages()` finds whatever directories are there, and this
# tuple only fixes the order they merge in. A family invented tomorrow is picked up without
# editing anything; it merely sorts after these.
#
# `core` was here and is gone: it held exactly one member, forever, and a family of one
# classifies nothing. The base vocabulary is the KERNEL now, prepended rather than found.
BUS = "bus"
PART = "part"
PLANT = "plant"
TOOL = "tool"
CAPABILITIES = "capability"
TRANSPORTS = "transport"
CODECS = "codec"
CALIBRATIONS = "scaling"

# The families whose members are borne by a BINDING rather than by an agent. Everything else is
# the same: the world states a premise, that package's `rules.ru` derives which member serves the
# SENSOR, and the runtime looks the term up against `PROVIDES`. What differs from a capability is
# the bearer and the predicate — `codec:decodedBy` on a sensor rather than `ag:hasCapability` on
# an agent — and not when it is decided, which is genesis either way.
BOUND_KINDS = (TRANSPORTS, CODECS, CALIBRATIONS)

# The base vocabulary, merged before anything else.
BASE = "orexis"

# The order the T-Box is merged in. RDF is order-independent, so this buys determinism in logs
# and diffs, not correctness. What it must NOT lose is that the base vocabulary comes first:
# every other package layers on those terms, and reading a merge that puts them last is reading
# it backwards.
#
# That used to be arranged by sorting `core/orexis` to the front, with a comment warning that
# it "happens to sort before `plant/water`, and that is not a thing to rely on". Nothing is
# relied on now: the kernel is not in the tree, so it cannot be sorted wrong.
KINDS = (BUS, PART, PLANT, TOOL, CAPABILITIES, TRANSPORTS, CODECS, CALIBRATIONS)

#  THE ONLY FILENAMES LEFT, and they are the two ROOTS' rather than any package's. Assembly and
#  the kernel are not packages — they are what packages are assembled onto — and neither may be
#  imported to be asked what it brings, since `assembly` importing `agent` is the one direction
#  `lint-imports` forbids outright. So the loader knows their layout by name, which is honest:
#  their layout is its own. Every other package SAYS what it brings, and may call its files
#  whatever it likes (the-assembly-is-not-the-mind).
#
#  `desires.ru`, `review.rq` and `actions.ttl` were here too and are not: no root has one, and
#  no package needs a constant for a name only it uses.
ONTOLOGY = "ontology.ttl"
SHAPES = "shapes.ttl"
RULES = "rules.ru"


@dataclass(frozen=True)
class Package:
    """One directory, and whichever of the four parts it chose to have."""

    kind: str  # capability | transport | part | plant | … — or `kernel`, which is not a family
    name: str
    path: Path
    #  Set only for the kernel, whose Python is `agent` and not `packages.<family>.<name>`.
    #  A field rather than a subclass because everything else about the kernel — its four
    #  filenames, how they are read, where it sorts — is a package's exactly.
    module: str | None = None

    @property
    def is_kernel(self) -> bool:
        """The one record not found by walking. It provides no capability; it provides the
        vocabulary every capability is declared against, and the code that loads them."""
        return self.kind == KERNEL_KIND

    @property
    def import_name(self) -> str:
        """Where its Python lives, for the packages that have any.

        **A package's directory IS its distribution name, and its module is that name with
        underscores** — `packages/orexis-capability-market/` is `orexis-capability-market` on
        an index and `orexis_capability_market` to an importer. One string, three spellings
        fixed by punctuation, and nothing to keep in step (a-package-is-its-name).

        There is no shared import root any more: a package is a TOP-LEVEL module, so nothing
        the kernel could import lives under a name the kernel also owns. `provides()` checks
        for an `__init__.py` before asking, so a knowledge-only package is never imported
        rather than being a special case here.
        """
        return self.module or self.path.name.replace("-", "_")

    def file(self, filename: str) -> Path | None:
        candidate = self.path / filename
        return candidate if candidate.exists() else None

    def manifest(self):
        """This package's `__init__`, imported — or None where it ships no Python.

        Imported at ASSEMBLY, for every package, which is why an `__init__.py` must stay cheap:
        stdlib and `assembly.terms`, nothing else. The heavy import lives behind `provides()`
        and is paid only by an agent whose grants reach it (#216).

        The kernel answers nothing here, and the guard is explicit rather than incidental:
        `agent/__init__.py` exists, so without it this would import the runtime.
        """
        if self.is_kernel or not (self.path / "__init__.py").exists():
            return None
        return importlib.import_module(self.import_name)

    #  What the two ROOTS bring, by convention rather than by contribution. Assembly and the
    #  kernel are not packages — they are what packages are assembled onto — and neither may be
    #  imported to be asked: `assembly` importing `agent` is the one direction `lint-imports`
    #  forbids outright. So the loader knows their layout, which is honest, because their layout
    #  is the loader's own.
    _ROOT_FILES = {terms.VOCABULARY: ONTOLOGY, terms.SHAPES: SHAPES,
                   terms.DERIVATION: RULES}

    def contributes(self, point: str) -> tuple:
        """What this package contributes to one assembly-time point, flattened.

        Never imports anything beyond the package's own `__init__`, and for a root does not
        import at all.
        """
        if self.is_kernel:
            name = self._ROOT_FILES.get(point)
            found = self.file(name) if name else None
            return (found,) if found is not None else ()
        manifest = self.manifest()
        if manifest is None:
            return ()
        fn = answer(manifest, point)
        return tuple(fn(self.path)) if fn is not None else ()

    def provides(self) -> tuple:
        """Whatever classes this package contributes — modules, drivers — or nothing.

        A package with no `__init__.py` is knowledge only, and that is a legitimate kind of
        package: the domain contributes vocabulary and no behaviour.

        LAZY, and that is the whole of #216: `provides()` is a function a package defines, so
        the classes it names are imported when something asks for them rather than when the
        manifest is read. A missing optional extra costs the agents that were granted the
        capability and nothing at all to the rest.
        """
        manifest = self.manifest()
        if manifest is None:
            return ()
        if callable(getattr(manifest, "provides", None)):
            return tuple(manifest.provides())
        return tuple(getattr(manifest, "PROVIDES", ()))


# The kernel, as a record. It carries the same four filenames a package carries, so every
# reader below — `files()`, `prefixes()`, genesis's rule substitution, onboarding's validation —
# reaches it without knowing it is special. What it is NOT is a family: there is no
# `orexis-kernel-<n>/` anyone can add a sibling to, which is exactly the difference from `core`.
KERNEL_KIND = "kernel"
#  The kernel is named, not discovered — it is what the packages layer on, and a thing outside
#  the tree cannot be sorted wrong. Assembly names it by PATH and never imports it.
KERNEL = Package(kind=KERNEL_KIND, name=BASE, path=AGENT_ROOT, module="agent")

#  MERGED FIRST, before the kernel's: the kernel's own extension points are instances of a class
#  this declares (`assembly:Extension`). Not a package and not the kernel — a third root, and
#  the only one that names the other two.
ASSEMBLY = Package(kind=KERNEL_KIND, name="assembly", path=ASSEMBLY_ROOT, module="assembly")


def _put_repo_root_on_path() -> None:
    """Make the repo root importable — done on import, so a checkout that has not been pip
    installed still resolves `agent`, `assembly` and `onboarding`.

    **It does NOT reach the packages any more, and cannot.** A package's module is
    `orexis_capability_market` while its directory is `packages/orexis-capability-market/`, so
    no single sys.path entry maps one to the other: a package is reachable because it is
    INSTALLED, which is what being a project means (a-package-is-its-name). This function is
    therefore about the three trees of the root distribution and nothing else.

    Appended rather than prepended: an installed distribution must always win over a stray
    directory at the repo root, so a new tree can never shadow a real dependency.
    """
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.append(root)


_put_repo_root_on_path()


@lru_cache(maxsize=1)
def packages() -> tuple[Package, ...]:
    """Every package there is, found by looking. Nothing is named.

    ONE level — `packages/orexis-<family>-<name>/` — and the family is read off the NAME rather
    than off a directory above it. It used to be a directory, and that was a second place for
    the same fact: a package's distribution said `orexis-capability-market` while its path said
    `capability/market`, and nothing held the two together. The name is now the only statement,
    so a package cannot be filed under one family and published under another.

    A plant and a part were once both `kind="vocabulary"`, which could not tell them apart. The
    family still means something; it is simply spelled where the package already had to spell
    it.

    The KERNEL comes first and is not found — it is prepended. Everything else layers on its
    terms, so it must merge first, and making that a fact of construction rather than of sort
    order is the point: a thing outside the tree cannot be sorted wrong.

    Families sort by KINDS and then alphabetically, so the merge is deterministic. A family
    nobody thought of is still found: it sorts after the known ones instead of being ignored,
    which is the behaviour a registry could not give.

    A directory whose name is not `orexis-<family>-<name>` is REFUSED rather than skipped. A
    skipped package is the failure this project keeps meeting — the thing that is silently not
    there, that no test sees because an empty result is not an error.

    **An empty `packages/` — or none at all — leaves the kernel, and that is a complete
    build.** Not a degenerate case to guard against: it is the claim that every package is
    optional, stated as the value this function returns.
    """
    if not PACKAGES_ROOT.is_dir():
        return (ASSEMBLY, KERNEL)

    visible = sorted(p for p in PACKAGES_ROOT.iterdir()
                     if p.is_dir() and not p.name.startswith((".", "_")))

    order = {family: i for i, family in enumerate(KINDS)}
    found: list[Package] = []
    for path in visible:
        prefix, _, rest = path.name.partition("-")
        family, _, name = rest.partition("-")
        if prefix != DIST_PREFIX or not family or not name:
            raise ValueError(
                f"{path} is not a package: a package directory is named "
                f"`{DIST_PREFIX}-<family>-<name>`, which is also its distribution name. "
                "Rename it or move it out of packages/.")
        found.append(Package(kind=family, name=name.replace("-", "_"), path=path))
    found.sort(key=lambda p: (order.get(p.kind, len(order)), p.kind, p.name != BASE, p.name))
    return (ASSEMBLY, KERNEL) + tuple(found)


def of_kind(kind: str) -> tuple[Package, ...]:
    return tuple(p for p in packages() if p.kind == kind)


def ask(point: str) -> tuple[Path, ...]:
    """Everything every package contributes to one assembly-time point, in merge order.

    The one door. It used to be a filename — `files("shapes.ttl")` — six literals the kernel
    held and seven call sites reaching for them, which meant a NEW kind of contribution was a
    kernel edit and no package could offer another package a place to contribute knowledge.
    Now a package says what it brings, by term, exactly as it says what it does at run time
    (the-assembly-is-not-the-mind).

    A package that answers nothing contributes nothing, which is how a package with no
    `__init__.py`— there are none left — or one that simply has no shapes says so.
    """
    return tuple(f for pkg in packages() for f in pkg.contributes(point))


def files(filename: str) -> tuple[Path, ...]:
    """Every package's copy of one named file. NOT the contribution mechanism — this is for a
    reader that wants a file by name whatever a package says it brings, and the tests that
    check the tree's shape are its callers."""
    return tuple(f for p in packages() if (f := p.file(filename)) is not None)


def ontology_files() -> tuple[Path, ...]:
    """Every package's vocabulary — and every FIRMWARE's (#175).

    A firmware directory may carry an `ontology.ttl` describing what a board running it IS:
    the sense mode, the procedures, the name the generator dispatches on — stated once, like a
    part's datasheet, and reaching every board through the closure's hasValue rule. The tree
    sits beside `packages/` rather than inside it because a firmware is not loadable code for
    an agent; it is a description of hardware behaviour, discovered the same way and merged
    into the same T-Box. Namespaces and prefixes flow through `prefixes()` unchanged, since
    that reads whatever this returns.
    """
    firmware_root = REPO_ROOT / "firmware"
    from_firmware: tuple[Path, ...] = ()
    if firmware_root.is_dir():
        from_firmware = tuple(sorted(
            p / ONTOLOGY for p in firmware_root.iterdir()
            if p.is_dir() and not p.name.startswith((".", "_")) and (p / ONTOLOGY).exists()))
    return ask(terms.VOCABULARY) + from_firmware


def shapes_files() -> tuple[Path, ...]:
    return ask(terms.SHAPES)


def rule_files() -> tuple[Path, ...]:
    return ask(terms.DERIVATION)


def desires_rule_files() -> tuple[Path, ...]:
    """Every package's want-derivation — run by the desire modality's build on every rebuild,
    never by genesis (#312). Only the desire package ships one today; a package that grows a
    kind of want ships its own, and the build collects them exactly as genesis collects
    `rules.ru` — the same union-of-what-is-loaded discipline, one lifecycle over."""
    return ask(terms.WANTS)


def action_files() -> tuple[Path, ...]:
    """Every package's ACTIONS — what an agent can do through the things this package knows.

    One `actions.ttl` per package, one `ag:Action` node per way of acting, carrying its
    precondition (`ag:available`, a SELECT), its effect (`sh:construct`, `ag:retracts`, the
    timing and the confirmation route) and its taker (`ag:takenBy`). RDF rather than a query
    file because a node with a condition and a construct already IS the action schema — it
    loads into the store at genesis, and a model or a sovereign reads the whole tool list
    without a second format existing anywhere.

    Found rather than listed, like every file here: a package that grows a way of acting is a
    directory with this file in it, and nothing in the kernel learns its name. Three files
    used to say this — availability, duties, effects — and an author adding one way of acting
    wrote to all of them.
    """
    return ask(terms.ACTIONS)


def sources(pattern: str = "*.py") -> tuple[Path, ...]:
    """Every file of one kind across the trees a runtime loads — the KERNEL's and the packages'.

    The accessors above answer for files the loader gives MEANING to: an ontology, a shapes file,
    a rule. This one answers for files it merely contains, which is what a scan wants — the guards
    that hold this codebase to its own rules read source text, and "all the source there is" had
    no name.

    It has one now because not having one cost five guards. Each hand-rolled the union, and four
    hand-rolled it as `PACKAGES_ROOT.rglob(...)` alone — correct when every module lived under
    `packages/`, and silently wrong the day the mind came into the kernel. They did not fail:
    they NARROWED, which nothing can see. A glob can be asserted non-empty and four of them were,
    passing the whole time.

    So: ask here rather than glob a tree. A tree is a layout, and layouts move.
    """
    found = [p for p in KERNEL.path.rglob(pattern) if "__pycache__" not in p.parts]
    if PACKAGES_ROOT.is_dir():
        found += [p for p in PACKAGES_ROOT.rglob(pattern) if "__pycache__" not in p.parts]
    return tuple(sorted(found))


def review_rules() -> tuple[Path, ...]:
    """Every package's review rule, if it has one. Most do not, and that is a statement:
    a capability with nothing worth reconsidering says so by shipping no file."""
    return ask(terms.REVIEW)


_ONTOLOGY_IRI = re.compile(r"<(http://example\.org/orexis[^>\s]*)>\s+a\s+owl:Ontology")


@lru_cache(maxsize=1)
def _namespace_owners() -> dict[str, "Package"]:
    """namespace -> the capability package that owns it, WITHOUT importing a line of Python.

    A package declares one `owl:Ontology` IRI and puts its terms in that IRI plus `#`, and it
    implements terms of its own namespace and no other — checked by `registry()` below, which
    is the eager build every gate still runs. That invariant is what lets a granted capability
    name its own implementer by string alone, so imports can follow grants (#216).
    """
    out: dict[str, Package] = {}
    #  Every package with an ontology, not the capability family alone: a transport declares a
    #  capability too — the one the fact of its bus grants (the-kernel-has-no-mailbox).
    for package in packages():
        if package.kind == "kernel":
            continue
        path = package.file(ONTOLOGY)
        if path is None:
            continue
        for iri in _ONTOLOGY_IRI.findall(path.read_text()):
            out[iri + "#"] = package
    return out


def _provider_in(package: "Package", capability: str) -> type | None:
    """The class in one package that implements one term — importing that package and no other.

    An ImportError is the DECLARED degrade path (#216): a package whose optional extra is not
    installed — `orexis[consulting]` and its model client — leaves its capability unprovided
    for the agents that were granted it, and costs nothing at all to the agents that were
    not. Before this, one missing extra crashed every agent in the society at import time,
    including those that had never heard of the capability.
    """
    try:
        provided = package.provides()
    except ImportError as exc:
        log.warning("%s cannot be imported (%s) — anything it provides is unavailable to "
                    "the agents granted it, and unnoticed by the rest",
                    package.import_name, exc)
        return None
    return next((c for c in provided if getattr(c, "CAPABILITY", "") == capability), None)


def registry_for(capabilities) -> dict[str, type]:
    """capability term -> its module class, importing only the packages the grants reach.

    Composition has always followed the graph; imports did not, and the universal image made
    that invisible until an optional dependency existed. A capability names its owner by
    namespace — no Python read to find out — so a fern imports sensing, market, desire,
    intention, deliberation, review and reporting, and never actuation's, and an agent
    granted no Consulting never touches whatever Consulting will need installed.
    """
    owners = _namespace_owners()
    out: dict[str, type] = {}
    for capability in capabilities:
        package = next((p for ns, p in owners.items() if capability.startswith(ns)), None)
        if package is None:
            continue
        if (cls := _provider_in(package, capability)) is not None:
            out[capability] = cls
    return out


@lru_cache(maxsize=1)
def registry() -> dict[str, type]:
    """capability term -> the module class that implements it, for EVERY package there is.

    The eager build, kept for the gates and the tools that ask what this checkout can do at
    all. A runtime asks `registry_for` instead, so its imports follow its grants; this one
    holds the two invariants that make that legal — every provided class names a term, and
    no term is implemented twice — plus the one it rests on: a package implements only terms
    of its own namespace, so a capability IRI identifies its implementer by string alone.
    """
    out: dict[str, type] = {}
    owners = _namespace_owners()
    for package in of_kind(CAPABILITIES) + of_kind(TRANSPORTS):
        for cls in package.provides():
            if package.kind == TRANSPORTS and hasattr(cls, "claims"):
                continue   # a driver: how ONE device is reached, granting nothing
            if not getattr(cls, "CAPABILITY", ""):
                raise RuntimeError(
                    f"{package.import_name} provides {cls.__name__}, which names no "
                    "CAPABILITY — a module must say which term activates it"
                )
            if cls.CAPABILITY in out:
                raise RuntimeError(
                    f"{cls.CAPABILITY} is implemented twice: {out[cls.CAPABILITY].__name__} "
                    f"and {cls.__name__}. One term, one module."
                )
            owner = next((p for ns, p in owners.items() if cls.CAPABILITY.startswith(ns)),
                         None)
            if owner is not package:
                raise RuntimeError(
                    f"{package.import_name} provides {cls.CAPABILITY}, which belongs to "
                    f"{owner.import_name if owner else 'no package'} — a package implements "
                    "the terms it declares, which is what lets imports follow grants (#216)"
                )
            out[cls.CAPABILITY] = cls
    return out


@lru_cache(maxsize=1)
def drivers() -> tuple[type, ...]:
    """Every transport's driver. Which one speaks to a given sensor is the driver's own
    answer — see sensing's `driver.driver_for`. A transport's `PROVIDES` may hold a MODULE too —
    the capability the fact of its bus grants, how the AGENT reaches everyone — and that one
    is found as every capability is, through `registry_for`."""
    return tuple(cls for p in of_kind(TRANSPORTS) for cls in p.provides()
                 if hasattr(cls, "claims"))


def _members(kind: str) -> dict[str, type]:
    """term -> the class implementing it, for one binding-borne family.

    The same shape as `registry()` and for the same reason: a derived fact names a TERM, and
    something has to map that back to code. Which member serves a sensor is decided by that
    package's `rules.ru` at genesis and read off the graph — nothing here searches, and there is
    no default to apply, because a default that lived in Python would be a fact nothing could
    query.

    One term implemented twice is refused rather than resolved. It would otherwise be settled by
    whichever package the filesystem yielded first, which is a coin flip dressed as a choice,
    and it produces not an error but a build that reads its devices through the wrong member.
    """
    out: dict[str, type] = {}
    for package in of_kind(kind):
        for cls in package.provides():
            term = getattr(cls, "TERM", "")
            if not term:
                raise RuntimeError(
                    f"{package.import_name} provides {cls.__name__}, which names no TERM — "
                    f"a member must say which term a derivation uses to reach it"
                )
            if term in out:
                raise RuntimeError(
                    f"{term} is implemented twice: {out[term].__name__} and "
                    f"{cls.__name__}. One term, one member."
                )
            out[term] = cls
    return out


@lru_cache(maxsize=1)
def codecs() -> dict[str, type]:
    """codec term -> the class that decodes it — see sensing's `codec.codec_for`."""
    return _members(CODECS)


@lru_cache(maxsize=1)
def scalings() -> dict[str, type]:
    """scaling term -> the class that applies it — see sensing's `scaling.scaling_for`."""
    return _members(CALIBRATIONS)


def describe() -> str:
    """What this build is made of — logged at genesis so a deployment is legible."""
    return ", ".join(f"{p.kind}/{p.name}" for p in packages())


# --- the fifth thing a package contributes: its namespace -----------------------------------
#
# A package that declares terms declares them somewhere, and where is its own business. The
# base vocabulary keeps `ag:`; `capabilities/market` keeps `market:`; the hardware modules have
# had `mc:`, `onewire:` and the rest since pins-and-wires. What was missing was any way for a
# runtime query to USE one: `store.PREFIXES` was a kernel constant, so a package with a
# namespace of its own could not be named in SPARQL without editing the kernel — a registry, in
# the tree whose whole claim is that adding a package edits nothing.
#
# So it is read rather than registered, off the `@prefix` lines of the ontology that declares
# the terms. Nothing is listed and nothing is imported: this runs before any capability's Python
# and must, because `agent.beliefs` needs the prefixes and half the capabilities import it.
_NAMESPACE_BASE = "http://example.org/orexis"
_PREFIX_LINE = re.compile(
    rf"@prefix\s+([A-Za-z][\w.-]*):\s*<({re.escape(_NAMESPACE_BASE)}[^>]*)>")


_ANY_PREFIX_LINE = re.compile(r"@prefix\s+([A-Za-z][\w.-]*):\s*<([^>]*)>")


@lru_cache(maxsize=1)
def external_prefixes() -> dict[str, str]:
    """Every EXTERNAL namespace some ontology declares, label -> IRI, found by looking.

    The other half of `prefixes()`, arrived at last (#378). `sosa:`, `ssn-system:`, `unit:`,
    `schema:`, `dcterms:` used to be a kernel constant on the argument that an external
    vocabulary is not a package's to bind — and the kernel then declared `sosa:` while speaking
    no sosa, because sensing does. What the ownership argument actually needs is the rule
    below: ONE label, ONE IRI, across every ontology there is, refused otherwise. A package
    cannot rebind `unit:` past that check, and the kernel does not have to know which package
    reads units to let it name them. What the kernel keeps hard-coded is the handful it speaks
    itself — see `store._KERNEL`.
    """
    out: dict[str, str] = {}
    origin: dict[str, Path] = {}
    for path in ontology_files():
        for label, iri in _ANY_PREFIX_LINE.findall(path.read_text()):
            if iri.startswith(_NAMESPACE_BASE):
                continue
            if (prior := out.get(label)) is not None and prior != iri:
                raise RuntimeError(
                    f"prefix {label!r} means <{prior}> in {origin[label]} and <{iri}> in "
                    f"{path}. One label, one namespace — a query cannot mean both."
                )
            out.setdefault(label, iri)
            origin.setdefault(label, path)
    return out


@lru_cache(maxsize=1)
def prefixes() -> dict[str, str]:
    """Every project-internal namespace there is, label -> IRI, found by looking.

    Only namespaces under this project's own base. An ontology also declares `rdfs:`, `owl:`,
    `sh:` and friends, and those are the kernel's to know: they are stable, external, and not a
    package's to redefine.

    A label bound to two different IRIs is refused rather than resolved. It would otherwise be
    the quietest possible bug — one package's query silently reading another's terms — and the
    engine could not detect it, because both spellings are valid SPARQL.
    """
    out: dict[str, str] = {}
    origin: dict[str, Path] = {}
    for path in ontology_files():
        for label, iri in _PREFIX_LINE.findall(path.read_text()):
            if (prior := out.get(label)) is not None and prior != iri:
                raise RuntimeError(
                    f"prefix {label!r} means <{prior}> in {origin[label]} and <{iri}> in "
                    f"{path}. One label, one namespace — a query cannot mean both."
                )
            out.setdefault(label, iri)
            origin.setdefault(label, path)
    return out


@lru_cache(maxsize=1)
def offers() -> dict:
    """service term -> the function that builds it, across every package. One term, one offer.

    The same rule `_members` holds for a family's members, for the same reason: a term offered
    twice would be settled by whichever package the filesystem yielded first, which is a coin
    flip dressed as a choice. Nothing is CALLED here — the functions are collected, and one runs
    only when an agent asks for that service.
    """
    out: dict[str, tuple] = {}
    for package in packages():
        manifest = package.manifest()
        if manifest is None:
            continue
        for term, name in offers_of(manifest).items():
            if term in out:
                raise RuntimeError(
                    f"{term} is offered twice: by {out[term][0].import_name} and by "
                    f"{package.import_name}. One term, one provider."
                )
            out[term] = (package, getattr(manifest, name))
    return out


@lru_cache(maxsize=1)
def extension_rows() -> dict[str, str]:
    """Every extension point and the cognitive row it belongs to — `ag:row`, declared beside the point by
    whoever owns the question (layered-by-timescale-and-interruptibility)."""
    import rdflib

    out: dict[str, str] = {}
    row = rdflib.URIRef("http://example.org/orexis#row")
    point = rdflib.URIRef("http://example.org/orexis/assembly#Extension")
    for path in ontology_files():
        g = rdflib.Graph().parse(path, format="turtle")
        for term in g.subjects(rdflib.RDF.type, point):
            for value in g.objects(term, row):
                out[str(term)] = str(value)
    return out


@lru_cache(maxsize=1)
def extensions() -> frozenset[str]:
    """Every `assembly:Extension` any ontology declares — the kernel's questions and each package's. What
    `Agent.ask` and `Agent.tell` hold a term to: a point nobody declared is a typo that would
    otherwise be answered by silence (a-hook-is-a-term)."""
    import rdflib

    out: set[str] = set()
    point = rdflib.URIRef("http://example.org/orexis/assembly#Extension")
    for path in ontology_files():
        g = rdflib.Graph().parse(path, format="turtle")
        out.update(str(s) for s in g.subjects(rdflib.RDF.type, point))
    return frozenset(out)
