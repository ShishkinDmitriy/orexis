"""The layering, where it involves a package — found by looking, never listed.

These four claims used to be `import-linter` contracts, and three of them named `packages` as a
single module. That worked while every package lived under one import root. It stopped working
when a package became a top-level distribution: there is no shared root left to name, and a
wildcard cannot stand in for one — `grimp` rejects `orexis_*` outright, because its wildcards
match whole segments and never part of one. Measured, not assumed.

The alternative was to list twenty-one modules in `pyproject.toml`. That is a registry, and a
registry is exactly what this tree exists not to have: adding a package is adding a directory,
and a contract somebody must remember to edit is a contract that is wrong the first time they
do not. So the claims moved here, where the list is **discovered** — `loader.packages()`, the
same call the runtime makes — and a package added tomorrow is covered without anyone touching
this file.

What is still in `pyproject.toml` is the layering among the three trees of the root
distribution. Those are fixed, few, and named honestly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from assembly import loader

from test_projects import FLOOR_FAMILY, imported, sources

REPO_ROOT = Path(__file__).resolve().parents[1]

#  Discovered, not written down. The kernel record and the assembly record are prepended by the
#  loader and are not packages under `packages/`, so they are dropped.
PACKAGES = tuple(p for p in loader.packages() if not p.is_kernel and p.kind != "kernel")
MODULES = {p.import_name for p in PACKAGES}

#  THE FLOOR: the mind's stores, a package the layers depend on and that depends on no layer
#  (a-layer-is-a-package-and-need-loads-it). Found by FAMILY — the loader's `kind`, read off
#  the package's own name — so the carve-out below names no package and a second member is
#  covered the day its directory appears. It is the one package the kernel may import, because
#  a layer importing the contract of the layer beneath it is the layering working; assembly
#  may not, because assembly is beneath the floor too.
FLOOR = tuple(p for p in PACKAGES if p.kind == FLOOR_FAMILY)
FLOOR_MODULES = {p.import_name for p in FLOOR}


def test_there_are_packages_to_check():
    """The guard on the guard: every assertion below loops, and an empty loop asserts nothing."""
    assert len(PACKAGES) >= 20, (
        f"only {len(PACKAGES)} packages discovered — if `packages/` moved or its naming "
        "changed, every test in this file silently stops checking anything.")


@pytest.mark.parametrize("tree", ["agent", "assembly"])
def test_the_kernel_and_the_assembly_reach_into_no_package(tree: str):
    """What LOADS packages must never need one — the claim every package's optionality rests on.

    The violations this replaced were not theoretical: the desire modality and `agent/genesis.py`
    once imported a package module that did nothing but re-export a kernel function, so the
    kernel was importing a package to get its own code back.

    The one carve-out is the FLOOR, and it is the kernel's alone: `agent/` is the layers, and
    a layer imports the stores beneath it (a-layer-is-a-package-and-need-loads-it). Assembly
    is beneath the stores, so for it nothing is carved out.
    """
    refused = MODULES - FLOOR_MODULES if tree == "agent" else MODULES
    offenders = {
        path.relative_to(REPO_ROOT): sorted(imported([path]) & refused)
        for path in sources(REPO_ROOT / tree)
        if imported([path]) & refused
    }
    assert not offenders, f"{tree}/ imports a package: {offenders}"


def test_there_is_a_floor():
    """The guard on the carve-out: a family with no member excuses nothing and looks as if it
    did — and the test below, looping over it, would assert nothing."""
    assert FLOOR, (
        f"no package of the `{FLOOR_FAMILY}` family discovered — the mind's stores moved or "
        "were renamed, and the kernel carve-out above now excuses nothing while the floor's "
        "own contract below checks nothing.")


@pytest.mark.parametrize("pkg", FLOOR, ids=lambda p: p.name)
def test_the_floor_imports_no_layer_and_no_package(pkg):
    """What every layer meets at must need none of them, and nothing a world could grant.

    The stores import `assembly` — beneath them, as they are beneath the layers — and nothing
    else of this repository's: not `agent/` (the layers), not `onboarding/` (the operator's
    tools), and no other package, capability or otherwise. A layer arriving here is the floor
    reaching UP, which is the trigger a-layer-is-a-package-and-need-loads-it names for
    rereading the record.
    """
    above = {"agent", "onboarding"} | (MODULES - {pkg.import_name})
    offenders = {
        path.relative_to(REPO_ROOT): sorted(imported([path]) & above)
        for path in sources(pkg.path)
        if imported([path]) & above
    }
    assert not offenders, f"{pkg.name} — the floor — imports what stands on it: {offenders}"


@pytest.mark.parametrize("pkg", PACKAGES, ids=lambda p: p.name)
def test_no_package_reaches_for_the_operators_tools(pkg):
    """A capability importing onboarding would put credential-minting code on the wrong side of
    the boundary the agent image is built to keep it out of."""
    offenders = {
        path.relative_to(REPO_ROOT): sorted(imported([path]) & {"onboarding"})
        for path in sources(pkg.path)
        if "onboarding" in imported([path])
    }
    assert not offenders, f"{pkg.name} imports onboarding: {offenders}"


CAPABILITIES = tuple(p for p in PACKAGES if p.kind == "capability")


@pytest.mark.parametrize("pkg", CAPABILITIES, ids=lambda p: p.name)
def test_capability_packages_do_not_import_each_other(pkg):
    """They meet through the T-Box, via `agent.provider()` — never through Python.

    The one written exception is a family's PLUG-INS importing the family's contract: a codec, a
    scaling and a transport import sensing's, because those are the contracts they exist to
    implement. That is why this covers capabilities only, and why the exception is a different
    family rather than a carve-out — see sensing-owns-the-reading-pipeline.
    """
    others = {p.import_name for p in CAPABILITIES} - {pkg.import_name}
    offenders = {
        path.relative_to(REPO_ROOT): sorted(imported([path]) & others)
        for path in sources(pkg.path)
        if imported([path]) & others
    }
    assert not offenders, f"{pkg.name} imports another capability: {offenders}"
