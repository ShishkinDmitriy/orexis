"""The root distribution declares exactly what its own trees import, and each unit its own: the core is the
kernel's, and a package that needs a library brings it as an extra named for its directory
(knowledge/decisions/a-package-brings-its-own-dependencies.md), in a `dependencies.txt` beside it, which
the pyproject reads; a package with none is the core's.

`orexis` is one distribution: the agent, the operator's tools and the simulator. What keeps its
dependency list worth reading is something holding it to the imports. Nothing did once, and two
errors sat in the list the day the first version of this test was written: `requests`, depended
on and imported by nothing, and `pyyaml`, imported by an operator's tool and declared in the
`dev` extra alone, so the tool raised ModuleNotFoundError on any install that was not a
developer's. Neither is exotic; both are invisible without a test, because a dependency you do
not need is silent and a deferred import of one you forgot only fails when the branch runs.

So this asserts EQUALITY, in both directions. A missing dependency is a crash somebody else
gets; an extra one is a claim nobody checks that grows into a supply chain nobody audits.

The module-to-distribution map is `importlib.metadata.packages_distributions()` rather than a
table here: a table would be a second place to edit, and the thing it would encode (that `paho`
comes from `paho-mqtt`) is already stated by the installed metadata.

It held twenty-five distributions to their imports too, one per 0.1.0 package, until 0.1.0 was
retired and its packages with it; Agent 0.2.0's packages are directories of the one tree.
"""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from importlib.metadata import packages_distributions
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#  The trees this repository's own distribution ships. An import of one is an import of
#  `orexis` itself and not a dependency on anything third-party.
OWN_TREES = {"documents", "onboarding", "simulation"}


def normalise(name: str) -> str:
    """PEP 503: one spelling for a distribution, so `paho_mqtt` and `paho-mqtt` compare equal."""
    return re.sub(r"[-_.]+", "-", name).lower()


def declared(pyproject: Path) -> set[str]:
    """The distributions a project depends on, names only — versions and markers stripped."""
    config = tomllib.loads(pyproject.read_text())
    return {normalise(re.split(r"[<>=!~\[;\s]", spec, maxsplit=1)[0])
            for spec in config["project"].get("dependencies", [])}


def imported(paths: list[Path]) -> set[str]:
    """Every top-level module name imported absolutely by these files."""
    names: set[str] = set()
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                names.add(node.module.split(".")[0])
    return names


def sources(root: Path) -> list[Path]:
    """The shipped Python under `root`: a test and a conftest are the runner's, and what they
    import — pytest above all — is the `dev` extra's and not the distribution's to declare."""
    return sorted(p for p in root.rglob("*.py")
                  if "__pycache__" not in p.parts and "tests" not in p.parts
                  and not p.name.startswith("test_") and p.name != "conftest.py")


def needed(root: Path | list[Path]) -> set[str]:
    """The third-party distributions the Python under `root`, or in the files listed, actually requires."""
    out: set[str] = set()
    by_module = packages_distributions()
    for module in sorted(imported(sources(root) if isinstance(root, Path) else root)):
        if module in sys.stdlib_module_names or module in OWN_TREES:
            continue
        dists = by_module.get(module)
        assert dists, (f"`{module}` is imported and no installed distribution provides it. Install the "
                       f"environment, `pip install -e '.[dev]'`, before trusting this test.")
        out.add(normalise(dists[0]))
    return out


def _specs(specs) -> set[str]:
    """Distribution names off requirement specs, versions stripped, the distribution's own extras apart."""
    return {normalise(re.split(r"[<>=!~\[;\s]", spec, maxsplit=1)[0]) for spec in specs
            if not normalise(spec).startswith("orexis[")}


def extras(pyproject: Path) -> dict[str, set[str]]:
    """Each extra the distribution declares and what it brings, read off its unit's own file."""
    out = {}
    for name, path in dependency_files(pyproject).items():
        lines = [line.split("#", 1)[0].strip() for line in (REPO_ROOT / path).read_text().splitlines()]
        out[name] = _specs([line for line in lines if line])
    return out


#  WHAT BOTH PROGRAMS SHARE: the core is its imports, and each program brings the rest as its extra.
CORE = REPO_ROOT / "documents"
DEPENDENCIES = "dependencies.txt"


def dependency_files(pyproject: Path) -> dict[str, str]:
    """Each extra the distribution declares, by the one file it is read from."""
    config = tomllib.loads(pyproject.read_text())["tool"]["setuptools"]["dynamic"]["optional-dependencies"]
    return {name: entry["file"][0] for name, entry in config.items()}


def units() -> dict[str, tuple[list[Path], str]]:
    """Each program that may bring a library of its own, by its extra, with its sources and its dependency file."""
    return {tree: (sources(REPO_ROOT / tree), f"{tree}/{DEPENDENCIES}") for tree in ("simulation", "onboarding")}


def test_no_python_is_left_in_the_agent():
    """The agent is the binary, and a `.py` in a crate is a second agent starting."""
    crates = [c for c in REPO_ROOT.glob("orexis*") if (c / "Cargo.toml").is_file()]
    assert crates, "no crate found at the root — this test is not looking"
    assert not [p for c in crates for p in c.rglob("*.py") if "__pycache__" not in p.parts]


def test_the_core_declares_exactly_what_the_kernel_imports():
    """The direction that catches most is `unused`: a dependency stops being needed when the last import
    of it goes, and nothing about deleting a line of Python makes anyone open the pyproject. The core is
    what the two programs share, so either installs nothing of the other's."""
    kernel = sorted(CORE.glob("*.py"))
    assert kernel, "the core's glob stopped matching"
    want, have = needed(kernel), declared(REPO_ROOT / "pyproject.toml")
    assert have == want, ("the core is out of step with what documents/*.py imports.\n"
                          f"  missing: {sorted(want - have) or 'none'}\n  unused:  {sorted(have - want) or 'none'}")


def test_every_unit_brings_exactly_what_it_imports_beyond_the_core_as_its_own_extra():
    """A package that needs a library declares it as its extra, and only it does: an extra holds what its
    unit imports beyond the core, both ways, and a unit that needs nothing beyond the core has none."""
    core, declared_extras, found = declared(REPO_ROOT / "pyproject.toml"), extras(REPO_ROOT / "pyproject.toml"), units()
    assert {"simulation", "onboarding"} <= set(found), sorted(found)

    files = dependency_files(REPO_ROOT / "pyproject.toml")
    wrong = {}
    for name, (sources_of, beside) in sorted(found.items()):
        want, have = needed(sources_of) - core, declared_extras.get(name, set())
        if want != have:
            wrong[name] = {"missing": sorted(want - have), "unused": sorted(have - want)}
        if name in files and files[name] != beside:
            wrong[name] = {"file": f"{files[name]}, where it belongs beside its unit: {beside}"}
        if (REPO_ROOT / beside).exists() != (name in files):
            wrong[name] = {"file": f"{beside} {'is' if (REPO_ROOT / beside).exists() else 'is not'} there, and the "
                                   f"pyproject {'does not read' if name not in files else 'reads'} it"}
    assert not wrong, f"an extra is out of step with what its unit imports beyond the core: {wrong}"
    assert set(declared_extras) - {"dev"} <= set(found), f"an extra names no unit: {sorted(set(declared_extras) - {'dev'} - set(found))}"


def test_a_developers_install_carries_every_units_extra():
    """`dev` installs every unit's extra, so a developer's environment and CI run every test of every
    program."""
    files = dependency_files(REPO_ROOT / "pyproject.toml")
    dev = [line.split("#", 1)[0].strip() for line in (REPO_ROOT / files["dev"]).read_text().splitlines()]
    carried = {name for spec in dev if normalise(spec).startswith("orexis[")
               for name in spec[spec.index("[") + 1:spec.index("]")].split(",")}
    assert carried == set(files) - {"dev"}, sorted(carried)


def test_the_distribution_ships_exactly_its_own_trees():
    """What `setuptools` finds is what the image and a fresh install carry: the three trees and
    nothing a retired kernel left behind."""
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    include = config["tool"]["setuptools"]["packages"]["find"]["include"]
    assert {pattern.rstrip("*") for pattern in include} == OWN_TREES
