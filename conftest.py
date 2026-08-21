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


# --- carrying the verdict out of a worker -----------------------------------------------------
#
# Issue #271. Everything above lives in the process that RUNS the test, and under `-n auto` that
# is a worker rather than the session the exit status comes from. A worker detected a vacuous
# test correctly and then lost the verdict twice: `session.exitstatus = 1` is not propagated,
# because the controller computes its own from test reports and every report says PASSED; and the
# printed lines went to a stdout xdist discards on a passing run — invisible even under
# `-n 1 --capture=no`. Meanwhile the controller ran no tests, so its own `_asserts_run` was empty
# and it returned early. The guard did not weaken under xdist, it stopped existing, and every
# distribution mode was equally dead: `-n 0` kept it, one worker killed it.
#
# So a worker hands its tally up `workeroutput` — a dict execnet ships back — and the controller
# SUMS the tallies before judging. Summing is the load-bearing word. The verdict is per FUNCTION
# across all its cases, and `--dist load` splits a parametrised function's cases across workers,
# so no single worker's tally is a verdict about anything: `test_queries_use_only_declared_prefixes`
# is parametrised over every source file and legitimately asserts nothing for the ones with no
# queries, so a worker holding only those would report zero and be believed. That is the
# 54-false-positive failure #106 was careful to avoid, and it would have come back through the
# side door.
#
# Pinning `--dist loadfile` would also keep a function's cases together, and is not the fix: it
# constrains the distribution to protect the guard, when the guard can simply be right.

_asserts_from_workers: dict[str, int] = {}


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node, error):
    """Controller side: fold one finished worker's tally into the running total.

    `optionalhook` because this hookspec only exists when xdist is installed. Without it pytest
    refuses to load a conftest declaring a hook it has never heard of, and a serial run would
    fail on a plugin it is not using.
    """
    tally = getattr(node, "workeroutput", {}).get("asserts_run") or {}
    for key, count in tally.items():
        _asserts_from_workers[key] = _asserts_from_workers.get(key, 0) + count


def pytest_sessionfinish(session, exitstatus):
    """Fail the run for any at-risk test whose assertions never executed, in any case.

    Reported here rather than per test because the verdict needs every parametrised case to have
    run first. A function that asserted nothing across all of them is checking nothing at all.

    Runs in three situations and does two different jobs. In a WORKER it only hands its tally up
    and judges nothing, because it has seen an arbitrary subset of the cases. In the CONTROLLER,
    or in a serial run, it judges — over the sum of what the workers reported plus whatever ran
    in this process, which is everything when serial and nothing when not.
    """
    output = getattr(session.config, "workeroutput", None)
    if output is not None:
        output["asserts_run"] = _asserts_run
        return

    totals = dict(_asserts_from_workers)
    for key, count in _asserts_run.items():
        totals[key] = totals.get(key, 0) + count

    silent = sorted(k for k, n in totals.items() if n == 0)
    if not silent:
        return
    session.exitstatus = 1
    print("\n\nTESTS THAT ASSERTED NOTHING (issue #106):")
    for key in silent:
        print(f"  {key}")
    print("  Their assertions sit inside a loop that ran zero times — the collection walked is\n"
          "  empty, so the test is green and checks nothing.\n")
