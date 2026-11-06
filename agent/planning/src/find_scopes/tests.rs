//! Reading the store's scopes, held to what `test_find_scopes.py` holds the Python read to.

use orexis::snapshots;

use super::*;

fn store() -> Store {
    let store = Store::new(snapshots::namespaces()).expect("an empty store");
    store
        .update("INSERT DATA { GRAPH <urn:test:catalogue> { <urn:test:catalogue> a orexis:CatalogueGraph } }")
        .unwrap();
    store
}

fn set(members: &[&str]) -> BTreeSet<String> {
    members.iter().map(|m| m.to_string()).collect()
}

#[test]
fn a_store_nobody_scoped_says_none_and_a_scoped_empty_store_says_nothing() {
    let store = store();
    assert_eq!(find_scopes(&store).unwrap(), None, "never scoped");
    store
        .update("INSERT DATA { GRAPH <urn:test:catalogue> { <urn:test:scopes> a planning:ScopeGraph } }")
        .unwrap();
    assert_eq!(
        find_scopes(&store).unwrap(),
        Some(Scopes::default()),
        "scoped, and empty"
    );
}

#[test]
fn every_member_is_read_with_every_scope_it_is_in() {
    let store = store();
    store
        .update(
            "INSERT DATA {
  GRAPH <urn:test:scopes> { <urn:test:s1> a planning:Scope . <urn:test:s2> a planning:Scope .
                            <urn:test:level> planning:inScope <urn:test:s1> .
                            <urn:test:fill> planning:inScope <urn:test:s1> .
                            <urn:test:bed> planning:inScope <urn:test:s1> , <urn:test:s2> .
                            <urn:test:heat> planning:inScope <urn:test:s2> }
  GRAPH <urn:test:catalogue> { <urn:test:scopes> a planning:ScopeGraph } }",
        )
        .unwrap();
    let scopes = find_scopes(&store).unwrap().unwrap();
    let expected: BTreeMap<String, BTreeSet<String>> = [
        ("urn:test:level", set(&["urn:test:s1"])),
        ("urn:test:fill", set(&["urn:test:s1"])),
        ("urn:test:bed", set(&["urn:test:s1", "urn:test:s2"])),
        ("urn:test:heat", set(&["urn:test:s2"])),
    ]
    .into_iter()
    .map(|(k, v)| (k.to_string(), v))
    .collect();
    assert_eq!(scopes.0, expected);
    assert_eq!(scopes.all(), set(&["urn:test:s1", "urn:test:s2"]));
}

#[test]
fn a_thing_is_placed_where_the_scopes_of_what_it_names_meet() {
    let store = store();
    store
        .update(
            "INSERT DATA {
  GRAPH <urn:test:scopes> { <urn:test:level> planning:inScope <urn:test:s1> .
                            <urn:test:bed> planning:inScope <urn:test:s1> , <urn:test:s2> .
                            <urn:test:temperature> planning:inScope <urn:test:s2> }
  GRAPH <urn:test:catalogue> { <urn:test:scopes> a planning:ScopeGraph } }",
        )
        .unwrap();
    let scopes = find_scopes(&store).unwrap().unwrap();
    assert_eq!(
        scopes.meet(["urn:test:bed", "urn:test:level", "urn:test:probe"]),
        set(&["urn:test:s1"])
    );
    assert_eq!(scopes.meet(["urn:test:bed"]), set(&["urn:test:s1", "urn:test:s2"]));
    assert_eq!(
        scopes.meet(["urn:test:level", "urn:test:temperature"]),
        set(&["urn:test:s1", "urn:test:s2"]),
        "held together by no scope, so every scope either is in"
    );
    assert_eq!(scopes.meet(["urn:test:probe"]), BTreeSet::new());
}
