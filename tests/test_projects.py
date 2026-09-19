"""Every package is a project, and a project declares exactly what it imports.

Twenty-five distributions, each owning a top-level module of its own. What makes that more than ceremony is
the DEPENDENCY GRAPH — `orexis-codec-json` needs `orexis-capability-sensing` because it
implements sensing's `Codec`, and says so — and a dependency list is only worth reading if
something holds it to the imports. Nothing did, and two errors were sitting in the root's list
the day this was written: `requests`, depended on and imported by nothing, and `pyyaml`, imported
by `onboarding/wireviz.py` and declared in the `dev` extra alone, so `orexis-wireviz` raised
ModuleNotFoundError on any install that was not a developer's. Neither is exotic; both are
invisible without a test, because a dependency you do not need is silent and a deferred import
of one you forgot only fails when the branch runs.

So this asserts EQUALITY, in both directions. A missing dependency is a crash somebody else
gets; an extra one is a claim nobody checks that grows into a supply chain nobody audits.

The module-to-distribution map is `importlib.metadata.packages_distributions()` rather than a
table here: a table would be a second place to edit, and the thing it would encode (that `paho`
comes from `paho-mqtt`) is already stated by the installed metadata.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from importlib.metadata import packages_distributions
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGES_ROOT = REPO_ROOT / "packages"

#  The trees this repository's own distribution ships. An import of one is a dependency on
#  `orexis` and not on anything third-party.
OWN_TREES = {"assembly", "agent", "onboarding"}
ROOT_DIST = "orexis"

#  THE LAYERS, IN ORDER, spelled ONCE. The kernel is three packages in the one tree — the
#  reactive loop, then progression, then deliberation, and no floor beneath them — and `agent/`
#  is the container that assembles them (a-layer-is-a-package-and-need-loads-it, #452). A
#  layer imports only families strictly EARLIER in this tuple; the container may import all
#  of them; a capability may import any layer's contract. `test_layering.py` holds every one
#  of those arrows and reads the order from here. The carve-outs are by FAMILY, never by
#  name: a layer is `orexis-agent-<layer>`, the family `agent` grouping the three in a listing
#  and the member being the row — one package each, not a family with members — so a capability can
#  never slip in by being listed. The pull (#455) derives the load set for service providers;
#  the LAYERS are still loaded by the root's own declared dependencies, because the kernel
#  imports them directly — which is why the root's list may name them and nothing else under
#  `packages/`.
LAYERS = ("reactive", "progression", "deliberation")


def family_of(pkg: Path) -> str:
    return pkg.name.split("-")[1]


LAYER_FAMILY = "agent"   # `orexis-agent-<layer>`: the family that groups the three in a listing


def member_of(pkg: Path) -> str:
    return pkg.name.split("-", 2)[2] if pkg.name.count("-") >= 2 else ""


def is_layer(pkg: Path) -> bool:
    return family_of(pkg) == LAYER_FAMILY and member_of(pkg) in LAYERS


def normalise(name: str) -> str:
    """PEP 503: one spelling for a distribution, so `paho_mqtt` and `paho-mqtt` compare equal."""
    return re.sub(r"[-_.]+", "-", name).lower()


def package_dirs() -> list[Path]:
    #  ONE level now, and the directory name IS the distribution name. A leading `.` or `_` is
    #  not a package, which is what keeps `__pycache__` from being one.
    return sorted(p for p in PACKAGES_ROOT.glob("*")
                  if p.is_dir() and not p.name.startswith((".", "_")))


def dist_name(pkg: Path) -> str:
    """The directory IS the distribution. Nothing is derived, so nothing can disagree."""
    return normalise(pkg.name)


def module_name(pkg: Path) -> str:
    return pkg.name.replace("-", "_")


def declared(pyproject: Path) -> set[str]:
    """The distributions a project depends on, names only — versions and markers stripped."""
    config = tomllib.loads(pyproject.read_text())
    out = set()
    for spec in config["project"].get("dependencies", []):
        out.add(normalise(re.split(r"[<>=!~\[;\s]", spec, maxsplit=1)[0]))
    return out


def imported(paths: list[Path]) -> set[str]:
    """Every top-level module name imported absolutely by these files."""
    names: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                names.add(node.module.split(".")[0])
    return names


def sources(root: Path) -> list[Path]:
    #  A package's own `test_*.py` is dev-time (a-package-may-test-itself). It imports pytest,
    #  which is the ROOT's dev extra and not a runtime dependency of anything shipped.
    #  A package's own `tests/` is test code, its conftest included: what it imports —
    #  pytest, above all — is the test runner's and not the distribution's to declare.
    return sorted(p for p in root.rglob("*.py")
                  if "__pycache__" not in p.parts and "tests" not in p.parts
                  and not p.name.startswith("test_"))


def needed(root: Path, own_import_root: str | None) -> set[str]:
    """The distributions the Python under `root` actually requires."""
    modules = imported(sources(root))
    out: set[str] = set()
    by_module = packages_distributions()
    for module in sorted(modules):
        if module in sys.stdlib_module_names or module == own_import_root:
            continue
        if module in OWN_TREES:
            out.add(ROOT_DIST)
        else:
            dists = by_module.get(module)
            assert dists, (
                f"{root.relative_to(REPO_ROOT)} imports `{module}`, which no installed "
                f"distribution provides. Install the environment before trusting this test.")
            out.add(normalise(dists[0]))
    return out


def siblings(root: Path) -> set[str]:
    """`orexis_codec_json` imported from elsewhere is a dependency on `orexis-codec-json`."""
    found = set()
    for path in sources(root):
        for match in re.finditer(r"\bpackages\.([a-z_0-9]+)\.([a-z_0-9]+)", path.read_text()):
            family, name = match.groups()
            if (PACKAGES_ROOT / family / name) != root:
                found.add(normalise(f"orexis-{family}-{name}"))
    return found


@pytest.mark.parametrize("pkg", package_dirs(), ids=lambda p: p.name)
def test_every_package_is_a_project(pkg: Path):
    """A package carries its own pyproject, named for where it sits, owning one leaf."""
    pyproject = pkg / "pyproject.toml"
    assert pyproject.is_file(), (
        f"{pkg.relative_to(REPO_ROOT)} has no pyproject.toml. Every package is a project — "
        "see knowledge/runbooks/add-a-package.md.")
    config = tomllib.loads(pyproject.read_text())
    module = module_name(pkg)
    assert normalise(config["project"]["name"]) == dist_name(pkg), (
        f"{pkg.name}: the directory IS the distribution name. One string, so a package cannot "
        "be filed under one family and published under another.")
    assert config["tool"]["setuptools"]["packages"] == [module], (
        f"{pkg.name} must claim exactly `{module}` — its own top-level module, and only its own.")
    parts = pkg.name.split("-")
    assert len(parts) >= 3 and parts[0] == "orexis", (
        f"{pkg.name} must be named `orexis-<family>-<name>`: the family is the second segment, "
        "and since the family directory went, that segment is the only place it is stated.")
    assert config["project"]["description"].strip(), "a project says what it is"


@pytest.mark.parametrize("pkg", package_dirs(), ids=lambda p: p.name)
def test_a_package_declares_exactly_what_it_imports(pkg: Path):
    #  A sibling needs no special case any more: `orexis_capability_sensing` is an ordinary
    #  top-level module, so `packages_distributions()` resolves it exactly like `paho`.
    want = needed(pkg, own_import_root=module_name(pkg))
    have = declared(pkg / "pyproject.toml")
    assert have == want, (
        f"{pkg.relative_to(REPO_ROOT)}/pyproject.toml is out of step with its imports.\n"
        f"  missing: {sorted(want - have) or 'none'}\n"
        f"  unused:  {sorted(have - want) or 'none'}")


#  ONBOARDING REACHES INTO THREE PACKAGES, and this is the count of record (#426).
#
#  It was invisible until the packages became top-level modules: the scan skipped anything
#  under `packages.`, so the root's imports of them never reached the comparison. They are not
#  declared as dependencies, and deliberately not — `orexis` depending on a package that
#  depends on `orexis` is a cycle, and worse, it would break the image's dependency-first layer,
#  where `pip install -e .` runs before any package directory has been copied.
#
#  The real fix is for onboarding to read these facts off the graph rather than out of Python,
#  which is rule 1 applied to the operator's tools. Until then this holds the line: a NEW one
#  fails, and one that stops occurring fails too, so the number can only fall to zero.
ONBOARDING_REACHES_IN = {
    ("onboarding/mqtt.py", "orexis_capability_reporting"),      # the sovereign's identity
    ("onboarding/mqtt.py", "orexis_capability_market"),         # the market's topic namespace
    ("onboarding/ask.py", "orexis_capability_reporting"),       # the sovereign's identity
    ("onboarding/validate.py", "orexis_capability_sensing"),    # regions_of, deferred
}


def test_the_root_trees_reach_into_exactly_the_packages_on_record():
    """A ratchet, not a permission. See #426.

    The LAYERS are not on this record and not held by it: the container importing the mind's
    stores, the loop, progression or the search is the layering working, not the root reaching
    into a grant — and onboarding reaching into the search for `effects` and `affordances_of`
    is the same reach it made when those lived in `agent/`. What keeps that carve-out narrow
    is `test_layering.py`, which holds each layer to importing only the layers beneath it.
    """
    modules = {p.name.replace("-", "_") for p in package_dirs() if not is_layer(p)}
    found = {
        (str(path.relative_to(REPO_ROOT)), module)
        for tree in sorted(OWN_TREES)
        for path in sources(REPO_ROOT / tree)
        for module in imported([path]) & modules
    }
    assert found == ONBOARDING_REACHES_IN, (
        "the root trees' reach into packages has changed.\n"
        f"  new (refuse, or move the fact into the graph): {sorted(found - ONBOARDING_REACHES_IN)}\n"
        f"  gone (delete the entry, the ratchet only falls): {sorted(ONBOARDING_REACHES_IN - found)}")


def test_the_root_declares_exactly_what_its_own_trees_import():
    """`orexis` is assembly, the kernel and the operator's tools — and nothing else.

    The direction that catches most is `unused`: a dependency stops being needed when the last
    import of it goes, and nothing about deleting a line of Python makes anyone open this file.
    """
    want = set()
    for tree in sorted(OWN_TREES):
        want |= needed(REPO_ROOT / tree, own_import_root=tree)
    want.discard(ROOT_DIST)
    #  The packages onboarding reaches into are held by the ratchet above, not declared here —
    #  the cycle and the image layer are why. That test is what keeps this exclusion honest.
    #  The LAYERS are the exception on both counts: the root declares them, knowingly a cycle,
    #  and the Containerfile installs the five editables together so the image layer survives.
    want -= {p.name for p in package_dirs() if not is_layer(p)}
    have = declared(REPO_ROOT / "pyproject.toml")
    assert have == want, (
        "pyproject.toml is out of step with what agent/, assembly/ and onboarding/ import.\n"
        f"  missing: {sorted(want - have) or 'none'}\n"
        f"  unused:  {sorted(have - want) or 'none'}")


def test_the_root_distribution_claims_no_package():
    """Each package installs itself; the root claiming `packages*` would shadow all of them."""
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    include = config["tool"]["setuptools"]["packages"]["find"]["include"]
    assert not [p for p in include if p.startswith("packages")], (
        "the root distribution must not claim `packages*` — it would install a copy of every "
        "package under its own name, and an out-of-tree package could never join the namespace.")


def test_the_workspace_holds_every_package():
    """`uv sync --all-packages` must reach all of them, so the glob has to actually match."""
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    members = config["tool"]["uv"]["workspace"]["members"]
    matched = {p for pattern in members for p in REPO_ROOT.glob(pattern) if p.is_dir()}
    assert matched == set(package_dirs()), (
        f"the workspace glob {members} misses "
        f"{sorted(p.name for p in set(package_dirs()) - matched)}")


@pytest.mark.parametrize("pkg", package_dirs(), ids=lambda p: p.name)
def test_packages_is_a_plain_directory_and_not_a_module(pkg: Path):
    """`packages/` is somewhere to keep projects, not somewhere to import from.

    This test used to assert that `packages/` and `packages/<family>/` carried no `__init__.py`,
    because twenty-two distributions shared a namespace across them. There is no shared namespace
    now — each package owns a top-level module of its own — and the family directory is gone, so
    the old form checked `packages/__init__.py` twice and said nothing about the shape that
    replaced it. It passed the whole time (a-package-is-its-name).

    What is still worth refusing: an `__init__.py` at `packages/` would make it a module again,
    and every project below would become one distribution's property.
    """
    assert not (PACKAGES_ROOT / "__init__.py").exists(), (
        "packages/__init__.py must not exist — `packages/` is a directory of projects, and "
        "each package's module is top-level and its own.")
    assert (pkg / "__init__.py").is_file(), "a package's own manifest is a regular module"
    assert pkg.name.count("-") >= 2 and pkg.name.startswith("orexis-"), (
        f"{pkg.name}: a package directory IS its distribution name, `orexis-<family>-<name>`.")


@pytest.mark.parametrize("family", LAYERS)
def test_every_layer_is_there_to_carve_out(family: str):
    """The guard on the carve-out: `is_layer` excuses a family from two ratchets above, and a
    family with no member would excuse nothing while looking as if it did."""
    assert [p for p in package_dirs() if is_layer(p) and member_of(p) == family], (
        f"no package of the `{family}` family under packages/ — that layer moved or was "
        "renamed, and the carve-outs in this file and test_layering.py now cover nothing.")
