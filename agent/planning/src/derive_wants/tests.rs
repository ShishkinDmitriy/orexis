//! `derive_wants`, held to `agent/planning/tests/derive_wants/`'s cases as `test_derive_wants.py` holds the Python
//! act: a pass as a pass stands — the grounds laid, every desire weighed in every ground, the derivation, and
//! `withdraw` handed its answer with what is walked.

use std::path::PathBuf;

use oxsdatatypes::DayTimeDuration;

use orexis::snapshots;

use super::*;
use crate::lay_ground::{Laying, lay_ground};
use crate::unweighed::unweighed;
use crate::weigh::weigh;
use crate::withdraw::withdraw;

fn cases() -> PathBuf {
    snapshots::tree().join("planning/tests/derive_wants")
}

/// What the intentions walk, as the executor's `walking` reads it: every want an unresolved intention pursues.
const WALKING_Q: &str = "
SELECT DISTINCT ?want WHERE {
  GRAPH ?g { ?i a execution:Intention ; execution:pursues ?want .
             FILTER NOT EXISTS { ?i execution:resolvedAt ?done } } }
ORDER BY ?want";

fn laid_and_weighed(case: &std::path::Path) -> Store {
    let store = snapshots::stand_in(case);
    lay_ground(&store, snapshots::now(), &Laying::default()).unwrap();
    weigh_all(&store, None);
    store
}

fn weigh_all(store: &Store, for_: Option<&str>) {
    let mut memo = Memo::default();
    for pair in unweighed(store, for_, None, &mut memo).unwrap() {
        weigh(
            store,
            &iri(&pair, "for").unwrap(),
            &iri(&pair, "about").unwrap(),
            &mut memo,
        )
        .unwrap();
    }
}

#[test]
fn derive_wants_leaves_the_store_as_the_diff_says() {
    for case in snapshots::cases_in(&cases()) {
        let store = laid_and_weighed(&case);
        let walking: BTreeSet<String> = store
            .rows(WALKING_Q, &[])
            .unwrap()
            .iter()
            .filter_map(|r| iri(r, "want"))
            .collect();
        let at: BTreeMap<String, DateTime> = walking.iter().map(|w| (w.clone(), snapshots::now())).collect();
        let mut wanted = derive_wants(&store, snapshots::now(), &at, &BTreeSet::new())
            .unwrap_or_else(|e| panic!("{}: {e}", case.display()));
        wanted.extend(walking);
        withdraw(&store, Some(&wanted), &BTreeSet::new(), &BTreeSet::new()).unwrap();
        snapshots::held_to_diff(&case, &store, "derive_wants");
    }
}

#[test]
fn every_case_is_read_and_no_diff_is_orphaned() {
    assert!(snapshots::cases_in(&cases()).len() >= 14);
    assert!(snapshots::orphans_in(&cases()).is_empty());
}

const HOMES: &str = "
SELECT ?w ?g ?start ?reopens WHERE {
  GRAPH ?g { ?w a planning:Want . OPTIONAL { ?w planning:reopens ?reopens } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:WantGraph .
               OPTIONAL { ?g dcterms:temporal/orexis:start ?start } } }";

#[test]
fn a_walking_want_a_belief_reopened_is_minted_again_where_its_step_in_flight_lands() {
    for reopened in [false, true] {
        let store = laid_and_weighed(&cases().join("a_standing_want_is_left_alone.trig"));
        let want = "http://example.org/test#keeper.in_range.pursued.tank1.level";
        let lands = snapshots::now()
            .checked_add_day_time_duration(DayTimeDuration::new(30))
            .unwrap();
        let before: BTreeMap<String, String> = store
            .rows(HOMES, &[])
            .unwrap()
            .iter()
            .filter_map(|r| Some((iri(r, "w")?, iri(r, "g")?)))
            .collect();
        let reopen: BTreeSet<String> = if reopened {
            [want.to_string()].into()
        } else {
            BTreeSet::new()
        };
        let wanted = derive_wants(&store, snapshots::now(), &[(want.to_string(), lands)].into(), &reopen).unwrap();
        let homes: Vec<_> = store
            .rows(HOMES, &[])
            .unwrap()
            .into_iter()
            .filter(|r| iri(r, "w").as_deref() == Some(want))
            .collect();
        assert!(wanted.contains(want) && homes.len() == 1, "{homes:?}");
        let (graph, reopens) = (iri(&homes[0], "g").unwrap(), iri(&homes[0], "reopens"));
        if !reopened {
            assert_eq!(
                (graph, reopens),
                (before[want].clone(), None),
                "a walking want nothing reopened stands where it was"
            );
            continue;
        }
        assert_eq!(
            lexical(&homes[0]["start"]).unwrap(),
            lands,
            "minted again where its step in flight lands"
        );
        assert_eq!(reopens.as_deref(), Some(want), "reopening itself");
        assert!(
            graph != before[want] && store.quads(&before[want]).unwrap().is_empty(),
            "the old graph goes"
        );
    }
}

const REMAINING_Q: &str = "
SELECT ?for ?left WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?g ; planning:remaining ?left .
               ?g a planning:GroundGraph } }";

#[test]
fn two_wants_under_one_desire_read_two_estimates() {
    let store = laid_and_weighed(&cases().join("two_parcels_two_estimates.trig"));
    let wants = derive_wants(&store, snapshots::now(), &BTreeMap::new(), &BTreeSet::new()).unwrap();
    assert_eq!(wants.len(), 2, "{wants:?}");
    for want in &wants {
        weigh_all(&store, Some(want));
    }
    let left: BTreeMap<String, f64> = store
        .rows(REMAINING_Q, &[])
        .unwrap()
        .iter()
        .filter_map(|r| {
            let for_ = iri(r, "for")?;
            Some((for_.rsplit('.').next()?.to_string(), value(r, "left")?.parse().ok()?))
        })
        .collect();
    assert_eq!(
        left,
        [("parcel_a".to_string(), 3.0), ("parcel_b".to_string(), 2.0)].into()
    );
}
