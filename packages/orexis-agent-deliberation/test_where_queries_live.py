"""Where the queries live, and where they must not.

Easy to state and easy to lose: the file that finds what a world affords must not become the
place that says what CAN be afforded. The file this was carved out of acquired a query text,
then a second, then a question belonging to another collection, and nothing said so.

Asked of the syntax tree rather than of the text, so a docstring may discuss selects while the
code holds none.

Two claims stood here once and are one now. `Actions` authored the enumeration and `Steps`
authored nothing; both are `steps.py`, because a class whose content was one query and one memo
was a file for a parameter. So the line moved from "authors none" to "authors one, and it names
no action", which is the property #207 actually asked for.
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


def test_the_one_query_here_names_no_action():
    """The sharp one, and it is why a step is not an action. `steps.py` authors ONE query —
    the enumeration, which asks by CLASS — and the select it RUNS is the action's own
    `orexis:available`, declared by whichever package ships the action, bound here and
    answered against the world it was handed.

    A new way of acting is a node in a new directory and never an edit here (#207), and that
    is what this protects. It used to say the file authored NO query at all, which was a
    sharper line and one file further out: the enumeration lived in `actions.py` behind a
    collection whose whole content was this query and a memo. Merging them moved the query
    in, so the claim is now about WHAT it may author rather than whether — and the property
    that matters survives, because a query that asks by class names no action.
    """
    tree = _parsed("steps.py")
    authored = _authored_queries(tree)
    assert len(authored) == 1, f"steps.py authors one query, the enumeration: {authored}"
    assert "a orexis:Action" in authored[0], \
        "and it asks by CLASS — a query naming an action is a registry, which is what #207 refused"
    assert {"bind", "bindings"} <= _names(tree), \
        "steps.py stopped binding and running the action's own precondition"
