"""Where the queries live, and where they must not.

Easy to state and easy to lose: a collection asks the question only IT can phrase, and runs
nobody else's. The file these two were carved out of acquired a query text, then a second, then a
question belonging to another collection, and nothing said so.

Asked of the syntax tree rather than of the text, so a docstring may discuss selects while the
code holds none. Two claims, because a guard that only forbids proves nothing: one file AUTHORS
a query and one RUNS a query it is handed.

A third stood here — that the SERVICE between them authored none — until the service turned out
to fetch nothing and decide nothing, and became `Steps.find_all`. See
knowledge/decisions/a-row-is-a-step.md.
"""

from __future__ import annotations

import ast
from pathlib import Path

SPARQL = ("SELECT", "CONSTRUCT", "INSERT", "DELETE", "WHERE {", "GRAPH ")


def _parsed(module: str) -> ast.Module:
    return ast.parse(Path(__file__).with_name(module).read_text())


def _authored_queries(tree: ast.Module) -> list[str]:
    """Query text this module writes down itself — docstrings excluded, since prose is not one."""
    docs = [ast.get_docstring(n, clean=False) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))]
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and not any(n.value is d for d in docs)
            and any(k in n.value.upper() for k in SPARQL)]


def _names(tree: ast.Module) -> set[str]:
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}


def test_the_collection_of_templates_authors_its_own():
    """`Actions` asks the vocabulary what it declares, which is a question only it can phrase."""
    assert _authored_queries(_parsed("actions.py")), "Actions stopped carrying its own query"


def test_the_collection_of_steps_authors_none_and_runs_the_actions():
    """The sharp one, and it is why a step is not an action. `Steps` writes NO query:
    the select it runs is the action's own `orexis:available`, declared by whichever package ships
    the action, bound here and answered against the world this collection was handed. A new way
    of acting is a node in a new directory and never an edit here (#207) — which is exactly what
    it would stop being if this file ever authored a select of its own."""
    tree = _parsed("steps.py")
    assert not _authored_queries(tree), "Steps began writing its own query text"
    assert {"bind", "bindings"} <= _names(tree), \
        "Steps stopped binding and running the action's precondition"
