"""`tree`: the agent tree's own layout, read by looking — which directories are packages, which packages a
package's code imports, and what an image of some of them keeps — and the image build's one step.

**A PACKAGE IS A DIRECTORY HOLDING AN `ontology.ttl`**, its tests' apart, as `runtime.every_package` finds them;
a directory holding packages and no ontology is a family, `transport/`, whose own files every member shares.

**AN IMAGE KEEPS THE KERNEL AND ITS AGENT'S PACKAGES, AND NOTHING ELSE OF `agent/`**
(knowledge/decisions/a-package-brings-its-own-dependencies.md): every entry of the tree that is no package —
the kernel's modules, `history/`, `metrics/` — every family's own files, and each package named, whole. What
`orexis-compose` mounts into an agent's container is the same list, so a code change still needs a restart and
no rebuild, and the container holds no code its agent does not run.

**THE STANDARD LIBRARY ALONE**, since the image build runs `python -m agent.tree` in a stage where nothing is
installed: it lays out what the image copies — the trees kept, and the distribution's metadata with every
package's dependency file, which setuptools reads to know the extras.
"""

from __future__ import annotations

import ast
import shutil
import sys
import tomllib
from pathlib import Path

KERNEL = Path(__file__).resolve().parent
ONTOLOGY = "ontology.ttl"
#  WHERE A PACKAGE SAYS WHAT IT BRINGS: beside its ontology, a requirements file; a package with none is the
#  core's, bringing nothing.
DEPENDENCIES = "dependencies.txt"
_SKIPPED = {"__pycache__", "tests"}


def packages(root: Path = KERNEL) -> list[str]:
    """Every package of the tree under `root`, by its path from it: each directory holding an ontology."""
    return sorted(p.parent.relative_to(root).as_posix() for p in root.rglob(ONTOLOGY)
                  if p.parent != root and not _SKIPPED & set(p.relative_to(root).parts))


def imported(sources: list[Path], every: set[str]) -> set[str]:
    """The packages of `every` whose code these files import, by the `agent.<package>` modules they name."""
    out: set[str] = set()
    for path in sources:
        for node in ast.walk(ast.parse(path.read_text())):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module] if isinstance(node, ast.ImportFrom) and node.module and not node.level else [])
            for name in names:
                parts = name.split(".")
                if parts[0] == "agent":
                    out |= {"/".join(parts[1:n]) for n in range(2, len(parts) + 1)} & every
    return out


def sources(directory: Path) -> list[Path]:
    """The Python a directory ships, its tests apart."""
    return sorted(p for p in directory.rglob("*.py") if not _SKIPPED & set(p.relative_to(directory).parts))


def closed(named, root: Path = KERNEL) -> list[str]:
    """`named` with every package whose code they import, and theirs: planning runs belief's transition machine,
    so an image of planning holds belief."""
    every, seen, todo = set(packages(root)), set(), list(named)
    while todo:
        package = todo.pop()
        if package in seen:
            continue
        seen.add(package)
        todo += sorted(imported(sources(root / package), every) - seen)
    return sorted(seen)


def kept(named, root: Path = KERNEL) -> list[str]:
    """The entries of the tree under `root` an image of the packages `named` holds, by their path from it: every
    entry that is no package and holds none, a family's own files, and each package named, whole — the runner's
    tests and conftest beside the kernel and a family apart."""
    every, keep = set(packages(root)), set(named)
    out: list[str] = []

    def walk(directory: Path) -> None:
        for child in sorted(directory.iterdir()):
            rel = child.relative_to(root).as_posix()
            if child.name in _SKIPPED or child.name == "conftest.py":
                continue                                             # what the runner reads, never the agent
            if child.is_dir() and rel in every:
                if rel in keep:
                    out.append(rel)
            elif child.is_dir() and any(p.startswith(rel + "/") for p in every):
                walk(child)                                          # a family: its own files, its kept members
            else:
                out.append(rel)

    walk(root)
    return out


def dependency_files(pyproject: Path) -> dict[str, str]:
    """Each extra the distribution declares, and the file it is read from."""
    config = tomllib.loads(pyproject.read_text())
    table = config.get("tool", {}).get("setuptools", {}).get("dynamic", {}).get("optional-dependencies", {})
    return {name: spec["file"][0] if isinstance(spec["file"], list) else spec["file"] for name, spec in table.items()}


def lay_out(source: Path, out: Path, named, simulator: bool) -> None:
    """What the image copies, laid out under `out`: `deps/`, the distribution's metadata and the dependency file
    of each unit the image holds — setuptools passes over, with a warning, an extra whose file is not there,
    which is every unit this image holds none of, onboarding's above all — and `trees/`, the agent tree as
    `kept` keeps it, the domains, and the simulator where the image is its."""
    deps, trees = out / "deps", out / "trees"
    deps.mkdir(parents=True)
    shutil.copy2(source / "pyproject.toml", deps / "pyproject.toml")
    held = {f"agent/{rel}" for rel in kept(named, source / "agent")} | ({"simulation"} if simulator else set())
    for path in dependency_files(source / "pyproject.toml").values():
        if (source / path).exists() and any(path == h or path.startswith(h + "/") for h in held):
            (deps / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / path, deps / path)
    for rel in kept(named, source / "agent"):
        src, dst = source / "agent" / rel, trees / "agent" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, dst)
    shutil.copytree(source / "domains", trees / "domains", ignore=shutil.ignore_patterns("__pycache__"))
    if simulator:
        shutil.copytree(source / "simulation", trees / "simulation", ignore=shutil.ignore_patterns("__pycache__"))


def main(argv: list[str] | None = None) -> int:
    """`python -m agent.tree <source> <out> <packages, comma-separated> <simulator: yes|no>` — the build's step."""
    source, out, named, simulator = (argv if argv is not None else sys.argv[1:])
    lay_out(Path(source), Path(out), [p for p in named.split(",") if p], simulator == "yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
