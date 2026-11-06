//! `reroot`, held to `agent/planning/tests/reroot/`'s cases as `test_reroot.py` holds the Python act.

use std::path::PathBuf;

use oxsdatatypes::{DateTime, DayTimeDuration};

use orexis::snapshots;

use super::*;
use crate::world_at::lexical;

fn cases() -> PathBuf {
    snapshots::tree().join("planning/tests/reroot")
}

/// THE PRESENT: the newest ground laid from nothing.
const PRESENT_Q: &str = "
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start .
               FILTER NOT EXISTS { ?g prov:wasDerivedFrom ?parent } } }
ORDER BY DESC(?start) LIMIT 1";

const WORLDS_Q: &str = "
SELECT ?w ?at ?until ?spent WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:PossibleGraph .
               OPTIONAL { ?w dcterms:temporal ?p . ?p orexis:start ?at . OPTIONAL { ?p orexis:end ?until } }
               OPTIONAL { ?w planning:spent ?spent } } }";

fn present(store: &Store) -> String {
    iri(&store.rows(PRESENT_Q, &[]).unwrap()[0], "g").unwrap()
}

#[test]
fn reroot_leaves_the_store_the_diff_says() {
    for case in snapshots::cases_in(&cases()) {
        let store = snapshots::stand_in(&case);
        reroot(&store, &present(&store)).unwrap();
        snapshots::held_to_diff(&case, &store, "reroot");
    }
}

#[test]
fn every_case_is_read_and_no_diff_is_orphaned() {
    snapshots::all_read(&cases(), 3);
}

#[test]
fn every_kept_world_is_re_stamped_and_none_loses_its_instant() {
    let store = snapshots::stand_in(&cases().join("a_step_taken_as_predicted_keeps_its_cone.trig"));
    assert!(reroot(&store, &present(&store)).unwrap().matched.is_some());
    let kept = store.rows(WORLDS_Q, &[]).unwrap();
    assert!(!kept.is_empty(), "the cone beneath the match is kept");
    let later: DateTime = snapshots::now()
        .checked_add_day_time_duration(DayTimeDuration::new(60))
        .unwrap();
    for r in &kept {
        let (at, until) = (lexical(&r["at"]).unwrap(), lexical(&r["until"]).unwrap());
        assert!(until >= at && at >= later, "{r:?}");
        assert!(r.contains_key("spent"));
    }
    let least = kept
        .iter()
        .filter_map(|r| value(r, "spent")?.parse::<f64>().ok())
        .fold(f64::MAX, f64::min);
    assert_eq!(least, 1.0, "the match's spent was taken off: its children cost one");
}

#[test]
fn a_surprise_keeps_nothing() {
    let store = snapshots::stand_in(&cases().join("a_surprise_drops_everything.trig"));
    assert!(reroot(&store, &present(&store)).unwrap().matched.is_none());
    assert!(store.rows(WORLDS_Q, &[]).unwrap().is_empty());
}

const GROUND: &str = "http://example.org/orexis/graph/ground/";

#[test]
fn two_grounds_holding_the_presents_facts_are_told_by_their_cones_and_never_by_name() {
    for holder_is_old in [true, false] {
        let store = snapshots::stand_in(&cases().join("nothing_happened_and_the_cone_is_kept_whole.trig"));
        let cat = store.catalogue().unwrap().unwrap();
        let (old, landing) = (
            format!("{GROUND}2026-01-01T120000p0000"),
            format!("{GROUND}2026-01-01T120030p0000"),
        );
        store
            .update(&format!(
                "INSERT {{ GRAPH <{cat}> {{ <{landing}> a planning:GroundGraph ; orexis:arrivedBy orexis:Derived ; orexis:hash ?h ;
    prov:wasDerivedFrom <{old}> ;
    dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start \"2026-01-01T12:00:30+00:00\"^^xsd:dateTime ] }} }}
WHERE {{ GRAPH <{cat}> {{ <{old}> orexis:hash ?h }} }}"
            ))
            .unwrap();
        let (held, bare) = if holder_is_old {
            (&old, &landing)
        } else {
            (&landing, &old)
        };
        if !holder_is_old {
            store
                .update(&format!(
                    "DELETE {{ GRAPH <{cat}> {{ ?c planning:from <{old}> }} }} INSERT {{ GRAPH <{cat}> {{ ?c planning:from <{landing}> }} }}
WHERE {{ GRAPH <{cat}> {{ ?c planning:from <{old}> }} }}"
                ))
                .unwrap();
        }
        let whole = store.rows(WORLDS_Q, &[]).unwrap().len();
        let found = reroot(&store, &present(&store)).unwrap();
        assert_eq!(found.matched.as_ref(), Some(held), "{bare} holds no search");
        assert!(found.kept.len() >= whole && store.rows(WORLDS_Q, &[]).unwrap().len() == whole);
        assert!(
            found.dropped.contains(bare),
            "the bare ground goes with the rest the pass made"
        );
    }
}
