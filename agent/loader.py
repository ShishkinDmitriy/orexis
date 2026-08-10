"""Discovery. There is no list of capabilities anywhere — there are directories.

A **package** is one self-contained thing the society is made of, and it is a directory:

    vocabulary/<name>/       what terms MEAN. Pure knowledge, no Python at all — `agora` is the
                             base everything layers on, `water` is what this society is about.
                             At the repo ROOT, because onboarding validates and derives from it
                             too: it is the one tree both sides genuinely share.
    agent/capabilities/<n>/  what an agent can DO. The extendable axis.
    agent/transports/<n>/    how a device is REACHED. Not a capability, deliberately — a
                             protocol changes nothing an agent must decide.

The last two live INSIDE `agent/` because only an agent runtime loads their Python. Onboarding
reads their `ontology.ttl`, `shapes.ttl` and `rules.ru` — which it finds here, wherever they
sit — and never imports a module from either.

Inside a package, the same four names mean the same four things every time:

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

from .config import REPO_ROOT

log = logging.getLogger("loader")

# This package's own directory. Capabilities and transports live under it, so they are found
# relative to the code that loads them rather than to a repo root that may be a mount point.
AGENT_ROOT = Path(__file__).resolve().parent


VOCABULARY = "vocabulary"
CAPABILITIES = "capabilities"
TRANSPORTS = "transports"

# The base vocabulary, merged before anything else.
BASE = "agora"

# The order the T-Box is merged in. RDF is order-independent, so this buys determinism in logs
# and diffs, not correctness. What it must NOT lose is that the base vocabulary comes first:
# every other package layers on those terms, and reading a merge that puts them last is reading
# it backwards. `vocabulary/agora` is sorted to the front explicitly rather than by luck of the
# alphabet — `agora` happens to sort before `water`, and that is not a thing to rely on.
KINDS = (VOCABULARY, CAPABILITIES, TRANSPORTS)

ONTOLOGY = "ontology.ttl"
SHAPES = "shapes.ttl"
RULES = "rules.ru"
# What a package would like its agents to reconsider about themselves. A SPARQL SELECT binding
# ?term and ?value, run by the reviewer — never an update, and never Python. See agora/review.py.
REVIEW = "review.rq"


@dataclass(frozen=True)
class Package:
    """One directory, and whichever of the four parts it chose to have."""

    kind: str  # vocabulary | capabilities | transports
    name: str
    path: Path

    @property
    def import_name(self) -> str:
        """Where its Python lives, for the packages that have any.

        Capabilities and transports are subpackages of `agent`; vocabulary has no Python at
        all, so this is never asked of one.
        """
        return f"agent.{self.kind}.{self.name}"

    def file(self, filename: str) -> Path | None:
        candidate = self.path / filename
        return candidate if candidate.exists() else None

    def provides(self) -> tuple:
        """Whatever classes this package contributes — modules, drivers — or nothing.

        A package with no `__init__.py` is knowledge only, and that is a legitimate kind of
        package: the domain contributes vocabulary and no behaviour.
        """
        if not (self.path / "__init__.py").exists():
            return ()
        return tuple(getattr(importlib.import_module(self.import_name), "PROVIDES", ()))


def _put_repo_root_on_path() -> None:
    """Make the repo root importable — done on import, so a checkout that has not been pip
    installed still resolves `agent.capabilities.market` and the world trees beside it.

    Appended rather than prepended: an installed distribution must always win over a stray
    directory at the repo root, so a new tree can never shadow a real dependency.
    """
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.append(root)


_put_repo_root_on_path()


@lru_cache(maxsize=1)
def packages() -> tuple[Package, ...]:
    """Every package there is, found by looking. Nothing is named."""
    found: list[Package] = []

    # vocabulary/ is at the repo root and shared with onboarding; the base goes first.
    tree = REPO_ROOT / VOCABULARY
    if tree.is_dir():
        names = sorted(p.name for p in tree.iterdir()
                       if p.is_dir() and not p.name.startswith((".", "_")))
        for name in sorted(names, key=lambda n: (n != BASE, n)):
            found.append(Package(kind=VOCABULARY, name=name, path=tree / name))

    # the agent's own trees: Python only it loads
    for kind in (CAPABILITIES, TRANSPORTS):
        tree = AGENT_ROOT / kind
        if not tree.is_dir():
            continue
        for path in sorted(tree.iterdir()):
            if path.is_dir() and not path.name.startswith((".", "_")):
                found.append(Package(kind=kind, name=path.name, path=path))
    return tuple(found)


def of_kind(kind: str) -> tuple[Package, ...]:
    return tuple(p for p in packages() if p.kind == kind)


def files(filename: str) -> tuple[Path, ...]:
    """Every package's copy of one of the four files, in merge order."""
    return tuple(f for p in packages() if (f := p.file(filename)) is not None)


def ontology_files() -> tuple[Path, ...]:
    return files(ONTOLOGY)


def shapes_files() -> tuple[Path, ...]:
    return files(SHAPES)


def rule_files() -> tuple[Path, ...]:
    return files(RULES)


def review_rules() -> tuple[Path, ...]:
    """Every package's review rule, if it has one. Most do not, and that is a statement:
    a capability with nothing worth reconsidering says so by shipping no file."""
    return files(REVIEW)


@lru_cache(maxsize=1)
def registry() -> dict[str, type]:
    """capability term -> the module class that implements it.

    Built by asking each capability package what it provides. A capability the world composes
    but no package implements is not an error here — the agent reports it at startup, because
    a world that expects more than this build has is a deployment fact, not a crash.
    """
    out: dict[str, type] = {}
    for package in of_kind(CAPABILITIES):
        for cls in package.provides():
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
            out[cls.CAPABILITY] = cls
    return out


@lru_cache(maxsize=1)
def drivers() -> tuple[type, ...]:
    """Every transport's driver. Which one speaks to a given sensor is the driver's own
    answer — see `agent.driver.driver_for`."""
    return tuple(cls for p in of_kind(TRANSPORTS) for cls in p.provides())


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
# and must, because `agent.store` needs the prefixes and half the capabilities import it.
_NAMESPACE_BASE = "http://example.org/agora"
_PREFIX_LINE = re.compile(
    rf"@prefix\s+([A-Za-z][\w.-]*):\s*<({re.escape(_NAMESPACE_BASE)}[^>]*)>")


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
