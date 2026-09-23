"""Reading the store's scopes — tested where the read lives. The writer is `scope_actions`,
held by its own cases; what is written here is the rows a scope graph holds, said plainly."""

from __future__ import annotations

from orexis.agent.store import update
from orexis.agent.planning.find_scopes import find_scopes


def test_a_store_nobody_scoped_says_none_and_a_scoped_empty_store_says_nothing(wants):
    assert find_scopes(wants.store) is None, "never scoped, which the derivation refuses to guess about"
    update(wants.store, "INSERT DATA { GRAPH <urn:test:catalogue> { <urn:test:scopes> a planning:ScopeGraph } }")
    assert find_scopes(wants.store) == {}, "scoped, and empty — a store with nothing to do"


def test_every_member_is_read_with_its_scope(wants):
    update(wants.store, """INSERT DATA {
  GRAPH <urn:test:scopes> { <urn:test:s1> a planning:Scope . <urn:test:level> planning:inScope <urn:test:s1> .
                            <urn:test:fill> planning:inScope <urn:test:s1> }
  GRAPH <urn:test:catalogue> { <urn:test:scopes> a planning:ScopeGraph } }""")
    assert find_scopes(wants.store) == {"urn:test:level": "urn:test:s1", "urn:test:fill": "urn:test:s1"}
