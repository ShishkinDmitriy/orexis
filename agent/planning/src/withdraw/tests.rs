//! Withdrawing what the derivation no longer implies, held to what `test_withdraw.py` holds the Python act to.

use crate::find_wants::tests::{at, derived, graph_of, owed, store};
use crate::find_wants::{Finding, find_wants};

use super::*;

fn set(uris: &[&str]) -> BTreeSet<String> {
    uris.iter().map(|u| u.to_string()).collect()
}

fn found(store: &Store) -> Vec<String> {
    find_wants(store, at(), &Finding::default()).unwrap()
}

#[test]
fn a_want_the_derivation_no_longer_implies_goes_and_the_named_one_stays() {
    let store = store();
    derived(&store, "urn:test:a", at(), None);
    derived(&store, "urn:test:b", at(), None);
    let none = BTreeSet::new();
    assert_eq!(
        withdraw(&store, Some(&set(&["urn:test:a"])), &none, &none).unwrap(),
        ["urn:test:b"]
    );
    assert_eq!(found(&store), ["urn:test:a"]);
}

#[test]
fn a_debt_is_not_the_derivations_to_withdraw_until_it_is_reached() {
    let store = store();
    owed(&store, "urn:test:owed");
    let none = BTreeSet::new();
    assert!(withdraw(&store, Some(&none), &none, &none).unwrap().is_empty());
    assert_eq!(found(&store), ["urn:test:owed"], "the ledger's, and it stands");
    store
        .update("INSERT DATA { GRAPH <http://example.org/orexis/market#obligations/gardener/owed> { <urn:test:history> a <urn:test:Entry> } }")
        .unwrap();
    assert_eq!(
        withdraw(&store, None, &set(&["urn:test:owed"]), &none).unwrap(),
        ["urn:test:owed"],
        "reached, whoever wrote it"
    );
    assert!(found(&store).is_empty());
    assert_eq!(
        store
            .quads("http://example.org/orexis/market#obligations/gardener/owed")
            .unwrap()
            .len(),
        1,
        "and the record keeps what else it holds"
    );
}

#[test]
fn forgetting_a_want_leaves_nothing_behind() {
    let store = store();
    derived(&store, "urn:test:want", at(), None);
    let none = BTreeSet::new();
    assert_eq!(withdraw(&store, Some(&none), &none, &none).unwrap(), ["urn:test:want"]);
    assert!(
        find_wants(
            &store,
            at(),
            &Finding {
                uri: Some("urn:test:want"),
                ..Finding::default()
            }
        )
        .unwrap()
        .is_empty()
    );
    let graph = graph_of(at(), None);
    assert!(
        store
            .rows(
                &format!("SELECT ?p WHERE {{ GRAPH <urn:test:catalogue> {{ <{graph}> ?p ?o }} }}"),
                &[]
            )
            .unwrap()
            .is_empty(),
        "and the catalogue says nothing of its graph"
    );
}

#[test]
fn one_want_of_two_in_a_graph_goes_alone() {
    let store = store();
    derived(&store, "urn:test:a", at(), None);
    derived(&store, "urn:test:b", at(), None);
    forget_want(&store, "urn:test:a").unwrap();
    assert_eq!(
        found(&store),
        ["urn:test:b"],
        "the graph of the stretch stays for the other"
    );
    let held = store.quads(&graph_of(at(), None)).unwrap();
    assert!(
        held.iter().all(|q| !q.to_string().contains("urn:test:a>")),
        "and nothing of the one is left"
    );
}
