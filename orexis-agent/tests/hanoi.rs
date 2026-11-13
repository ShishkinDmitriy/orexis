//! Tower of Hanoi on the binary, held to what `world/hanoi/tests/test_hanoi.py` holds the Python runtime to: the world
//! boots from its files, the mover plans the tower, and the run stops `planned` once the plan is published — the
//! mover is a planner and no executor, so the plan is its output and nothing walks it (#928) — and its metrics and its
//! journal, as the Python file and `agent/planning/tests/test_events.py` hold them.

mod common;

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use oxsdatatypes::DateTime;

use orexis::boot::{TREE, packages_of};
use orexis::clock::instant;
use orexis::namespaces::Namespaces;
use orexis::ontology::{BELIEF, PLAN, SELF_GRAPH};
use orexis::store::{Store, Within, iri, value};
use orexis::task::PLANNED;
use orexis_agent::booted;

const WANT: &str = "http://example.org/orexis/planning#WantGraph";
const REVISION: &str = "http://example.org/orexis/belief#RevisionGraph";
const COMMITTED: &str = "http://example.org/orexis/execution#CommittedStepGraph";

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn world() -> PathBuf {
    tree().join("world/hanoi")
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

const HOME_Q: &str = "PREFIX hanoi: <http://example.org/orexis/hanoi#>
SELECT (COUNT(DISTINCT ?d) AS ?n) WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph }
  GRAPH ?g { ?d (hanoi:on)+ hanoi:PegC } }";
const STEPS_Q: &str = "PREFIX hanoi: <http://example.org/orexis/hanoi#>
SELECT ?plan ?spent ?step ?next ?disk ?onto WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?plan a orexis:PlanGraph }
  GRAPH ?plan { ?plan planning:spent ?spent . ?step a execution:Step ; hanoi:disk ?disk ; hanoi:onto ?onto .
                OPTIONAL { ?step execution:then ?next } } }";
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

/// One run of the mover over `store` at `budget`, planning alone: how it ended within `within` seconds of its time.
async fn ran(store: &Store, budget: usize, within: u64) -> String {
    let loaded = ["planning".to_string()];
    let wiring = orexis_agent::Wiring::default();
    let running = orexis_agent::start(store, "hanoi", common::clock(now()), &loaded, Some(budget), wiring).unwrap();
    assert_eq!(running.parts(), ["planning"]);
    let outcome = common::outcome(&running, within).await;
    running.stop().await;
    outcome
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
fn the_mover_loads_planning_and_its_journal_and_nothing_else() {
    let store = store();
    assert_eq!(boot(&store), ["planning", "journal"], "a planner and a recorder");
    assert_eq!(packages_of(&store, tree()).unwrap(), ["planning", "journal"]);
    let absent = [
        "orexis-execution/ontology.ttl",
        "orexis-belief/ontology.ttl",
        "orexis-sensing/ontology.ttl",
        "orexis-sensing/rules.ttl",
        "orexis-prediction/ontology.ttl",
        "orexis-speech/ontology.ttl",
        "orexis-transport-mqtt/ontology.ttl",
    ];
    let present = ["orexis/ontology.ttl", "orexis-planning/ontology.ttl"];
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

#[tokio::test(start_paused = true)]
async fn the_plan_is_the_seven_textbook_moves() {
    let store = store();
    boot(&store);
    assert_eq!(ran(&store, 64, 20).await, PLANNED);
    let (spent, moves) = plan(&store);
    assert_eq!((spent, moves), (7.0, textbook()));
    assert_eq!(home(&store), 0, "a plan published moves no disk");
    let published = store.graphs_of(&[PLAN], &Within::default()).unwrap();
    assert_eq!(ran(&store, 64, 20).await, PLANNED);
    assert_eq!(
        store.graphs_of(&[PLAN], &Within::default()).unwrap(),
        published,
        "a second run publishes nothing new"
    );
}

#[tokio::test(start_paused = true)]
async fn a_budget_that_cuts_the_search_short_is_finished_by_the_plannings_after() {
    let store = store();
    boot(&store);
    assert_eq!(ran(&store, 20, 30).await, PLANNED);
    assert_eq!(plan(&store), (7.0, textbook()));
}

#[cfg(feature = "volume")]
#[tokio::test(start_paused = true)]
async fn a_lived_in_volume_keeps_the_plan_and_does_not_search_again() {
    let path = std::env::temp_dir().join(format!("orexis-hanoi-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&path);
    {
        let store = Store::open(&path, Arc::new(Namespaces::of_tree(tree()).unwrap())).unwrap();
        boot(&store);
        assert_eq!(ran(&store, 64, 20).await, PLANNED);
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
    let weighed = store.len().unwrap();
    assert_eq!(ran(&store, 64, 20).await, PLANNED);
    assert_eq!(
        store.graphs_of(&[PLAN], &Within::default()).unwrap(),
        published,
        "the want is walked by the plan it has, and nothing publishes another"
    );
    let _ = weighed;
    assert_eq!(plan(&store), (7.0, textbook()));
    drop(store);
    let _ = std::fs::remove_dir_all(&path);
}

/// Three disks at twenty candidates a pass, with a metrics window `interval_s` long — nought writes one a pass, and
/// anything longer than the run writes one at the end, as a stop does: every window written, as `_metered` in
/// `world/hanoi/tests/test_hanoi.py` collects them.
async fn metered(interval_s: f64) -> Vec<Vec<orexis::events::Point>> {
    use orexis::events::Point;
    let store = store();
    let loaded = boot(&store);
    let writes: std::sync::Arc<std::sync::Mutex<Vec<Vec<Point>>>> = Default::default();
    let kept = writes.clone();
    let sink = orexis::series::Sink::new(
        "METRICS",
        "hanoi-hanoi-metrics",
        Box::new(move |_, points| {
            kept.lock().unwrap().push(points.to_vec());
            Ok(())
        }),
    );
    let window = orexis_metrics::Window::new(sink, interval_s, Some("hanoi"), Some("hanoi"));
    let wiring = orexis_agent::Wiring {
        watching: orexis_agent::Watching {
            metrics: Some(window),
            ..Default::default()
        },
        ..Default::default()
    };
    let running = orexis_agent::start(&store, "hanoi", common::clock(now()), &loaded, Some(20), wiring).unwrap();
    assert_eq!(common::outcome(&running, 30).await, PLANNED);
    running.stop().await;
    writes
        .lock()
        .unwrap()
        .iter()
        .filter(|w| !w.is_empty())
        .cloned()
        .collect()
}

fn float(point: &orexis::events::Point, field: &str) -> f64 {
    match point.fields.get(field) {
        Some(orexis::events::Field::Float(f)) => *f,
        Some(orexis::events::Field::Int(i)) => *i as f64,
        other => panic!("{} has no {field}: {other:?}", point.measurement),
    }
}

#[tokio::test(start_paused = true)]
async fn a_window_a_stretch_writes_the_planners_levels_and_the_runs_own_and_nothing_of_execution() {
    use orexis::events::Field;
    let windows = metered(0.0).await;
    let first: BTreeMap<&str, &orexis::events::Point> =
        windows[0].iter().map(|p| (p.measurement.as_str(), p)).collect();
    for m in ["pass", "planner", "imaginarium", "search", "reroot"] {
        assert!(first.contains_key(m), "{m} in {:?}", first.keys());
    }
    let ints = |pairs: &[(&str, i64)]| -> BTreeMap<String, Field> {
        pairs.iter().map(|(k, v)| (k.to_string(), Field::Int(*v))).collect()
    };
    assert_eq!(
        first["imaginarium"].fields,
        ints(&[
            ("worlds", 20),
            ("weighings", 21),
            ("open", 3),
            ("met", 0),
            ("satisfied", 0),
            ("exhausted", 1),
            ("no_candidate", 0)
        ])
    );
    assert!(!first["imaginarium"].tags["scope"].is_empty());
    let every: std::collections::BTreeSet<&str> = windows.iter().flatten().map(|p| p.measurement.as_str()).collect();
    for m in ["intentions", "intention", "act", "silence", "revisions"] {
        assert!(!every.contains(m), "{m} is not the mover's: {every:?}");
    }
    let passes: Vec<&orexis::events::Point> = windows.iter().flatten().filter(|p| p.measurement == "pass").collect();
    assert_eq!(passes.len(), 3);
    for p in &passes {
        assert_eq!(p.fields["count"], Field::Int(1));
        assert!(float(p, "duration_s_max") > 0.0 && float(p, "quads") > 0.0 && float(p, "uptime_s") > 0.0);
        let phases: f64 = p
            .fields
            .keys()
            .filter(|k| k.ends_with("_s_sum") && *k != "duration_s_sum")
            .map(|k| float(p, k))
            .sum();
        assert!(
            phases > 0.0 && phases <= float(p, "duration_s_sum"),
            "the parts are of the pass"
        );
    }
}

#[tokio::test(start_paused = true)]
async fn every_search_and_the_publishing_are_tallied_into_one_window_and_never_by_the_want() {
    let windows = metered(3600.0).await;
    assert_eq!(windows.len(), 1, "one window, written at the stop");
    let window = &windows[0];
    let by = |m: &str| -> Vec<&orexis::events::Point> { window.iter().filter(|p| p.measurement == m).collect() };
    let searches: BTreeMap<String, &orexis::events::Point> = by("search")
        .into_iter()
        .map(|p| (p.tags["outcome"].clone(), p))
        .collect();
    assert_eq!(float(searches["Exhausted"], "count"), 2.0);
    assert_eq!(float(searches["Exhausted"], "weighed_sum"), 40.0);
    assert_eq!(float(searches["Satisfied"], "count"), 1.0);
    assert_eq!(float(searches["Exhausted"], "budget_max"), 20.0);
    let published = by("published");
    assert_eq!(published.len(), 1);
    let p = published[0];
    assert_eq!(
        (float(p, "count"), float(p, "passes_max"), float(p, "replan")),
        (1.0, 3.0, 0.0)
    );
    assert_eq!(float(p, "cost_max"), 7.0);
    assert!(0.0 <= float(p, "estimate_max") && float(p, "estimate_max") <= float(p, "cost_max"));
    let searched: f64 = searches.values().map(|s| float(s, "duration_s_sum")).sum();
    assert!(float(p, "wall_s_max") >= searched && searched > 0.0);
    let passed = by("pass");
    assert_eq!(float(passed[0], "count"), 3.0);
    let rerooted: f64 = by("reroot").iter().map(|r| float(r, "count")).sum();
    assert_eq!(rerooted, float(by("planner")[0], "count"));
    assert_eq!(rerooted, 3.0);
    assert!(
        !p.tags.contains_key("desire"),
        "an authored want was derived under no desire"
    );
    for point in window {
        assert_eq!(
            (point.tags["world"].as_str(), point.tags["agent"].as_str()),
            ("hanoi", "hanoi")
        );
        assert!(!point.tags.contains_key("want") && !point.fields.contains_key("want"));
        assert!(!point.tags.values().any(|v| v.contains("every_disk_home")));
    }
    assert!(window.len() < 20, "a point per measurement and tag set a window");
}

#[tokio::test(start_paused = true)]
async fn a_plan_published_is_kept_in_the_journal_with_its_steps_in_the_words_of_the_domain() {
    let store = store();
    let loaded = boot(&store);
    let journal = Arc::new(orexis_journal::journal::Journal::new(600.0, Arc::new(now)).unwrap());
    let wiring = orexis_agent::Wiring {
        watching: orexis_agent::Watching {
            journal: Some(journal.clone()),
            ..Default::default()
        },
        ..Default::default()
    };
    let running = orexis_agent::start(&store, "hanoi", common::clock(now()), &loaded, Some(400), wiring).unwrap();
    common::settled(&running).await;
    running.stop().await;
    let text = "PREFIX planning: <http://example.org/orexis/planning#> PREFIX execution: <http://example.org/orexis/execution#>
PREFIX hanoi: <http://example.org/orexis/hanoi#>
SELECT ?step ?disk ?onto (COUNT(?before) AS ?order) WHERE {
  ?e a planning:PlanPublished ; planning:published ?plan . ?step execution:partOf ?plan ; planning:fills hanoi:Move ;
  hanoi:disk ?disk ; hanoi:onto ?onto . OPTIONAL { ?before execution:then+ ?step } }
GROUP BY ?step ?disk ?onto ORDER BY ?order";
    let (_, body) = orexis_journal::journal::answer(&journal.store, text).unwrap();
    let body = String::from_utf8(body).unwrap();
    let mut moves = Vec::new();
    for row in body.split("\"step\":").skip(1) {
        let of = |var: &str| {
            let v = row.split(&format!("\"{var}\":")).nth(1).unwrap();
            local(v.split("\"value\":\"").nth(1).unwrap().split('"').next().unwrap())
        };
        moves.push((of("disk"), of("onto")));
    }
    assert_eq!(
        moves,
        textbook(),
        "the seven moves, in the order they are walked, read off the journal alone"
    );
}

#[tokio::test(start_paused = true)]
async fn the_history_part_marks_an_event_of_a_class_beneath_incident_and_no_other() {
    use orexis::events::Event;
    use orexis_planning::events::{PlanPublished, WantUnreachable};
    let store = store();
    let loaded = boot(&store);
    let journal = Arc::new(orexis_journal::journal::Journal::new(600.0, Arc::new(now)).unwrap());
    let wiring = orexis_agent::Wiring {
        watching: orexis_agent::Watching {
            journal: Some(journal.clone()),
            ..Default::default()
        },
        ..Default::default()
    };
    let running = orexis_agent::start(&store, "hanoi", common::clock(now()), &loaded, Some(1), wiring).unwrap();
    let watch = running.handed.events.watch().clone();
    let unreachable: &dyn Event = &WantUnreachable {
        want: "http://example.org/test#want".into(),
        desire: None,
        at: Some(now()),
    };
    watch.emit(unreachable);
    watch.emit(&PlanPublished {
        plan: "http://example.org/test#plan".into(),
        want: "http://example.org/test#want".into(),
        desire: None,
        derived_from: None,
        scope: None,
        passes: None,
        weighed: None,
        wall_s: None,
        estimate: None,
        cost: None,
        replan: false,
        at: Some(now()),
        said: Vec::new(),
    });
    let (_, body) = orexis_journal::journal::answer(
        &journal.store,
        "SELECT ?k WHERE { ?e a <http://example.org/orexis#Incident>, ?k FILTER(?k != <http://example.org/orexis#Incident>) }",
    )
    .unwrap();
    let body = String::from_utf8(body).unwrap();
    assert!(
        body.contains("WantUnreachable") && !body.contains("PlanPublished"),
        "off the agent's own T-Box: {body}"
    );
}
