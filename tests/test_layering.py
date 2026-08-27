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

from test_projects import imported, sources

REPO_ROOT = Path(__file__).resolve().parents[1]

#  Discovered, not written down. The kernel record and the assembly record are prepended by the
#  loader and are not packages under `packages/`, so they are dropped.
PACKAGES = tuple(p for p in loader.packages() if not p.is_kernel and p.kind != "kernel")
MODULES = {p.import_name for p in PACKAGES}


def test_there_are_packages_to_check():
    """The guard on the guard: every assertion below loops, and an empty loop asserts nothing."""
    assert len(PACKAGES) >= 20, (
        f"only {len(PACKAGES)} packages discovered — if `packages/` moved or its naming "
        "changed, every test in this file silently stops checking anything.")


@pytest.mark.parametrize("tree", ["agent", "assembly"])
def test_the_kernel_and_the_assembly_reach_into_no_package(tree: str):
    """What LOADS packages must never need one — the claim every package's optionality rests on.

    The violations this replaced were not theoretical: `agent/desire.py` and `agent/genesis.py`
    once imported a package module that did nothing but re-export a kernel function, so the
    kernel was importing a package to get its own code back.
    """
    offenders = {
        path.relative_to(REPO_ROOT): sorted(imported([path]) & MODULES)
        for path in sources(REPO_ROOT / tree)
        if imported([path]) & MODULES
    }
    assert not offenders, f"{tree}/ imports a package: {offenders}"


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
