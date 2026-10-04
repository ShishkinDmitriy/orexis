"""Reading the store's scopes — tested where the read lives. The writer is `scope_actions`,
held by its own cases; what is written here is the rows a scope graph holds, said plainly."""

from __future__ import annotations

from agent.store import update
from agent.planning.find_scopes import find_scopes


def test_a_store_nobody_scoped_says_none_and_a_scoped_empty_store_says_nothing(wants):
    assert find_scopes(wants.store) is None, "never scoped, which the derivation refuses to guess about"
    update(wants.store, "INSERT DATA { GRAPH <urn:test:catalogue> { <urn:test:scopes> a planning:ScopeGraph } }")
    assert find_scopes(wants.store) == {}, "scoped, and empty — a store with nothing to do"


def test_every_member_is_read_with_every_scope_it_is_in(wants):
    """A member in two scopes — the bed a pump's filling and a heater's both bind, the action a filling
    of which falls in each — is read with both; it was read with whichever row came last."""
    update(wants.store, """INSERT DATA {
  GRAPH <urn:test:scopes> { <urn:test:s1> a planning:Scope . <urn:test:s2> a planning:Scope .
                            <urn:test:level> planning:inScope <urn:test:s1> .
                            <urn:test:fill> planning:inScope <urn:test:s1> .
                            <urn:test:bed> planning:inScope <urn:test:s1> , <urn:test:s2> .
                            <urn:test:heat> planning:inScope <urn:test:s2> }
  GRAPH <urn:test:catalogue> { <urn:test:scopes> a planning:ScopeGraph } }""")
    scopes = find_scopes(wants.store)
    assert scopes == {"urn:test:level": {"urn:test:s1"}, "urn:test:fill": {"urn:test:s1"},
                      "urn:test:bed": {"urn:test:s1", "urn:test:s2"}, "urn:test:heat": {"urn:test:s2"}}
    assert scopes.all() == {"urn:test:s1", "urn:test:s2"}
    assert scopes.one("urn:test:level") == "urn:test:s1" and scopes.one("urn:test:bed") is None, \
        "a member of two scopes is unique to neither"


def test_a_thing_is_placed_where_the_scopes_of_what_it_names_meet(wants):
    """The bed is both scopes' and the level the first's: a reading naming both is the first's alone.
    Two members no scope holds together are every scope either is in — the tower's state, which names
    the courier's cells and the puzzle's `on`. Naming no member is being nowhere, which a reader takes
    as everywhere."""
    update(wants.store, """INSERT DATA {
  GRAPH <urn:test:scopes> { <urn:test:level> planning:inScope <urn:test:s1> .
                            <urn:test:bed> planning:inScope <urn:test:s1> , <urn:test:s2> .
                            <urn:test:temperature> planning:inScope <urn:test:s2> }
  GRAPH <urn:test:catalogue> { <urn:test:scopes> a planning:ScopeGraph } }""")
    scopes = find_scopes(wants.store)
    assert scopes.meet(["urn:test:bed", "urn:test:level", "urn:test:probe"]) == {"urn:test:s1"}
    assert scopes.meet(["urn:test:bed"]) == {"urn:test:s1", "urn:test:s2"}
    assert scopes.meet(["urn:test:level", "urn:test:temperature"]) == {"urn:test:s1", "urn:test:s2"}, \
        "held together by no scope, so every scope either is in"
    assert scopes.meet(["urn:test:probe"]) == frozenset()
