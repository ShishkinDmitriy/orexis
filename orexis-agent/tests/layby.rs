//! The layby on the binary, held to the drives the Python courier sent: `world/layby/tests/test_layby.py`'s walks, the
//! van driven by command down the lane and round a fallen tree, replayed from what the simulator published to the
//! Python courier at each ten-second step — its van's fix, the receiver's peer and the radar's slot. The binary is
//! held to the same drives, each at the same instant and to the same cell, and to the same beliefs of where
//! everything stands at the end: a replay is the closed loop for as long as the drives agree, since the fix answers
//! the drive before it, and where the binary drove elsewhere the drives differ and the replay says so.

mod common;

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use oxsdatatypes::DateTime;
use serde_json::Value as Json;

use orexis::Error;
use orexis::boot::TREE;
use orexis::clock::{Clock, instant, isoformat};
use orexis::namespaces::Namespaces;
use orexis::ontology::BELIEF;
use orexis::store::{Store, Within, iri, value};
use orexis_agent::{Wiring, booted};
use orexis_transport_mqtt::driver::{Client, Mqtt};

const L: &str = "http://example.org/orexis/world/layby#";

/// WHERE EVERYTHING THE COURIER BELIEVES STANDS, save where a parcel is owed, which is authored and never moves.
const AT_Q: &str = "PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?s ?x ?y WHERE { ?s courier:x ?x ; courier:y ?y . FILTER(isIRI(?s)) FILTER NOT EXISTS { ?p courier:destination ?s } }";

/// Each drive sent: the time of day it was sent at, and the cell it was to.
type Drives = Vec<(String, i64, i64)>;

/// Every drive the courier sends, with the instant it was sent.
struct Bus {
    clock: Arc<dyn Clock>,
    drives: Arc<Mutex<Vec<(String, i64, i64)>>>,
}

impl Client for Bus {
    fn subscribe(&mut self, _pattern: &str) -> Result<(), Error> {
        Ok(())
    }

    fn publish(&mut self, topic: &str, payload: &[u8], _retain: bool) -> Result<(), Error> {
        assert_eq!(topic, "actuators/van_a/command", "nothing commands the parked van");
        let payload: Json = serde_json::from_slice(payload).map_err(|e| Error::Evaluation(e.to_string()))?;
        let at = isoformat(self.clock.now());
        let cell = (
            payload["to"]["x"].as_i64().unwrap(),
            payload["to"]["y"].as_i64().unwrap(),
        );
        self.drives
            .lock()
            .unwrap()
            .push((at[11..19].to_string(), cell.0, cell.1));
        Ok(())
    }
}

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn repo() -> &'static Path {
    tree()
}

/// Each step's instant and what was published then.
fn steps(fixture: &str) -> Vec<(DateTime, Vec<(String, String)>)> {
    let text = fs::read_to_string(
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("tests/fixtures")
            .join(fixture),
    )
    .unwrap();
    let mut out: Vec<(DateTime, Vec<(String, String)>)> = Vec::new();
    for line in text.lines().filter(|l| !l.starts_with('#') && !l.trim().is_empty()) {
        let mut fields = line.splitn(3, '\t');
        let at = instant(fields.next().unwrap()).unwrap();
        let (topic, payload) = (fields.next().unwrap_or_default(), fields.next().unwrap_or_default());
        if out.last().is_none_or(|(t, _)| *t != at) {
            out.push((at, Vec::new()));
        }
        if !topic.is_empty() {
            out.last_mut().unwrap().1.push((topic.to_string(), payload.to_string()));
        }
    }
    out
}

fn at(store: &Store) -> BTreeMap<String, (i64, i64)> {
    let beliefs = store.graphs_of(&[BELIEF], &Within::default()).unwrap();
    let beliefs: Vec<&str> = beliefs.iter().map(String::as_str).collect();
    store
        .rows(AT_Q, &beliefs)
        .unwrap()
        .iter()
        .map(|r| {
            (
                iri(r, "s").unwrap().rsplit('#').next().unwrap().to_string(),
                (
                    value(r, "x").unwrap().parse().unwrap(),
                    value(r, "y").unwrap().parse().unwrap(),
                ),
            )
        })
        .collect()
}

/// Walk the courier of `world` through `fixture`'s steps: the drives it sent and where it believes everything stands.
async fn walk(world: &Path, fixture: &str) -> (Drives, BTreeMap<String, (i64, i64)>) {
    let steps = steps(fixture);
    let store = Store::new(Arc::new(Namespaces::linked().unwrap())).unwrap();
    let clock: Arc<dyn Clock> = common::clock(steps[0].0);
    let loaded = booted(&store, world, "courier_a", steps[0].0).unwrap();
    let drives = Arc::new(Mutex::new(Vec::new()));
    let bus = Bus {
        clock: clock.clone(),
        drives: drives.clone(),
    };
    let member = Mqtt::new(&store, &format!("{L}courier_a"), vec![(None, Box::new(bus))]);
    let inbox = member.inbox.clone();
    let wiring = Wiring {
        mqtt: Some(member),
        ..Wiring::default()
    };
    let running = orexis_agent::start(&store, "courier_a", clock.clone(), &loaded, None, wiring).unwrap();
    //  THE WANTS THE COURIER IS WALKING, read off its intentions by an executor of the test's own.
    let reader = orexis_execution::Executor::new(&store, "courier_a", None, None, clock.clone()).unwrap();
    for (n, (when, published)) in steps.iter().enumerate() {
        let ahead = orexis::clock::seconds_of(when.checked_sub(clock.now()).unwrap());
        common::pass(&running, ahead.max(0.0)).await;
        for (topic, payload) in published {
            inbox.deliver(topic, payload.as_bytes(), Some(*when));
        }
        common::settled(&running).await;
        if n > 0 && reader.walking().unwrap().is_empty() {
            break;
        }
    }
    let walking = reader.walking().unwrap();
    assert!(walking.is_empty(), "the plan was walked to its end: {walking:?}");
    running.stop().await;
    let believed = at(&store);
    let sent = drives.lock().unwrap().clone();
    (sent, believed)
}

fn drives(said: &[(&str, i64, i64)]) -> Vec<(String, i64, i64)> {
    said.iter().map(|(t, x, y)| (t.to_string(), *x, *y)).collect()
}

fn believed(said: &[(&str, (i64, i64))]) -> BTreeMap<String, (i64, i64)> {
    said.iter().map(|(k, v)| (k.to_string(), *v)).collect()
}

#[tokio::test(start_paused = true)]
async fn the_van_is_driven_by_command_and_lands_where_the_fix_shows_it() {
    let (sent, at) = walk(&repo().join("world/layby"), "layby.tsv").await;
    assert_eq!(
        sent,
        drives(&[
            ("12:00:00", 1, 1),
            ("12:00:50", 2, 1),
            ("12:01:40", 3, 1),
            ("12:02:30", 4, 1),
            ("12:03:20", 5, 1),
            ("12:04:10", 6, 1)
        ]),
        "six drives east along the lane, each when the Python courier sent it"
    );
    assert_eq!(
        at,
        believed(&[
            ("contact_1", (4, 0)),
            ("parcel_a", (6, 1)),
            ("van_a", (6, 1)),
            ("van_b", (6, 0))
        ])
    );
}

/// The layby with its documents rewritten, as `test_layby.py`'s `variant` rewrites it — a copy beside the domains,
/// since a world imports its domains by the tree's shape.
fn variant(name: &str, edits: &[(&str, &str, &str)]) -> PathBuf {
    let root = std::env::temp_dir().join(format!("orexis-{name}-{}", std::process::id()));
    let world = root.join("world/layby");
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(world.join("beliefs")).unwrap();
    for entry in fs::read_dir(repo().join("world/layby")).unwrap() {
        let path = entry.unwrap().path();
        if path.is_file() {
            fs::copy(&path, world.join(path.file_name().unwrap())).unwrap();
        }
    }
    for entry in fs::read_dir(repo().join("world/layby/beliefs")).unwrap() {
        let path = entry.unwrap().path();
        fs::copy(&path, world.join("beliefs").join(path.file_name().unwrap())).unwrap();
    }
    std::os::unix::fs::symlink(repo().join("domains"), root.join("domains")).unwrap();
    for (file, old, new) in edits {
        let path = world.join(file);
        let text = fs::read_to_string(&path).unwrap();
        assert!(text.contains(old), "{file} no longer says {old:?}");
        fs::write(&path, text.replace(old, new)).unwrap();
    }
    world
}

#[tokio::test(start_paused = true)]
async fn a_thing_the_radar_sees_is_an_obstacle_and_the_plan_goes_round_it() {
    let world = variant(
        "detour",
        &[
            (
                "world.ttl",
                "sim:initialValue 1 ; sim:jitter 0 ] ;    # van A row 1",
                "sim:initialValue 0 ; sim:jitter 0 ] ;    # van A row 0",
            ),
            (
                "world.ttl",
                ":driver_b a courier:Driver ;",
                ":tree sim:simulatedBy [ a sim:Model ; sim:x 0 ; sim:y 1 ] ; rdfs:label \"a fallen tree, which only the \
                 radar knows\" .\n:driver_b a courier:Driver ;",
            ),
            (
                "beliefs/courier_a.state.ttl",
                ":parcel_a courier:x 1 ; courier:y 1 .",
                ":parcel_a courier:x 0 ; courier:y 2 .",
            ),
            ("society.ttl", ":van_a , :van_b ,", ":van_a , :van_b , :tree ,"),
        ],
    );
    let (sent, at) = walk(&world, "detour.tsv").await;
    let _ = fs::remove_dir_all(world.parent().unwrap().parent().unwrap());
    assert_eq!(
        sent,
        drives(&[
            ("12:00:00", -1, 0),
            ("12:00:50", -1, 1),
            ("12:01:40", -1, 2),
            ("12:02:30", 0, 2),
            ("12:03:20", 1, 2),
            ("12:04:10", 1, 1),
            ("12:05:00", 2, 1),
            ("12:05:50", 3, 1),
            ("12:06:40", 4, 1),
            ("12:07:30", 5, 1),
            ("12:08:20", 6, 1)
        ]),
        "round the tree by the column the Python courier took, and on down the lane"
    );
    assert_eq!(at["parcel_a"], (6, 1), "{at:?}");
}
