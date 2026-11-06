//! `prepare_ground`, held to `agent/planning/tests/prepare_ground/`'s cases as `test_prepare_ground.py` holds the
//! Python act — the store it FILLS is the diff — and to its tests beside them.

use std::collections::BTreeSet;
use std::path::PathBuf;

use oxigraph::model::{GraphName, Literal, NamedNode, Quad};

use orexis::snapshots;

use super::*;
use crate::lay_ground::{Laying, lay_ground};
use crate::ontology::GROUND_GRAPH;

fn cases() -> PathBuf {
    snapshots::tree().join("planning/tests/prepare_ground")
}

fn empty() -> Store {
    Store::new(snapshots::namespaces()).expect("an empty store")
}

#[test]
fn prepare_ground_fills_the_store_as_the_diff_says() {
    for case in snapshots::cases_in(&cases()) {
        let into = empty();
        prepare_ground(&snapshots::stand_in(&case), &into, None, None).unwrap();
        snapshots::held_to_diff(&case, &into, "prepare_ground");
    }
}

#[test]
fn every_case_is_read_and_no_diff_is_orphaned() {
    snapshots::all_read(&cases(), 3);
}

#[test]
fn a_second_filling_refreshes_the_copy_and_keeps_what_the_store_made() {
    let beliefs = snapshots::stand_in(&cases().join("a_forecast_holding_later_crosses_whole.trig"));
    let into = empty();
    prepare_ground(&beliefs, &into, None, None).unwrap();
    lay_ground(&into, snapshots::now(), &Laying::default()).unwrap();
    let grounds = into.graphs_of(&[GROUND_GRAPH], &Within::default()).unwrap();
    assert!(!grounds.is_empty(), "the store made grounds of its own");
    //  A WANT THE DERIVATION MINTED is a kind that crosses too, told apart by how it arrived: no want crosses that
    //  way, since the derivation runs in here and nowhere else.
    let minted = "urn:test:minted";
    let catalogue = into.catalogue().unwrap().unwrap();
    into.update(&format!(
        "INSERT DATA {{ GRAPH <{minted}> {{ <urn:test:w> a planning:Want }}
           GRAPH <{catalogue}> {{ <{minted}> a planning:WantGraph ; orexis:arrivedBy orexis:Derived }} }}"
    ))
    .unwrap();
    let crossing = beliefs.graphs_of(CROSSING, &Within::default()).unwrap();
    let (replaced, swept) = (&crossing[0], &crossing[1]);
    let old = beliefs.quads(replaced).unwrap().remove(0);
    beliefs.remove_all(std::slice::from_ref(&old)).unwrap();
    let new = Quad::new(
        old.subject.clone(),
        old.predicate.clone(),
        Literal::new_simple_literal("moved on"),
        GraphName::NamedNode(NamedNode::new(replaced).unwrap()),
    );
    beliefs.add([new.clone()]).unwrap();
    beliefs.forget_graph(swept, Some(BELIEF)).unwrap();
    prepare_ground(&beliefs, &into, None, None).unwrap();
    let held = into.quads(replaced).unwrap();
    assert!(
        held.contains(&new) && !held.contains(&old),
        "the row replaced, not laid beside the old one"
    );
    assert!(
        !into.graph_names().unwrap().contains(swept),
        "the graph the beliefs swept is gone from the copy"
    );
    assert_eq!(
        into.graphs_of(&[GROUND_GRAPH], &Within::default()).unwrap(),
        grounds,
        "what the store made stays"
    );
    assert!(
        !into.quads(minted).unwrap().is_empty(),
        "and so does the want it minted"
    );
}

fn names(store: &Store) -> BTreeSet<String> {
    store.graph_names().unwrap().into_iter().collect()
}

fn filled(beliefs: &Store, scope: Option<&str>, scopes: Option<&Scopes>) -> BTreeSet<String> {
    let into = empty();
    prepare_ground(beliefs, &into, scope, scopes).unwrap();
    names(&into)
}

fn scopes(members: &[(&str, &[&str])]) -> Scopes {
    Scopes(
        members
            .iter()
            .map(|(m, s)| (m.to_string(), s.iter().map(|s| s.to_string()).collect()))
            .collect(),
    )
}

#[test]
fn a_reading_keyed_by_another_scopes_term_stays_behind_with_its_revisions_and_its_prediction() {
    let beliefs = snapshots::stand_in(&cases().join("a_readings_revisions_cross_with_it.trig"));
    let soils: BTreeSet<String> = ["sensed", "sensed_revisions", "drying_stops", "drying_stops_revisions"]
        .iter()
        .map(|l| format!("http://example.org/test#{l}"))
        .collect();
    let (soil, air) = ("urn:test:soil", "urn:test:air");
    let (moisture, temperature, bed) = (
        "http://example.org/test#SoilMoisture",
        "urn:test:AirTemperature",
        "http://example.org/test#bed",
    );
    let whole = filled(&beliefs, None, None);
    assert!(soils.is_subset(&whole), "with no other scope, every reading crosses");
    let one = scopes(&[(moisture, &[soil])]);
    assert_eq!(
        filled(&beliefs, Some(soil), Some(&one)),
        whole,
        "one scope in the partition is a store of one scope: everything crosses"
    );
    let parted = scopes(&[(moisture, &[soil]), (temperature, &[air])]);
    let less: BTreeSet<String> = whole.difference(&soils).cloned().collect();
    let into = empty();
    prepare_ground(&beliefs, &into, Some(air), Some(&parted)).unwrap();
    assert_eq!(
        names(&into),
        less,
        "the soil's reading, its side and its prediction are another scope's"
    );
    prepare_ground(&beliefs, &into, None, None).unwrap();
    assert_eq!(names(&into), whole, "a refresh for a store of one scope brings them");
    prepare_ground(&beliefs, &into, Some(air), Some(&parted)).unwrap();
    assert_eq!(names(&into), less, "and a refresh for the air's scope takes them back");
    let apart = scopes(&[(moisture, &[soil]), (temperature, &[air]), (bed, &[air])]);
    assert_eq!(
        filled(&beliefs, Some(air), Some(&apart)),
        whole,
        "a reading naming a member of each scope, held together by neither, is each scope's"
    );
    let shared = scopes(&[(moisture, &[soil]), (temperature, &[air]), (bed, &[soil, air])]);
    assert_eq!(
        filled(&beliefs, Some(air), Some(&shared)),
        less,
        "a bed of two scopes and a property of one meet in the one"
    );
    assert_eq!(filled(&beliefs, Some(soil), Some(&shared)), whole);
}
