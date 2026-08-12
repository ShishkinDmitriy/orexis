"""Repo-root conftest: the one check that must reach BOTH test roots.

`tests/` holds the integration suite and a package may carry its own tests beside its code, so a
guard that lives in `tests/conftest.py` covers half of them. This one covers everything pytest
collects, which is what `testpaths` names.

Nothing else belongs here. Fixtures that build a world are the integration suite's and stay with
it — a package test that needs one is a test in the wrong place.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# --- vacuity: a test that asserted nothing passed by doing nothing ----------------------------
#
# Issue #106. A loop over query results that matches nothing runs its body zero times, so every
# assertion inside it is skipped and the test is green — indistinguishable from a test that
# checked a hundred things. It has happened four times: a privacy query dead for four PRs (#79),
# the cadence guard dead for four more (#105), a glob emptied twice, and 143 cases lost in the
# layout move (#113).
#
# WHAT IS CHECKED is the true invariant rather than a proxy: did any `assert` in this test
# actually execute? Not "is the collection non-empty", which every site would spell differently,
# and not a source-text pattern, which cannot know what ran.
#
# PER TEST FUNCTION, not per parametrised case, and that distinction is the whole of getting it
# right. `test_queries_use_only_declared_prefixes` is parametrised over every source file in the
# project and asserts nothing for the ones containing no queries — which is correct, not vacuous.
# Checking each case separately called 54 of those a failure. What is wrong is a function that
# asserted nothing in ANY of its runs.
#
# WHERE it is checked is narrowed by a static scan, because line-tracing every test would cost
# more than the suite. Only tests with an `assert` inside a loop over something that could be
# EMPTY are traced — a loop over a literal tuple cannot be, and is left alone. The list is
# computed on collection, never maintained.

import ast as _ast
import sys as _sys
from functools import lru_cache as _lru_cache

_asserts_run: dict[str, int] = {}


def _cannot_be_empty(node) -> bool:
    """A literal collection, or a call over literals. These loops always run."""
    if isinstance(node, (_ast.Tuple, _ast.List, _ast.Set, _ast.Dict, _ast.Constant)):
        return True
    if isinstance(node, _ast.Call):
        name = getattr(node.func, "id", None)
        if name == "range":
            return True
        if name in ("sorted", "enumerate", "zip", "reversed"):
            return all(_cannot_be_empty(a) for a in node.args)
    if isinstance(node, _ast.Attribute):
        return isinstance(node.value, (_ast.Tuple, _ast.List, _ast.Dict, _ast.Set))
    return False


@_lru_cache(maxsize=None)
def _tests_that_could_assert_nothing(path: str) -> frozenset[str]:
    try:
        tree = _ast.parse(Path(path).read_text())
    except (OSError, SyntaxError):
        return frozenset()
    found = set()
    for fn in _ast.walk(tree):
        if not isinstance(fn, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            continue
        if not fn.name.startswith("test_"):
            continue
        if any(isinstance(node, _ast.For)
               and not _cannot_be_empty(node.iter)
               and any(isinstance(x, _ast.Assert) for x in _ast.walk(node))
               for node in _ast.walk(fn)):
            found.add(fn.name)
    return frozenset(found)


@pytest.fixture(autouse=True)
def _count_assertions_that_ran(request):
    """Trace the at-risk tests, tallying executed asserts per FUNCTION across its cases."""
    path = Path(request.node.fspath)
    base = request.node.name.split("[")[0]
    if base not in _tests_that_could_assert_nothing(str(path)):
        yield
        return

    key = f"{path}::{base}"
    _asserts_run.setdefault(key, 0)
    source = path.read_text().splitlines()
    target = str(path)

    def trace(frame, event, arg):
        if event == "line" and frame.f_code.co_filename == target:
            line = source[frame.f_lineno - 1].strip() if frame.f_lineno <= len(source) else ""
            if line.startswith("assert "):
                _asserts_run[key] += 1
        return trace

    previous = _sys.gettrace()
    _sys.settrace(trace)
    try:
        yield
    finally:
        _sys.settrace(previous)


def pytest_sessionfinish(session, exitstatus):
    """Fail the run for any at-risk test whose assertions never executed, in any case.

    Reported here rather than per test because the verdict needs every parametrised case to have
    run first. A function that asserted nothing across all of them is checking nothing at all.
    """
    silent = sorted(k for k, n in _asserts_run.items() if n == 0)
    if not silent:
        return
    session.exitstatus = 1
    print("\n\nTESTS THAT ASSERTED NOTHING (issue #106):")
    for key in silent:
        print(f"  {key}")
    print("  Their assertions sit inside a loop that ran zero times — the collection walked is\n"
          "  empty, so the test is green and checks nothing.\n")
