"""Where the queries live, and where they must not.

The sovereign's line when this shape was settled: a service is the GLUE between collections, with
the logic in it and the queries out of it. Easy to state and easy to lose — the file this service
replaced acquired a query text, then a second, then a question belonging to another collection,
and nothing said so.

Asked of the syntax tree rather than of the text, so a docstring may discuss selects while the
code holds none. Three claims, because a guard that only forbids proves nothing: one file AUTHORS
a query, one RUNS a query it is handed, and one touches neither.

See knowledge/decisions/an-afforder-is-a-service-between-two-collections.md.
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


def test_the_service_authors_no_query_and_runs_none():
    """The glue decides WHAT to ask; either would mean it had learned a collection's job."""
    tree = _parsed("afforder.py")
    assert not _authored_queries(tree), "the afforder writes query text"
    assert not ({"bind", "bindings", "Raw"} & _names(tree)), \
        "the afforder reaches for the store's query machinery"


def test_the_collection_of_templates_authors_its_own():
    """`Actions` asks the vocabulary what it declares, which is a question only it can phrase."""
    assert _authored_queries(_parsed("actions.py")), "Actions stopped carrying its own query"


def test_the_collection_of_rows_authors_none_and_runs_the_actions():
    """The sharp one, and it is why an affordance is not an action. `Affordances` writes NO query:
    the select it runs is the action's own `orexis:available`, declared by whichever package ships
    the action, bound here and answered against the world this collection was handed. A new way
    of acting is a node in a new directory and never an edit here (#207) — which is exactly what
    it would stop being if this file ever authored a select of its own."""
    tree = _parsed("affordances.py")
    assert not _authored_queries(tree), "Affordances began writing its own query text"
    assert {"bind", "bindings"} <= _names(tree), \
        "Affordances stopped binding and running the action's precondition"
