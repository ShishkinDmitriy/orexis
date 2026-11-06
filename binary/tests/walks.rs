//! The courier and the driver walked on the binary, held to what `world/courier/tests/test_courier.py` and
//! `world/driver/tests/test_driver.py` hold the Python runtime to: the plan found, adopted, walked a step at a time as
//! each lands, and the run ending as the Python one does. The tests of those files that hold the events, the
//! metrics and the sensing wait for those packages.

use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use oxsdatatypes::{DateTime, DayTimeDuration};

use orexis::boot::TREE;
use orexis::clock::{Clock, instant};
use orexis::namespaces::Namespaces;
use orexis::runtime::{MET, Part, Runtime, UNFINISHED};
use orexis::store::{Store, iri, value};
use orexis_agent::{assemble, booted};

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn world(name: &str) -> PathBuf {
    tree().parent().unwrap().join("world").join(name)
}

fn now() -> DateTime {
    instant("2026-01-01T12:00:00+00:00").unwrap()
}

/// A timeline that moves on a second at every read, as a running agent's does: a drive lands half a minute after it
/// is taken, and held at one instant the run would never reach it.
struct Ticking(Mutex<DateTime>);

impl Clock for Ticking {
    fn now(&self) -> DateTime {
        let mut at = self.0.lock().unwrap();
        *at = at.checked_add_day_time_duration(DayTimeDuration::new(1)).unwrap();
        *at
    }
}

/// Boot `agent` of `world` and run it until nothing holds it or `passes` are spent: the outcome.
fn run(store: &Store, world: &Path, agent: &str, clock: &Ticking, passes: usize, budget: Option<usize>) -> String {
    let loaded = booted(store, tree(), world, agent, clock.now()).unwrap();
    let mut parts = assemble(store, agent, clock, &loaded, budget).unwrap();
    let lent: Vec<(String, &mut dyn Part)> = parts
        .iter_mut()
        .map(|(p, part)| (p.clone(), part.as_mut() as &mut dyn Part))
        .collect();
    let mut runtime = Runtime::new(store, agent, clock, lent).unwrap();
    let outcome = runtime.run(Some(passes), 0.0).unwrap();
    runtime.stop();
    outcome
}

fn store() -> Store {
    Store::new(Arc::new(Namespaces::of_tree(tree()).unwrap())).unwrap()
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

#[test]
fn the_parcel_is_delivered_in_eight_steps_and_the_runtime_stops() {
    let (store, clock) = (store(), Ticking(Mutex::new(now())));
    assert_eq!(run(&store, &world("courier"), "courier", &clock, 400, None), MET);
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

#[test]
fn a_budget_that_cuts_the_search_short_is_finished_by_the_passes_after() {
    let (store, clock) = (store(), Ticking(Mutex::new(now())));
    assert_eq!(run(&store, &world("courier"), "courier", &clock, 200, Some(16)), MET);
    assert_eq!(count(&store, ACTS_Q), 8);
}

#[test]
fn walked_the_drivers_one_plan_moves_both_parcels_and_leaves_the_driver_aboard_van_b() {
    let (store, clock) = (store(), Ticking(Mutex::new(now())));
    assert_eq!(
        run(&store, &world("driver"), "dispatcher", &clock, 120, None),
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
