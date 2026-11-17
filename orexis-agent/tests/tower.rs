//! The tower on the binary, held to what `world/tower/tests/test_tower.py` holds the Python runtime to: hanoi's puzzle
//! on the courier's grid, planned one level inside the other. The world's rules say what a disk is on from where it
//! stands, so the mover is a deliberator as well as a planner and an executor: belief revises the state at the
//! start, and every graph the executor writes as the world as it is written. Run on TWO disks, the world's third
//! taken out of the booted beliefs, as the Python gate runs it.

mod common;

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

use oxsdatatypes::DateTime;

use orexis::boot::TREE;
use orexis::clock::instant;
use orexis::hash::hash_named_graph;
use orexis::ontology::{BELIEF, SELF_GRAPH};
use orexis::store::{Store, Within, iri, value};
use orexis::task::{MET, Provided};

const TOWER: &str = "http://example.org/orexis/world/tower#";
const REVISION: &str = "http://example.org/orexis/belief#RevisionGraph";
const COMMITTED: &str = "http://example.org/orexis/execution#CommittedStepGraph";

/// Where each of the tower's things is believed to stand, by its local name.
fn positions(store: &Store) -> BTreeMap<String, (i64, i64)> {
    const AT_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?s ?x ?y WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph } GRAPH ?g { ?s courier:x ?x ; courier:y ?y } } ORDER BY ?s";
    store
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
        .collect()
}

/// How many steps were refined.
fn refined(store: &Store) -> usize {
    const REFINED_Q: &str = "PREFIX execution: <http://example.org/orexis/execution#>
        SELECT (COUNT(?a) AS ?n) WHERE { GRAPH ?g { ?a execution:refinedBy ?w } }";
    value(&store.rows(REFINED_Q, &[]).unwrap()[0], "n")
        .unwrap()
        .parse()
        .unwrap()
}

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn world() -> PathBuf {
    tree().join("world/tower")
}

fn now() -> DateTime {
    instant("2026-01-01T12:00:00+00:00").unwrap()
}

fn store() -> Store {
    Store::new().unwrap()
}

fn local(iri: &str) -> String {
    iri.rsplit('#').next().unwrap().to_string()
}

fn on(store: &Store) -> BTreeSet<(String, String)> {
    const ON_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
    PREFIX hanoi: <http://example.org/orexis/hanoi#>
    SELECT ?d ?below WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph } GRAPH ?g { ?d hanoi:on ?below } } ORDER BY ?d";
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

#[tokio::test(start_paused = true)]
async fn the_agent_concludes_what_each_disk_is_on_from_where_it_stands() {
    let store = store();
    let booted = orexis_agent::boot(&store, &world(), "mover", common::clock(now()), Provided::default()).unwrap();
    let running = booted.start().await.unwrap();
    let parts = running.parts();
    for package in ["belief", "planning", "execution"] {
        assert!(parts.iter().any(|p| p == package), "{package}: {parts:?}");
    }
    assert_eq!(
        on(&store),
        pairs(&[("disk_1", "disk_2"), ("disk_2", "disk_3"), ("disk_3", "PegA")])
    );
}

#[tokio::test(start_paused = true)]
async fn the_puzzle_is_planned_above_and_carried_out_by_the_van_below() {
    let store = store();
    let booted = orexis_agent::boot(&store, &world(), "mover", common::clock(now()), Provided::default()).unwrap();
    two_disks(&store);
    let running = booted.start().await.unwrap();
    let outcome = common::outcome(&running, 3600).await;
    running.stop().await;
    assert_eq!(outcome, MET);
    let at = positions(&store);
    assert_eq!(at["disk_1"], (1, 2), "both disks at peg C's position: {at:?}");
    assert_eq!(at["disk_2"], (1, 2), "{at:?}");
    assert_eq!(
        on(&store),
        pairs(&[("disk_1", "disk_2"), ("disk_2", "PegC")]),
        "and stacked in order"
    );
    let refined = refined(&store);
    assert_eq!(
        refined, 3,
        "each of the three moves was kept below, and none was taken as fictive"
    );
}

/// How the two-disk puzzle ends where the packages are started in `order`: how the run ended, the instant it ended
/// at, where everything stands, what each disk is on, and how many moves were kept below.
type Walked = (
    String,
    String,
    BTreeMap<String, (i64, i64)>,
    BTreeSet<(String, String)>,
    usize,
);

async fn walked(order: &[&str]) -> Walked {
    use orexis::clock::Clock;
    let store = store();
    let clock = common::clock(now());
    let booted = orexis_agent::boot(&store, &world(), "mover", clock.clone(), Provided::default()).unwrap();
    //  THE RECORDER'S PACKAGE, WHAT KEEPS HOUSE FOR IT AND THE METRICS begin on no event and are handed nothing
    //  here, so no order is asked of them.
    let watching = ["journal", "journal-oxigraph", "journal-otlp", "metrics"];
    two_disks(&store);
    let order: Vec<String> = order.iter().map(|p| p.to_string()).collect();
    let running = booted.first(&order).unwrap().start().await.unwrap();
    //  THE ORDER THE STARTS ARE SPAWNED IN, not the order they say they started: an executor depends on a planner
    //  (`orexis:dependsOn`), so execution makes its core once planning has made its own, whichever was spawned first.
    let started: BTreeSet<String> = running
        .parts()
        .into_iter()
        .filter(|p| !watching.contains(&p.as_str()))
        .collect();
    assert_eq!(
        started,
        order.iter().cloned().collect::<BTreeSet<_>>(),
        "the order names every package the mover runs"
    );
    let outcome = common::outcome(&running, 3600).await;
    let ended = clock.now().to_string();
    running.stop().await;
    let at = positions(&store);
    let refined = refined(&store);
    (outcome, ended, at, on(&store), refined)
}

/// Planning and execution both begin on what belief revised, and neither waits for the other: whichever is started
/// first, and so hears a revision first, the puzzle is walked home the same way and ends at the same instant. The one
/// thing between them that needs an order, taking a head, is asked and answered.
#[tokio::test(start_paused = true)]
async fn the_puzzle_ends_the_same_whichever_of_planning_and_execution_hears_a_revision_first() {
    let planning_first = walked(&["belief", "planning", "execution"]).await;
    let execution_first = walked(&["belief", "execution", "planning"]).await;
    assert_eq!(planning_first.0, MET);
    assert_eq!(planning_first, execution_first);
    let belief_last = walked(&["planning", "execution", "belief"]).await;
    assert_eq!(planning_first, belief_last);
}

/// As `agent/metrics/tests/test_window.py`'s last case holds it: the mover, which plans, walks and deliberates, writes
/// the window it was in as it stops — the one pass tallied, every level as it last stood — so the window holds every
/// one of those three packages' figures, tagged with the world.
#[tokio::test(start_paused = true)]
async fn the_last_window_is_written_as_the_process_stops() {
    let store = store();
    let written: std::sync::Arc<std::sync::Mutex<Vec<orexis::events::Point>>> = Default::default();
    let kept = written.clone();
    let sink = orexis::series::Sink::new(
        "METRICS",
        "m",
        Box::new(move |_, points| {
            kept.lock().unwrap().extend(points.iter().cloned());
            Ok(())
        }),
    );
    let provided = Provided::default().with(orexis_metrics::Window::new(sink, 3600.0, Some("tower"), Some("mover")));
    let booted = orexis_agent::boot(&store, &world(), "mover", common::clock(now()), provided).unwrap();
    common::metered(&store);
    let running = booted.start().await.unwrap();
    common::settled(&running).await;
    running.stop().await;
    let by: BTreeMap<String, orexis::events::Point> = written
        .lock()
        .unwrap()
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
    assert!(written.lock().unwrap().iter().all(|p| p.tags["world"] == "tower"));
}
