---
type: Decision
title: Every package is a project, and a dependency is declared by whoever imports it
description: >-
  One distribution held one dependency list for twenty-four trees, so nothing could say which
  tree needed what. Four defects were sitting in that list unseen — a dependency imported by
  nobody, one imported and declared dev-only, one imported in nine places and declared nowhere,
  and one declared by the root on a package's behalf. Decided: each package under `packages/`
  is its own project with its own dependencies, `packages/` and `packages/<family>/` become
  PEP 420 namespace portions claimed by nobody, and a test holds every list to the imports in
  both directions. The image boundary is untouched — it never was packaging's.
status: accepted
timestamp: 2026-08-27T19:00:00Z
---

# What was true before

One distribution. The root's `[tool.setuptools.packages.find]` claimed `packages*` along with the
other three trees, an `__init__.py` at `packages/` and at each of four families made every level
a regular package, and one `dependencies` list served `assembly/`, `agent/`, `onboarding/` and all
twenty-one packages at once. A package that needed something third-party declared an **extra on
the root**, named for the capability that needed it, and imported it inside `provides()`.

That arrangement was not careless — it was the deliberate outcome of
[repository-layout](/decisions/repository-layout.md), which collapsed two pyprojects into one
because the two had **pretended to draw a boundary they did not enforce**. Nothing here installs
from an index, so what actually kept the operator's tools out of an agent image was the
`Containerfile` not naming `onboarding/`. That reasoning was right and is not reversed below.

What went wrong is that "one distribution" was then applied to a different question. A boundary
and a dependency graph are not the same thing, and the second one had no way to exist.

# What the single list hid

Four defects, none exotic, all found within a minute of asserting the lists against the imports —
which is the argument for this change more than any principle is:

- **`requests>=2.31`** was declared and imported by nothing anywhere in the repository.
- **`pyyaml`** was imported by the WireViz generator, since removed unused, and was declared in the `dev` extra alone,
  so `orexis-wireviz` raised `ModuleNotFoundError` on any install that was not a developer's. The
  import is deferred inside a function, so it failed only when that branch ran — the same shape
  as the deferred import that crash-looped every agent for four merges
  ([a-deferred-import-is-code-no-test-runs](/decisions/a-deferred-import-is-code-no-test-runs.md)).
- **`rdflib`** is imported directly in nine places across `assembly/`, `agent/` and
  `onboarding/`, and was declared nowhere. It arrived only as a transitive of `pyshacl`, which is
  free to drop it or re-pin it at any release.
- **`pyoxigraph`** is imported by `packages/orexis-capability-sensing/module.py`, and was declared by the
  root on that package's behalf.

A dependency you do not need is silent. A dependency you forgot is silent until the branch runs.
Neither is visible while one list stands for twenty-four trees, because there is nothing to
compare it against.

# What is decided

**Every package is a project.** `packages/orexis-<family>-<name>/pyproject.toml`, distribution
`orexis-<family>-<name>`, import name `packages.<family>.<name>`, and its own `dependencies`.
Twenty-two distributions where there was one.

**`packages/` and `packages/<family>/` are claimed by nobody.** They are PEP 420 namespace
portions, and the five `__init__.py` files that made them regular packages are deleted. Each
distribution claims exactly its own leaf. That is the whole mechanism by which a twenty-second
package, installed from another repository, lands in the same namespace as these twenty-one —
measured before the change was written, with two probe distributions built and installed into a
throwaway environment.

**A dependency is declared by whoever imports it, and the test asserts EQUALITY in both
directions.** `tests/test_projects.py` walks each project's Python with `ast`, maps module names
to distributions with `importlib.metadata.packages_distributions()` rather than a table, and
fails on a missing dependency and on an unused one alike. An unused dependency is a claim nobody
checks, which is how a supply chain stops being audited.

**The root depends on no package.** `orexis` is assembly, the kernel and the operator's tools.
That the kernel needs no package was already a claim
([the-mind-is-not-a-package](/decisions/the-mind-is-not-a-package.md)) and a test
(`test_the_kernel_stands_alone_with_no_packages_at_all`); it is now also the shape of the
install.

**uv is the ergonomics, pip is the mechanism.** `[tool.uv.workspace]` makes `uv sync
--all-packages` resolve a sibling dependency to its directory, but every member is an ordinary
PEP 621 project: the `Containerfile` installs them with one `pip install -e . $(ls -d
packages/*/*/)` and nothing at run time knows uv exists.

# What the earlier reasoning got right

[repository-layout](/decisions/repository-layout.md) refused per-package pyprojects **and** entry
points in one breath, and only the first half is reversed here. Its second argument was that entry
points would be *a registry in metadata against the found-by-looking commitment* — and that
stands: nothing below discovers a package by entry point, the loader still walks the tree, and
the day that changes it will be for the seam at the bottom of this record and not for
convenience. Its third was that **the loader is this project's package manager**, managing what
pip cannot — ontologies, shapes, rules, affordances. Also unchanged. A `pyproject.toml` adds the
one thing pip *can* manage and the loader never could: who needs what.

# What did not change

- **The image boundary.** `onboarding/` still ships inside the `orexis` distribution beside
  `agent/`, and what keeps it out of an image is still the `Containerfile` not naming the tree,
  with `lint-imports` holding the direction. Twenty-two distributions are a dependency graph, not
  a boundary, and reading them as one would repeat the exact mistake
  [repository-layout](/decisions/repository-layout.md) corrected.
- **The loader.** Discovery is still a filesystem walk of `packages/`. Nothing about the split
  needed it to change, and the seam below says what would.
- **"Adding a package is adding a directory"** — now a directory and one twenty-line file, which
  is a real cost and is stated rather than waved away. It buys a package that can declare what it
  needs, be built alone, and be developed in another repository.

# Seams left open

- **An out-of-tree package can be imported but not enumerated.** Measured, not assumed:
  `packages.__path__` under an editable install holds setuptools *finder hooks* rather than
  directories, and `pkgutil.iter_modules` over it returns `[]`. So `importlib` resolves
  `packages.transport.foo` by name while nothing can discover that it exists. **Entry points are
  the standard answer** and are how a third-party package will eventually announce itself; until
  then, an external package is found only if its directory is inside the tree (#424).
- ~~**`packages` is a very general top-level namespace to ask an external developer to share.**~~
  Closed by [a-package-is-its-name](/decisions/a-package-is-its-name.md): the tree went flat, the
  shared import root went with it, and each package owns a top-level module named for its own
  distribution. There is no namespace to share any more.
- **Versions all read `0.1.0` and move together.** Nothing is released independently, so nothing
  yet needs a version that means anything.
- **The agent image still installs onboarding's dependencies** — `influxdb-client`, `paho-mqtt`
  and `pyyaml` — because the root is one project and the image installs it. The *code* is absent,
  which is what the boundary is about; the wheels are not. Pre-existing, and unchanged.
