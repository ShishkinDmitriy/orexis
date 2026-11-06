//! `take`, held to `agent/planning/tests/take/`'s cases as `test_take.py` holds the Python act: every candidate
//! that has reached no world taken in mint order, and the diff the worlds they made.

use std::collections::BTreeSet;
use std::path::PathBuf;

use orexis::snapshots;

use super::*;
use crate::admit::{Scope, admit};

const UNTAKEN_Q: &str = "
SELECT ?cand WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?cand a planning:Candidate ; planning:minted ?m .
               FILTER NOT EXISTS { ?w planning:by ?cand } } }
ORDER BY ?m";

const EDGES_Q: &str = "
SELECT ?cand ?m ?w ?wm WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?cand a planning:Candidate ; planning:minted ?m .
               OPTIONAL { ?w planning:by ?cand ; planning:minted ?wm } } }
ORDER BY ?m";

const PRESENT_Q: &str =
    "SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph } } LIMIT 1";

fn cases() -> PathBuf {
    snapshots::tree().join("planning/tests/take")
}

fn untaken(store: &Store) -> Vec<String> {
    store
        .rows(UNTAKEN_Q, &[])
        .unwrap()
        .iter()
        .filter_map(|r| iri(r, "cand"))
        .collect()
}

#[test]
fn take_forks_the_worlds_the_diff_says() {
    for case in snapshots::cases_in(&cases()) {
        let store = snapshots::stand_in(&case);
        let mut memo = Memo::default();
        let candidates = untaken(&store);
        assert!(!candidates.is_empty(), "{} admits no candidate to take", case.display());
        for cand in candidates {
            take(&store, &cand, None, &mut memo).unwrap();
        }
        snapshots::held_to_diff(&case, &store, "take");
    }
}

#[test]
fn every_case_is_read_and_no_diff_is_orphaned() {
    snapshots::all_read(&cases(), 2);
}

fn admitted(memo: &mut Memo) -> Store {
    let store = snapshots::stand_in(&snapshots::tree().join("planning/tests/admit/one_lever_two_tanks.trig"));
    let present = iri(&store.rows(PRESENT_Q, &[]).unwrap()[0], "g").unwrap();
    admit(&store, &present, &Scope::default(), memo).unwrap();
    store
}

#[test]
fn siblings_differing_in_one_value_never_share_a_graph() {
    let mut memo = Memo::default();
    let store = admitted(&mut memo);
    for cand in untaken(&store) {
        assert!(take(&store, &cand, None, &mut memo).unwrap());
    }
    let edges = store.rows(EDGES_Q, &[]).unwrap();
    let worlds: Vec<String> = edges.iter().filter_map(|e| iri(e, "w")).collect();
    assert_eq!((edges.len(), worlds.len()), (2, 2));
    let possible: BTreeSet<String> = store
        .graphs_of(&[POSSIBLE_GRAPH], &Within::default())
        .unwrap()
        .into_iter()
        .collect();
    assert_eq!(worlds.iter().cloned().collect::<BTreeSet<_>>(), possible);
    for e in &edges {
        assert_eq!(value(e, "m"), value(e, "wm"), "a world carries its candidate's number");
    }
    let held: Vec<BTreeSet<String>> = worlds
        .iter()
        .map(|w| store.triples(w).unwrap().iter().map(|t| t.to_string()).collect())
        .collect();
    assert!(!held[0].is_empty() && !held[1].is_empty() && held[0] != held[1]);
}

#[test]
fn a_second_pass_over_one_store_mints_above_everything_it_holds() {
    let mut first = Memo::default();
    let store = admitted(&mut first);
    for cand in untaken(&store) {
        take(&store, &cand, None, &mut first).unwrap();
    }
    let before = store.rows(EDGES_Q, &[]).unwrap();
    let names: BTreeSet<String> = before
        .iter()
        .flat_map(|e| [iri(e, "cand"), iri(e, "w")])
        .flatten()
        .collect();
    let mut second = Memo::default();
    admit(&store, &iri(&before[0], "w").unwrap(), &Scope::default(), &mut second).unwrap();
    for cand in untaken(&store) {
        take(&store, &cand, None, &mut second).unwrap();
    }
    let after = store.rows(EDGES_Q, &[]).unwrap();
    let new: Vec<_> = after
        .iter()
        .filter(|e| !names.contains(&iri(e, "cand").unwrap()))
        .collect();
    assert!(!new.is_empty() && new.iter().all(|e| iri(e, "w").is_some()));
    let number = |e: &orexis::store::Row| value(e, "m").unwrap().parse::<u64>().unwrap();
    assert!(new.iter().map(|e| number(e)).min() > before.iter().map(number).max());
    let all: BTreeSet<String> = after
        .iter()
        .flat_map(|e| [iri(e, "cand"), iri(e, "w")])
        .flatten()
        .collect();
    assert_eq!(
        all.len(),
        2 * after.len(),
        "every candidate and every world under a name of its own"
    );
}
