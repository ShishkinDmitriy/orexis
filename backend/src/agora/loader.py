"""Discovery. There is no list of capabilities anywhere — there are directories.

A **package** is one self-contained thing the society is made of, and it is a directory:

    kernel/                the T-Box everything layers on. Not a capability; there is one.
    capabilities/<name>/   what an agent can DO. The extendable axis.
    transports/<name>/     how a device is REACHED. Not a capability, deliberately — a
                           protocol changes nothing an agent must decide.
    domain/<name>/         what the society is ABOUT. Vocabulary and rules, usually no code.

Inside a package, the same four names mean the same four things every time:

    ontology.ttl   the vocabulary — what its terms mean
    shapes.ttl     the rules — what an agent must believe to hold it
    rules.ru       the derivation — what wiring GIVES an agent it
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
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .config import PROJECT_ROOT

log = logging.getLogger("loader")

REPO_ROOT = PROJECT_ROOT.parent

KERNEL = "kernel"
CAPABILITIES = "capabilities"
TRANSPORTS = "transports"
DOMAIN = "domain"

# The order the T-Box is merged in. RDF is order-independent, so this buys determinism in
# logs and diffs, not correctness — the kernel first because it is what the rest layer on.
KINDS = (KERNEL, CAPABILITIES, TRANSPORTS, DOMAIN)

ONTOLOGY = "ontology.ttl"
SHAPES = "shapes.ttl"
RULES = "rules.ru"


@dataclass(frozen=True)
class Package:
    """One directory, and whichever of the four parts it chose to have."""

    kind: str  # kernel | capabilities | transports | domain
    name: str
    path: Path

    @property
    def import_name(self) -> str:
        return self.name if self.kind == KERNEL else f"{self.kind}.{self.name}"

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
    """Make the package trees importable — done on import, so `import capabilities.market`
    works for anything that has reached the loader at all.

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
    if (REPO_ROOT / KERNEL).is_dir():
        found.append(Package(kind=KERNEL, name=KERNEL, path=REPO_ROOT / KERNEL))
    for kind in (CAPABILITIES, TRANSPORTS, DOMAIN):
        tree = REPO_ROOT / kind
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
    answer — see `agora.driver.driver_for`."""
    return tuple(cls for p in of_kind(TRANSPORTS) for cls in p.provides())


def describe() -> str:
    """What this build is made of — logged at genesis so a deployment is legible."""
    return ", ".join(
        f"{p.kind}/{p.name}" if p.kind != KERNEL else p.name for p in packages()
    )
