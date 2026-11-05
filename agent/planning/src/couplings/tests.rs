//! What a holder's constraints can make collide, held to what `test_couplings.py` holds the Python read to.

use orexis::snapshots;

use super::*;
use crate::lay_ground::{Laying, lay_ground};

const T: &str = "http://example.org/test#";

fn laid(name: &str) -> (Store, String) {
    let store = snapshots::stand_in(&snapshots::tree().join(format!("planning/tests/derive_wants/{name}.trig")));
    let grounds = lay_ground(&store, snapshots::now(), &Laying::default()).unwrap();
    let [present] = grounds.as_slice() else {
        panic!("one ground: {grounds:?}")
    };
    let present = present.clone();
    (store, present)
}

#[test]
fn a_drive_to_a_computed_position_couples_everything_and_runs_no_reach() {
    let (store, present) = laid("two_parcels_a_constraint_joins_are_one_want");
    let coupled = couplings(
        &store,
        &format!("{T}keeper"),
        &present,
        snapshots::now(),
        &mut Memo::default(),
    )
    .unwrap()
    .expect("the holder holds a constraint");
    assert!(coupled.anything);
    assert!(coupled.joins(&format!("{T}parcel_a"), &format!("{T}parcel_b")));
    assert!(
        !store.graph_names().unwrap().contains(&REACH_GRAPH.to_string()),
        "no reach is run"
    );
}

#[test]
fn a_holder_with_no_constraint_couples_nothing_and_pays_no_reach() {
    let (store, present) = laid("two_parcels_two_estimates");
    assert_eq!(
        couplings(
            &store,
            &format!("{T}keeper"),
            &present,
            snapshots::now(),
            &mut Memo::default()
        )
        .unwrap(),
        None
    );
}

#[test]
fn a_reach_over_finite_places_joins_only_what_can_meet() {
    let parts = vec![BTreeSet::from(["urn:a".to_string(), "urn:cell".to_string()])];
    let bound = BTreeMap::from([
        ("urn:p".to_string(), BTreeSet::from(["urn:a".to_string()])),
        ("urn:q".to_string(), BTreeSet::from(["urn:cell".to_string()])),
        ("urn:r".to_string(), BTreeSet::from(["urn:b".to_string()])),
    ]);
    let coupled = Couplings {
        parts,
        bound,
        anything: false,
    };
    assert!(
        coupled.joins("urn:p", "urn:q"),
        "one part meets what each is bound with"
    );
    assert!(!coupled.joins("urn:p", "urn:r"), "and nothing joins what no part meets");
}
