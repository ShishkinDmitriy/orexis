//! The tower on the binary, held to what `world/tower/tests/test_tower.py` holds the Python runtime to: hanoi's puzzle
//! on the courier's grid, planned one level inside the other. The world's rules say what a disk is on from where it
//! stands, so the mover is a deliberator as well as a planner and an executor: belief revises the state at the
//! start, and every graph the executor writes as the world as it is written. Run on TWO disks, the world's third
//! taken out of the booted beliefs, as the Python gate runs it.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use oxsdatatypes::{DateTime, DayTimeDuration};

use orexis::boot::TREE;
use orexis::clock::{Clock, instant};
use orexis::hash::hash_named_graph;
use orexis::namespaces::Namespaces;
use orexis::ontology::{BELIEF, SELF_GRAPH};
use orexis::runtime::{MET, Part, Runtime};
use orexis::store::{Store, Within, iri, value};
use orexis_agent::{assemble, booted};

const TOWER: &str = "http://example.org/orexis/world/tower#";
const REVISION: &str = "http://example.org/orexis/belief#RevisionGraph";
const COMMITTED: &str = "http://example.org/orexis/execution#CommittedStepGraph";

const ON_Q: &str = "PREFIX hanoi: <http://example.org/orexis/hanoi#>
SELECT ?d ?below WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph } GRAPH ?g { ?d hanoi:on ?below } } ORDER BY ?d";
const AT_Q: &str = "PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?s ?x ?y WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph } GRAPH ?g { ?s courier:x ?x ; courier:y ?y } } ORDER BY ?s";
const REFINED_Q: &str = "SELECT (COUNT(?a) AS ?n) WHERE { GRAPH ?g { ?a execution:refinedBy ?w } }";

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn world() -> PathBuf {
    tree().parent().unwrap().join("world/tower")
}

fn now() -> DateTime {
    instant("2026-01-01T12:00:00+00:00").unwrap()
}

fn store() -> Store {
    Store::new(Arc::new(Namespaces::of_tree(tree()).unwrap())).unwrap()
}

fn local(iri: &str) -> String {
    iri.rsplit('#').next().unwrap().to_string()
}

/// A timeline that moves on five seconds at every read, as the Python case's does.
struct Ticking(Mutex<DateTime>);

impl Clock for Ticking {
    fn now(&self) -> DateTime {
        let mut at = self.0.lock().unwrap();
        *at = at.checked_add_day_time_duration(DayTimeDuration::new(5)).unwrap();
        *at
    }
}

/// A clock that stands still.
struct Still;

impl Clock for Still {
    fn now(&self) -> DateTime {
        now()
    }
}

fn on(store: &Store) -> BTreeSet<(String, String)> {
    store
        .rows(ON_Q, &[])
        .unwrap()
        .iter()
        .map(|r| (local(&iri(r, "d").unwrap()), local(&iri(r, "below").unwrap())))
        .collect()
}

fn pairs(items: &[(&str, &str)]) -> BTreeSet<(String, String)> {
    items.iter().map(|(a, b)| (a.to_string(), b.to_string())).collect()
}

/// The agent's own beliefs, as the state documents were.
fn own(store: &Store) -> Vec<String> {
    let mut shared = store.graphs_of(&[BELIEF], &Within::common()).unwrap();
    shared.extend(
        store
            .graphs_of(&[SELF_GRAPH, REVISION, COMMITTED], &Within::default())
            .unwrap(),
    );
    store
        .graphs_of(&[BELIEF], &Within::default())
        .unwrap()
        .into_iter()
        .filter(|g| !shared.contains(g))
        .collect()
}

/// The world less its large disk, and the conclusions drawn of the three taken back, so the runtime revises the
/// state again at its start.
fn two_disks(store: &Store) {
    store
        .update(&format!("DELETE WHERE {{ GRAPH ?g {{ <{TOWER}disk_3> ?p ?o }} }}"))
        .unwrap();
    for graph in store.graphs_of(&[BELIEF], &Within::default()).unwrap() {
        hash_named_graph(store, &graph, None).unwrap();
    }
    let own = own(store);
    let own: Vec<&str> = own.iter().map(String::as_str).collect();
    for graph in store.revisions_of(&own, BELIEF).unwrap() {
        store.forget_graph(&graph, Some(BELIEF)).unwrap();
    }
}

#[test]
fn the_runtime_concludes_what_each_disk_is_on_from_where_it_stands() {
    let store = store();
    let clock = Still;
    let loaded = booted(&store, tree(), &world(), "mover", now()).unwrap();
    for package in ["belief", "planning", "execution"] {
        assert!(loaded.iter().any(|p| p == package), "{package}: {loaded:?}");
    }
    let mut parts = assemble(&store, "mover", &clock, &loaded, None).unwrap();
    let lent: Vec<(String, &mut dyn Part)> = parts
        .iter_mut()
        .map(|(p, part)| (p.clone(), part.as_mut() as &mut dyn Part))
        .collect();
    let runtime = Runtime::new(&store, "mover", &clock, lent).unwrap();
    assert_eq!(runtime.parts(), ["belief", "planning", "execution"]);
    assert_eq!(
        on(&store),
        pairs(&[("disk_1", "disk_2"), ("disk_2", "disk_3"), ("disk_3", "PegA")])
    );
}

#[test]
fn the_puzzle_is_planned_above_and_carried_out_by_the_van_below() {
    let store = store();
    let clock = Ticking(Mutex::new(now()));
    let loaded = booted(&store, tree(), &world(), "mover", clock.now()).unwrap();
    two_disks(&store);
    let mut parts = assemble(&store, "mover", &clock, &loaded, None).unwrap();
    let lent: Vec<(String, &mut dyn Part)> = parts
        .iter_mut()
        .map(|(p, part)| (p.clone(), part.as_mut() as &mut dyn Part))
        .collect();
    let mut runtime = Runtime::new(&store, "mover", &clock, lent).unwrap();
    let outcome = runtime.run(Some(120), 0.0).unwrap();
    runtime.stop();
    assert_eq!(outcome, MET);
    let at: BTreeMap<String, (i64, i64)> = store
        .rows(AT_Q, &[])
        .unwrap()
        .iter()
        .filter(|r| iri(r, "s").unwrap().starts_with(TOWER))
        .map(|r| {
            (
                local(&iri(r, "s").unwrap()),
                (
                    value(r, "x").unwrap().parse().unwrap(),
                    value(r, "y").unwrap().parse().unwrap(),
                ),
            )
        })
        .collect();
    assert_eq!(at["disk_1"], (1, 2), "both disks at peg C's position: {at:?}");
    assert_eq!(at["disk_2"], (1, 2), "{at:?}");
    assert_eq!(
        on(&store),
        pairs(&[("disk_1", "disk_2"), ("disk_2", "PegC")]),
        "and stacked in order"
    );
    let refined: usize = value(&store.rows(REFINED_Q, &[]).unwrap()[0], "n")
        .unwrap()
        .parse()
        .unwrap();
    assert_eq!(
        refined, 3,
        "each of the three moves was kept below, and none was taken as fictive"
    );
}

/// As `agent/metrics/tests/test_window.py`'s last case holds it: the mover, which plans, walks and deliberates, writes
/// the window it was in as it stops — the one pass tallied, every level as it last stood — so the window holds every
/// one of those three packages' figures, tagged with the world.
#[test]
fn the_last_window_is_written_as_the_process_stops() {
    let store = store();
    let loaded = booted(&store, tree(), &world(), "mover", now()).unwrap();
    let written: std::rc::Rc<std::cell::RefCell<Vec<orexis::events::Point>>> = Default::default();
    let kept = written.clone();
    let sink = orexis::series::Sink::new(
        "METRICS",
        "m",
        Box::new(move |_, points| {
            kept.borrow_mut().extend(points.iter().cloned());
            Ok(())
        }),
    );
    let mut wiring = orexis_agent::Wiring::default();
    wiring.watching.metrics = Some(orexis_metrics::Window::new(sink, 3600.0, Some("tower"), Some("mover")));
    let clock = Still;
    let (mut parts, seen) = orexis_agent::assemble_seen(&store, "mover", &clock, &loaded, None, wiring).unwrap();
    {
        let lent: Vec<(String, &mut dyn Part)> = parts
            .iter_mut()
            .map(|(p, part)| (p.clone(), part.as_mut() as &mut dyn Part))
            .collect();
        let mut runtime = Runtime::new(&store, "mover", &clock, lent).unwrap();
        runtime.watch = seen.watch.clone();
        runtime.run(Some(1), 0.0).unwrap();
        runtime.stop();
    }
    let by: BTreeMap<String, orexis::events::Point> = written
        .borrow()
        .iter()
        .map(|p| (p.measurement.clone(), p.clone()))
        .collect();
    assert_eq!(
        by["pass"].fields["count"],
        orexis::events::Field::Int(1),
        "the one pass, written at the stop"
    );
    assert!(matches!(by["pass"].fields["quads"], orexis::events::Field::Int(n) if n > 0));
    for m in ["planner", "imaginarium", "search", "revise", "revisions", "intentions"] {
        assert!(by.contains_key(m), "{m} in {:?}", by.keys());
    }
    assert!(written.borrow().iter().all(|p| p.tags["world"] == "tower"));
}
