//! The courier and the driver walked on the binary, held to what `world/courier/tests/test_courier.py` and
//! `world/driver/tests/test_driver.py` hold the Python runtime to: the plan found, adopted, walked a step at a time as
//! each lands, and the run ending as the Python one does — and, as `agent/metrics/tests/test_window.py` holds it, a
//! run whose metrics are written reads the agent's clock no more than one whose are not.

mod common;

use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use oxsdatatypes::DateTime;

use orexis::boot::TREE;
use orexis::clock::{Clock, instant};
use orexis::namespaces::Namespaces;
use orexis::store::{Store, iri, value};
use orexis::task::{MET, UNFINISHED};
use orexis_agent::booted;

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn world(name: &str) -> PathBuf {
    tree().join("world").join(name)
}

fn now() -> DateTime {
    instant("2026-01-01T12:00:00+00:00").unwrap()
}

/// Boot `agent` of `world` and run it until nothing holds it or `within` seconds of its time are spent: the outcome.
async fn run(store: &Store, world: &Path, agent: &str, within: u64, budget: Option<usize>) -> String {
    let loaded = booted(store, world, agent, now()).unwrap();
    let wiring = orexis_agent::Wiring::default();
    let running = orexis_agent::start(store, agent, common::clock(now()), &loaded, budget, wiring).unwrap();
    let outcome = common::outcome(&running, within).await;
    running.stop().await;
    outcome
}

fn store() -> Store {
    Store::new(Arc::new(Namespaces::linked().unwrap())).unwrap()
}

fn count(store: &Store, text: &str) -> usize {
    value(&store.rows(text, &[]).unwrap()[0], "n").unwrap().parse().unwrap()
}

const ACTS_Q: &str = "SELECT (COUNT(?a) AS ?n) WHERE { GRAPH ?g { ?a a execution:Act } }";
const INTENTIONS_Q: &str = "SELECT (COUNT(?i) AS ?n) WHERE { GRAPH ?g { ?i a execution:Intention } }";
const OUTCOMES_Q: &str = "SELECT ?o WHERE { GRAPH ?g { ?i a execution:Intention ; execution:outcome ?o } }";
const STANDS_Q: &str = "PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?x ?cx ?cy WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph ; orexis:ownedBy ?o }
  GRAPH ?g { ?x courier:x ?cx ; courier:y ?cy } } ORDER BY ?x";
const ABOARD_Q: &str = "PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?van WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph }
  GRAPH ?g { ?d courier:aboard ?van } }";
const WANTS_Q: &str =
    "SELECT (COUNT(?g) AS ?n) WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:WantGraph } }";

fn local(iri: &str) -> &str {
    iri.rsplit('#').next().unwrap()
}

/// Where each thing the agent believes of stands, by name, as two coordinates.
fn stands(store: &Store) -> Vec<(String, i64, i64)> {
    store
        .rows(STANDS_Q, &[])
        .unwrap()
        .iter()
        .map(|r| {
            (
                local(&iri(r, "x").unwrap()).to_string(),
                value(r, "cx").unwrap().parse().unwrap(),
                value(r, "cy").unwrap().parse().unwrap(),
            )
        })
        .filter(|(x, _, _)| !x.starts_with("top_of"))
        .collect()
}

#[tokio::test(start_paused = true)]
async fn the_parcel_is_delivered_in_eight_steps_and_the_runtime_stops() {
    let store = store();
    assert_eq!(run(&store, &world("courier"), "courier", 3600, None).await, MET);
    assert_eq!(
        count(&store, ACTS_Q),
        8,
        "three drives, the pick, three drives, the drop"
    );
    assert!(
        stands(&store).contains(&("parcel".to_string(), 3, 3)),
        "{:?}",
        stands(&store)
    );
    assert_eq!(count(&store, WANTS_Q), 0, "the want was reached and withdrawn");
}

#[tokio::test(start_paused = true)]
async fn a_budget_that_cuts_the_search_short_is_finished_by_the_passes_after() {
    let store = store();
    assert_eq!(run(&store, &world("courier"), "courier", 3600, Some(16)).await, MET);
    assert_eq!(count(&store, ACTS_Q), 8);
}

#[tokio::test(start_paused = true)]
async fn walked_the_drivers_one_plan_moves_both_parcels_and_leaves_the_driver_aboard_van_b() {
    let store = store();
    assert_eq!(
        run(&store, &world("driver"), "dispatcher", 3600, None).await,
        UNFINISHED,
        "a desire holds the agent"
    );
    assert_eq!(count(&store, INTENTIONS_Q), 1, "one want, one plan, one intention");
    assert_eq!(count(&store, ACTS_Q), 11, "the one plan walked whole");
    let outcomes: Vec<String> = store
        .rows(OUTCOMES_Q, &[])
        .unwrap()
        .iter()
        .filter_map(|r| value(r, "o"))
        .collect();
    assert_eq!(outcomes, ["done"]);
    let aboard: Vec<String> = store
        .rows(ABOARD_Q, &[])
        .unwrap()
        .iter()
        .filter_map(|r| iri(r, "van"))
        .collect();
    assert_eq!(aboard.iter().map(|v| local(v)).collect::<Vec<_>>(), ["van_b"]);
    let at = stands(&store);
    for (thing, x, y) in [
        ("van_a", 0, 3),
        ("parcel_a", 0, 3),
        ("van_b", 10, 3),
        ("parcel_b", 10, 3),
    ] {
        assert!(at.contains(&(thing.to_string(), x, y)), "{thing} at ({x}, {y}): {at:?}");
    }
}

/// The courier at 128 candidates for forty passes on a clock that ticks per read, enough for a drive to land now that an idle
/// pass reads it twice, with a metrics window written every
/// pass or none: how often the clock was read, how many points were written, how the run ended, and what was measured.
async fn metered_courier(watched: bool) -> (usize, usize, String, std::collections::BTreeSet<String>) {
    struct Counting(orexis::clock::Elapsing, Mutex<usize>);
    impl Clock for Counting {
        fn now(&self) -> DateTime {
            *self.1.lock().unwrap() += 1;
            self.0.now()
        }
    }
    let store = store();
    let clock = Arc::new(Counting(orexis::clock::Elapsing::from(now()), Mutex::new(0)));
    let loaded = booted(&store, &world("courier"), "courier", now()).unwrap();
    let written: std::sync::Arc<std::sync::Mutex<Vec<orexis::events::Point>>> = Default::default();
    let kept = written.clone();
    let mut wiring = orexis_agent::Wiring::default();
    if watched {
        let sink = orexis::series::Sink::new(
            "METRICS",
            "m",
            Box::new(move |_, points| {
                kept.lock().unwrap().extend(points.iter().cloned());
                Ok(())
            }),
        );
        wiring.watching.metrics = Some(orexis_metrics::Window::new(sink, 0.0, Some("courier"), Some("courier")));
    }
    let running = orexis_agent::start(&store, "courier", clock.clone(), &loaded, Some(128), wiring).unwrap();
    let outcome = common::outcome(&running, 3600).await;
    running.stop().await;
    let reads = *clock.1.lock().unwrap();
    let measured = written.lock().unwrap().iter().map(|p| p.measurement.clone()).collect();
    let count = written.lock().unwrap().len();
    (reads, count, outcome, measured)
}

#[tokio::test(start_paused = true)]
async fn a_timing_never_reads_the_agents_clock() {
    let (without, with) = (metered_courier(false).await, metered_courier(true).await);
    assert!(
        with.1 > 0 && without.1 == 0,
        "the sink was loaded for one run and not the other"
    );
    for m in ["search", "published", "intentions", "act", "landing"] {
        assert!(with.3.contains(m), "{m} measured: {:?}", with.3);
    }
    assert_eq!(
        (with.0, &with.2),
        (without.0, &without.2),
        "the clock is read as often, and the run ends the same"
    );
}
