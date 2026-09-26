"""The root distribution declares exactly what its own trees import.

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
OWN_TREES = {"agent", "onboarding", "simulation"}


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


def needed(root: Path) -> set[str]:
    """The third-party distributions the Python under `root` actually requires."""
    out: set[str] = set()
    by_module = packages_distributions()
    for module in sorted(imported(sources(root))):
        if module in sys.stdlib_module_names or module in OWN_TREES:
            continue
        dists = by_module.get(module)
        assert dists, (f"{root.relative_to(REPO_ROOT)} imports `{module}`, which no installed "
                       f"distribution provides. Install the environment before trusting this test.")
        out.add(normalise(dists[0]))
    return out


def test_the_root_declares_exactly_what_its_own_trees_import():
    """The direction that catches most is `unused`: a dependency stops being needed when the
    last import of it goes, and nothing about deleting a line of Python makes anyone open the
    pyproject."""
    assert all((REPO_ROOT / tree).is_dir() for tree in OWN_TREES), "a shipped tree moved"
    want = set().union(*(needed(REPO_ROOT / tree) for tree in sorted(OWN_TREES)))
    have = declared(REPO_ROOT / "pyproject.toml")
    assert have == want, (
        "pyproject.toml is out of step with what agent/, onboarding/ and simulation/ import.\n"
        f"  missing: {sorted(want - have) or 'none'}\n"
        f"  unused:  {sorted(have - want) or 'none'}")


def test_the_distribution_ships_exactly_its_own_trees():
    """What `setuptools` finds is what the image and a fresh install carry: the three trees and
    nothing a retired kernel left behind."""
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    include = config["tool"]["setuptools"]["packages"]["find"]["include"]
    assert {pattern.rstrip("*") for pattern in include} == OWN_TREES
