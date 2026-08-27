"""Every package is a project, and a project declares exactly what it imports.

Twenty-two distributions share one `packages.` namespace. What makes that more than ceremony is
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


def normalise(name: str) -> str:
    """PEP 503: one spelling for a distribution, so `paho_mqtt` and `paho-mqtt` compare equal."""
    return re.sub(r"[-_.]+", "-", name).lower()


def package_dirs() -> list[Path]:
    #  The loader's own rule for what counts as a directory worth looking at: a leading `.`
    #  or `_` is not a package, which is what keeps `__pycache__` from being one.
    return sorted(p for p in PACKAGES_ROOT.glob("*/*")
                  if p.is_dir() and not p.name.startswith((".", "_"))
                  and not p.parent.name.startswith((".", "_")))


def dist_name(pkg: Path) -> str:
    return normalise(f"orexis-{pkg.parent.name}-{pkg.name}")


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
    return sorted(p for p in root.rglob("*.py")
                  if "__pycache__" not in p.parts and not p.name.startswith("test_"))


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
        elif module == "packages":
            continue  # a sibling, resolved from the dotted path below
        else:
            dists = by_module.get(module)
            assert dists, (
                f"{root.relative_to(REPO_ROOT)} imports `{module}`, which no installed "
                f"distribution provides. Install the environment before trusting this test.")
            out.add(normalise(dists[0]))
    return out


def siblings(root: Path) -> set[str]:
    """`packages.codec.json` imported from elsewhere is a dependency on `orexis-codec-json`."""
    found = set()
    for path in sources(root):
        for match in re.finditer(r"\bpackages\.([a-z_0-9]+)\.([a-z_0-9]+)", path.read_text()):
            family, name = match.groups()
            if (PACKAGES_ROOT / family / name) != root:
                found.add(normalise(f"orexis-{family}-{name}"))
    return found


@pytest.mark.parametrize("pkg", package_dirs(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_every_package_is_a_project(pkg: Path):
    """A package carries its own pyproject, named for where it sits, owning one leaf."""
    pyproject = pkg / "pyproject.toml"
    assert pyproject.is_file(), (
        f"{pkg.relative_to(REPO_ROOT)} has no pyproject.toml. Every package is a project — "
        "see knowledge/runbooks/add-a-package.md.")
    config = tomllib.loads(pyproject.read_text())
    leaf = f"packages.{pkg.parent.name}.{pkg.name}"
    assert normalise(config["project"]["name"]) == dist_name(pkg)
    assert config["tool"]["setuptools"]["packages"] == [leaf], (
        f"{pkg.name} must claim exactly `{leaf}` — `packages/` and `packages/{pkg.parent.name}/` "
        "are PEP 420 namespace portions, and a distribution that claims one shuts every other "
        "distribution out of it.")
    assert config["project"]["description"].strip(), "a project says what it is"


@pytest.mark.parametrize("pkg", package_dirs(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_a_package_declares_exactly_what_it_imports(pkg: Path):
    want = needed(pkg, own_import_root=None) | siblings(pkg)
    have = declared(pkg / "pyproject.toml")
    assert have == want, (
        f"{pkg.relative_to(REPO_ROOT)}/pyproject.toml is out of step with its imports.\n"
        f"  missing: {sorted(want - have) or 'none'}\n"
        f"  unused:  {sorted(have - want) or 'none'}")


def test_the_root_declares_exactly_what_its_own_trees_import():
    """`orexis` is assembly, the kernel and the operator's tools — and nothing else.

    The direction that catches most is `unused`: a dependency stops being needed when the last
    import of it goes, and nothing about deleting a line of Python makes anyone open this file.
    """
    want = set()
    for tree in sorted(OWN_TREES):
        want |= needed(REPO_ROOT / tree, own_import_root=tree)
    want.discard(ROOT_DIST)
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


@pytest.mark.parametrize("pkg", package_dirs(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_no_package_carries_an_init_that_makes_it_a_regular_subpackage(pkg: Path):
    """The two levels above a package belong to nobody, which is what PEP 420 buys.

    An `__init__.py` at `packages/` or `packages/<family>/` makes that level a REGULAR package
    owned by whichever distribution ships it, and every other distribution's leaf becomes
    unreachable. It is one file away, and the failure is an ImportError at boot in a container.
    """
    for level in (PACKAGES_ROOT, pkg.parent):
        assert not (level / "__init__.py").exists(), (
            f"{(level / '__init__.py').relative_to(REPO_ROOT)} must not exist — "
            "it would close the namespace these distributions share.")
    assert (pkg / "__init__.py").is_file(), "a package's own manifest is a regular module"
