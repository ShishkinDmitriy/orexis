"""The layering, where it involves a package — found by looking, never listed.

These claims used to be `import-linter` contracts, and three of them named `packages` as a
single module. That worked while every package lived under one import root. It stopped working
when a package became a top-level distribution: there is no shared root left to name, and a
wildcard cannot stand in for one — `grimp` rejects `orexis_*` outright, because its wildcards
match whole segments and never part of one. Measured, not assumed.

The alternative was to list twenty-odd modules in `pyproject.toml`. That is a registry, and a
registry is exactly what this tree exists not to have: adding a package is adding a directory,
and a contract somebody must remember to edit is a contract that is wrong the first time they
do not. So the claims moved here, where the list is **discovered** — `loader.packages()`, the
same call the runtime makes — and a package added tomorrow is covered without anyone touching
this file.

What is still in `pyproject.toml` is the layering among the three trees of the root
distribution. Those are fixed, few, and named honestly.

THE KERNEL'S OWN LAYERING IS HERE TOO (#452). The kernel is three packages in the one tree — the
reactive loop, progression, deliberation, no floor beneath them — and the order is spelled once,
in `test_projects.LAYERS`. Every arrow between them is a test below, and each was broken once
and seen to fail before it was trusted: a layer importing a layer above it, the container
importing a capability, the assembly importing anything, a capability importing another.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from assembly import loader

from test_projects import LAYERS, imported, sources

REPO_ROOT = Path(__file__).resolve().parents[1]

#  Discovered, not written down. The kernel record and the assembly record are prepended by the
#  loader and are not packages under `packages/`, so they are dropped.
PACKAGES = tuple(p for p in loader.packages() if not p.is_kernel and p.kind != "kernel")
MODULES = {p.import_name for p in PACKAGES}

#  THE LAYERS: found by FAMILY — the loader's `kind`, read off the package's own name — so
#  nothing below names a package and a second member of a layer is covered the day its
#  directory appears. `agent/` is the CONTAINER that assembles them and may import them all;
#  it is not a layer and nothing imports it from below. What a lower layer has to say to a
#  higher one it says as an EVENT through the choir, which is how the arrows stay one-way.
LAYER_PACKAGES = tuple(p for p in PACKAGES if p.kind in LAYERS)
LAYER_MODULES = {p.import_name for p in LAYER_PACKAGES}


def below(family: str) -> set[str]:
    """The import names of every layer STRICTLY beneath this family, in `LAYERS` order."""
    rank = LAYERS.index(family)
    return {p.import_name for p in LAYER_PACKAGES if LAYERS.index(p.kind) < rank}


def test_there_are_packages_to_check():
    """The guard on the guard: every assertion below loops, and an empty loop asserts nothing."""
    assert len(PACKAGES) >= 20, (
        f"only {len(PACKAGES)} packages discovered — if `packages/` moved or its naming "
        "changed, every test in this file silently stops checking anything.")


@pytest.mark.parametrize("family", LAYERS)
def test_every_layer_has_a_member(family: str):
    """The guard on the carve-outs: a family with no member excuses nothing and looks as if it
    did — and the tests below, looping over it, would assert nothing."""
    assert [p for p in LAYER_PACKAGES if p.kind == family], (
        f"no package of the `{family}` family discovered — that layer moved or was renamed, "
        "and the carve-outs in this file and test_projects.py now excuse nothing.")


@pytest.mark.parametrize("tree", ["agent", "assembly"])
def test_the_kernel_and_the_assembly_reach_into_no_package(tree: str):
    """What LOADS packages must never need one — the claim every package's optionality rests on.

    The violations this replaced were not theoretical: the desire modality and `agent/genesis.py`
    once imported a package module that did nothing but re-export a kernel function, so the
    kernel was importing a package to get its own code back.

    The one carve-out is the LAYERS, and it is the container's alone: `agent/` assembles the
    three layer packages into an agent and imports every one of them
    (a-layer-is-a-package-and-need-loads-it). Assembly is beneath the stores, so for it
    nothing is carved out.
    """
    refused = MODULES - LAYER_MODULES if tree == "agent" else MODULES
    offenders = {
        path.relative_to(REPO_ROOT): sorted(imported([path]) & refused)
        for path in sources(REPO_ROOT / tree)
        if imported([path]) & refused
    }
    assert not offenders, f"{tree}/ imports a package: {offenders}"


@pytest.mark.parametrize("pkg", LAYER_PACKAGES, ids=lambda p: p.name)
def test_a_layer_imports_only_the_layers_beneath_it(pkg):
    """The arrows: deliberation -> progression -> reactive, and nothing beneath but assembly.

    A layer may import `assembly` (beneath everything) and the layers strictly earlier in
    `LAYERS`; it may not import the container (`agent/`), the operator's tools, a layer at or
    above its own rank, or any package a world could grant. A layer reaching UP is the trigger
    a-layer-is-a-package-and-need-loads-it names for rereading the record; a layer reaching
    for a capability is the mind depending on a grant, which the-mind-is-not-a-package retired.

    Broken once each way before it was trusted: reactive importing progression FAILED,
    progression importing the search FAILED, the search importing the market FAILED, and the
    container importing the market FAILED.
    """
    allowed = below(pkg.kind) | {pkg.import_name}
    refused = ({"agent", "onboarding"} | MODULES) - allowed
    offenders = {
        path.relative_to(REPO_ROOT): sorted(imported([path]) & refused)
        for path in sources(pkg.path)
        if imported([path]) & refused
    }
    assert not offenders, (
        f"{pkg.name} ({pkg.kind}, may import only {sorted(below(pkg.kind)) or 'assembly'}) "
        f"reaches past its layer: {offenders}")


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

    A capability may import any LAYER's contract — the timer, the act, the reviser's door —
    because the layers are the kernel, not grants; what it may not import is a sibling grant.
    The one written exception among the families is a family's PLUG-INS importing the family's
    contract: a codec, a scaling and a transport import sensing's, because those are the
    contracts they exist to implement. That is why this covers capabilities only, and why the
    exception is a different family rather than a carve-out — see
    sensing-owns-the-reading-pipeline.
    """
    others = {p.import_name for p in CAPABILITIES} - {pkg.import_name}
    offenders = {
        path.relative_to(REPO_ROOT): sorted(imported([path]) & others)
        for path in sources(pkg.path)
        if imported([path]) & others
    }
    assert not offenders, f"{pkg.name} imports another capability: {offenders}"
