//! Tower of Hanoi on the binary, held to what `world/hanoi/tests/test_hanoi.py` holds the Python runtime to: the world
//! boots from its files, the mover plans the tower, and the run stops `planned` once the plan is published — the
//! mover is a planner and no executor, so the plan is its output and nothing walks it (#928). The tests of the
//! Python file that hold its metrics wait for the metrics package.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use oxsdatatypes::{DateTime, DayTimeDuration};

use orexis::boot::{TREE, packages_of};
use orexis::clock::{Clock, Manual, instant};
use orexis::namespaces::Namespaces;
use orexis::ontology::{BELIEF, PLAN, SELF_GRAPH};
use orexis::runtime::{PLANNED, Part, Runtime};
use orexis::store::{Store, Within, iri, value};
use orexis_agent::booted;
use orexis_planning::create::Planning;

const WANT: &str = "http://example.org/orexis/planning#WantGraph";
const REVISION: &str = "http://example.org/orexis/belief#RevisionGraph";
const COMMITTED: &str = "http://example.org/orexis/execution#CommittedStepGraph";

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn world() -> PathBuf {
    tree().parent().unwrap().join("world/hanoi")
}

fn now() -> DateTime {
    instant("2026-01-01T12:00:00+00:00").unwrap()
}

fn store() -> Store {
    Store::new(Arc::new(Namespaces::of_tree(tree()).unwrap())).unwrap()
}

fn boot(store: &Store) -> Vec<String> {
    booted(store, tree(), &world(), "hanoi", now()).unwrap()
}

/// A timeline that moves on a second at every read, as a running agent's does.
struct Ticking(Mutex<DateTime>);

impl Clock for Ticking {
    fn now(&self) -> DateTime {
        let mut at = self.0.lock().unwrap();
        *at = at.checked_add_day_time_duration(DayTimeDuration::new(1)).unwrap();
        *at
    }
}

const HOME_Q: &str = "PREFIX hanoi: <http://example.org/orexis/hanoi#>
SELECT (COUNT(DISTINCT ?d) AS ?n) WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph }
  GRAPH ?g { ?d (hanoi:on)+ hanoi:PegC } }";
const STEPS_Q: &str = "PREFIX hanoi: <http://example.org/orexis/hanoi#>
SELECT ?plan ?spent ?step ?next ?disk ?onto WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?plan a orexis:PlanGraph }
  GRAPH ?plan { ?plan planning:spent ?spent . ?step a execution:Step ; hanoi:disk ?disk ; hanoi:onto ?onto .
                OPTIONAL { ?step execution:then ?next } } }";
const ESTIMATE_Q: &str = "
SELECT ?left WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:weighs ?g ; planning:remaining ?left .
               ?g a planning:GroundGraph } }";
const TEXTBOOK: [(&str, &str); 7] = [
    ("disk_1", "PegC"),
    ("disk_2", "PegB"),
    ("disk_1", "PegB"),
    ("disk_3", "PegC"),
    ("disk_1", "PegA"),
    ("disk_2", "PegC"),
    ("disk_1", "PegC"),
];

fn home(store: &Store) -> usize {
    value(&store.rows(HOME_Q, &[]).unwrap()[0], "n")
        .unwrap()
        .parse()
        .unwrap()
}

fn local(iri: &str) -> String {
    iri.rsplit('#').next().unwrap().to_string()
}

/// The one plan published: what it spent, and its moves walked from its head.
fn plan(store: &Store) -> (f64, Vec<(String, String)>) {
    let found = store.rows(STEPS_Q, &[]).unwrap();
    let plans: std::collections::BTreeSet<String> = found.iter().filter_map(|r| iri(r, "plan")).collect();
    assert_eq!(plans.len(), 1, "one plan published");
    let after: BTreeMap<String, Option<String>> = found
        .iter()
        .map(|r| (iri(r, "step").unwrap(), iri(r, "next")))
        .collect();
    let moves: BTreeMap<String, (String, String)> = found
        .iter()
        .map(|r| {
            (
                iri(r, "step").unwrap(),
                (local(&iri(r, "disk").unwrap()), local(&iri(r, "onto").unwrap())),
            )
        })
        .collect();
    let followers: std::collections::BTreeSet<&String> = after.values().flatten().collect();
    let mut step = after.keys().find(|s| !followers.contains(s)).cloned();
    let mut out = Vec::new();
    while let Some(s) = step {
        out.push(moves[&s].clone());
        step = after[&s].clone();
    }
    (value(&found[0], "spent").unwrap().parse().unwrap(), out)
}

fn textbook() -> Vec<(String, String)> {
    TEXTBOOK.iter().map(|(d, p)| (d.to_string(), p.to_string())).collect()
}

/// The agent's own beliefs: no world's document, no self graph, no revision and no committed step.
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

/// One run of the mover over `store` at `budget`: the outcome, and the planning part left.
fn ran<'s>(store: &'s Store, budget: usize, clock: &'s dyn Clock, passes: usize) -> (String, Planning<'s>) {
    let mut planning = Planning::new(store, "hanoi", Some(budget)).unwrap();
    let outcome = {
        let parts: Vec<(String, &mut dyn Part)> = vec![("planning".into(), &mut planning)];
        let mut runtime = Runtime::new(store, "hanoi", clock, parts).unwrap();
        assert_eq!(runtime.parts(), ["planning"]);
        runtime.run(Some(passes), 0.0).unwrap()
    };
    (outcome, planning)
}

#[test]
fn the_boot_says_what_each_graph_is() {
    let store = store();
    boot(&store);
    assert_eq!(store.graphs_of(&[WANT], &Within::default()).unwrap().len(), 1);
    assert_eq!(own(&store).len(), 1);
    assert_eq!(home(&store), 0, "three disks on peg A");
    let scopes = store
        .rows(
            "SELECT (COUNT(?s) AS ?n) WHERE { GRAPH ?g { ?s a planning:Scope } }",
            &[],
        )
        .unwrap();
    assert!(
        value(&scopes[0], "n").unwrap().parse::<usize>().unwrap() >= 1,
        "the scopes were written at boot"
    );
}

#[test]
fn the_mover_loads_planning_and_nothing_else() {
    let store = store();
    assert_eq!(boot(&store), ["planning"]);
    assert_eq!(packages_of(&store, tree()).unwrap(), ["planning"]);
    let absent = [
        "execution/ontology.ttl",
        "belief/ontology.ttl",
        "sensing/ontology.ttl",
        "sensing/rules.ttl",
        "prediction/ontology.ttl",
        "speech/ontology.ttl",
        "transport/mqtt/ontology.ttl",
    ];
    let present = ["ontology.ttl", "planning/ontology.ttl"];
    let held = |p: &str| {
        let uri = orexis::document::file_uri(&tree().join(p)).unwrap();
        !store
            .rows(
                &format!("SELECT ?p WHERE {{ GRAPH ?g {{ <{uri}> ?p ?o }} }} LIMIT 1"),
                &[],
            )
            .unwrap()
            .is_empty()
    };
    for p in absent {
        assert!(!held(p), "{p} is not the mover's to read");
    }
    for p in present {
        assert!(held(p), "{p} is read");
    }
}

#[test]
fn the_plan_is_the_seven_textbook_moves_at_a_cost_the_estimate_does_not_exceed() {
    let store = store();
    boot(&store);
    let clock = Manual::at(now());
    let (outcome, planning) = ran(&store, 64, &clock, 20);
    assert_eq!(outcome, PLANNED);
    let (spent, moves) = plan(&store);
    assert_eq!((spent, moves), (7.0, textbook()));
    let estimates: Vec<f64> = {
        let planner = planning.planner.borrow();
        let im = planner.imaginaria.values().next().unwrap();
        im.rows(ESTIMATE_Q, &[])
            .unwrap()
            .iter()
            .filter_map(|r| value(r, "left")?.parse().ok())
            .collect()
    };
    assert_eq!(estimates, [3.0], "an estimate never overstates what the plan cost");
    assert_eq!(home(&store), 0, "a plan published moves no disk");
    let published = store.graphs_of(&[PLAN], &Within::default()).unwrap();
    drop(planning);
    let (again, _) = ran(&store, 64, &clock, 20);
    assert_eq!(again, PLANNED);
    assert_eq!(
        store.graphs_of(&[PLAN], &Within::default()).unwrap(),
        published,
        "a second run publishes nothing new"
    );
}

#[test]
fn a_budget_that_cuts_the_search_short_is_finished_by_the_passes_after() {
    let store = store();
    boot(&store);
    let clock = Ticking(Mutex::new(now()));
    let (outcome, _) = ran(&store, 20, &clock, 12);
    assert_eq!(outcome, PLANNED);
    assert_eq!(plan(&store), (7.0, textbook()));
}

#[cfg(feature = "volume")]
#[test]
fn a_lived_in_volume_keeps_the_plan_and_does_not_search_again() {
    let path = std::env::temp_dir().join(format!("orexis-hanoi-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&path);
    let clock = Ticking(Mutex::new(now()));
    {
        let store = Store::open(&path, Arc::new(Namespaces::of_tree(tree()).unwrap())).unwrap();
        boot(&store);
        assert_eq!(ran(&store, 64, &clock, 20).0, PLANNED);
    }
    let store = Store::open(&path, Arc::new(Namespaces::of_tree(tree()).unwrap())).unwrap();
    let published = store.graphs_of(&[PLAN], &Within::default()).unwrap();
    boot(&store);
    assert!(
        published.len() == 1 && store.graphs_of(&[PLAN], &Within::default()).unwrap() == published,
        "the plan is the agent's"
    );
    assert_eq!(store.graphs_of(&[WANT], &Within::default()).unwrap().len(), 1);
    assert_eq!(home(&store), 0);
    let (outcome, planning) = ran(&store, 64, &clock, 20);
    assert_eq!(outcome, PLANNED);
    assert!(
        planning.planner.borrow().imaginaria.values().all(|im| im
            .graphs_of(&[orexis_planning::ontology::POSSIBLE_GRAPH], &Within::default())
            .unwrap()
            .is_empty()),
        "the want is walked by the plan it has, and nothing searches it again"
    );
    assert_eq!(plan(&store), (7.0, textbook()));
    drop(planning);
    drop(store);
    let _ = std::fs::remove_dir_all(&path);
}
