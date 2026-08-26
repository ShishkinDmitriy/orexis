"""Every import inside a function resolves — because nothing else looks at one.

An import at the top of a module is checked by the first test that imports the module, which is
every test. An import inside a FUNCTION is checked only when that function runs, and a function
that runs solely in a container runs in no test at all.

`packages/capability/reporting/module.py` held `from agent.influx_writer import InfluxWriter`,
deferred with the note *"nothing built for a test agent"*. `metrics-are-an-aspect` moved that
module into the reporting package as `series.py`; the deferred line was not repointed, and the
class was already imported at the top of the same file. So the line was dead wrong, unreachable
from the suite, and fatal in production — reporting is the capability every agent holds, so
`StoringModule.start()` raised `ModuleNotFoundError` for every agent in every world, which
restarted, and crash-looped. `pytest` was green, `orexis-validate` passed all three worlds, and
`lint-imports` had nothing to say because the layering was fine; only booting a world showed it.

This walks the AST rather than executing anything, so a deferred import stays deferred.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import pathlib
import subprocess

SHIPPED = ("agent/", "packages/", "onboarding/")


def _resolves(module: str, name: str) -> bool:
    """`from x import y` where y may be an attribute OR a submodule x.y not yet loaded."""
    try:
        loaded = importlib.import_module(module)
    except Exception:
        return False
    if name == "*" or hasattr(loaded, name):
        return True
    try:
        return importlib.util.find_spec(f"{module}.{name}") is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _found(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def test_every_deferred_import_resolves():
    files = [f for f in subprocess.run(["git", "ls-files", "*.py"], capture_output=True,
                                       text=True, check=True).stdout.split()
             if f.startswith(SHIPPED)]
    assert files, "no shipped Python found — the `git ls-files` filter stopped matching"

    broken, seen = [], 0
    for path in files:
        tree = ast.parse(pathlib.Path(path).read_text(), path)
        functions = [n for n in ast.walk(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for node in (n for fn in functions for n in ast.walk(fn)):
            #  A RELATIVE deferred import (`from .series import X`) is skipped: resolving one
            #  needs the importing module's package, and every one in this tree is a sibling
            #  the module-level imports already reach. The line that broke was absolute.
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                seen += 1
                if not _found(node.module):
                    broken.append(f"{path}:{node.lineno}  from {node.module} import "
                                  + ", ".join(a.name for a in node.names) + "  — no such module")
                    continue
                broken += [f"{path}:{node.lineno}  {node.module}.{a.name} — no such name"
                           for a in node.names if not _resolves(node.module, a.name)]
            elif isinstance(node, ast.Import):
                seen += 1
                broken += [f"{path}:{node.lineno}  import {a.name} — no such module"
                           for a in node.names if not _found(a.name.split(".")[0])]

    assert seen, "no deferred imports found at all — the AST walk stopped matching"
    assert not broken, (
        "a deferred import that does not resolve — nothing else in the suite executes one, and "
        "the last of these crash-looped every agent in every world:\n  " + "\n  ".join(broken))
