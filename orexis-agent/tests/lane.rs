//! The lane on the binary: two couriers in one process on one bus that hands each what the other tells it, walked
//! CLOSED LOOP. `common/road.rs` plays the vans as the simulator does, off the world's own documents: a drive either
//! courier sends moves its van after the world's delay, and each ten-second step both are told where the vans and
//! the hedges truly stand. So a walk is held to what the world exists to prove, where the vans went and who gave way,
//! and to no recording: the walks were once replays of what the simulator had published to the two Python couriers,
//! which hold only for as long as every drive is sent at the recorded instant, and two minds that wait for no pass
//! do not keep another runtime's instants (#1149).
//!
//! EVERY WALK IS HELD TO THE ROAD'S OWN RULES, whatever else it proves: no two vans ever stand on one cell, no van
//! ever stands on a hedge, and no van is told a cell it cannot drive to.

mod common;
#[path = "common/road.rs"]
mod road;
#[path = "common/trace.rs"]
mod trace;

use std::collections::{BTreeMap, BTreeSet};
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
use orexis::task::Running;
use orexis_agent::{Wiring, booted};
use orexis_transport_mqtt::driver::{Client, Inbox, Mqtt};
use road::{Cell, Road};

const L: &str = "http://example.org/orexis/world/lane#";
const WON_Q: &str = "SELECT ?w WHERE { ?draw <http://example.org/orexis/coordination#wonBy> ?w }";
const KINDS: [&str; 4] = [
    "coordination#Question",
    "coordination#Answer",
    "draw#Commitment",
    "draw#Reveal",
];

/// What the bus carried: each drive, each document told, and the inboxes it hands a document to.
#[derive(Default)]
struct Carried {
    inboxes: BTreeMap<String, Inbox>,
    commands: Vec<String>,
    told: Vec<String>,
    /// The road the vans are on, told each drive as it is sent.
    road: Option<Road>,
    /// What the walk is traced into, where it is being looked into.
    trace: Option<trace::Trace>,
    /// What the bus loses: a document to `courier_a` saying this kind, where a walk says so.
    dropping: Option<String>,
}

/// One courier's side of the bus.
struct Bus {
    clock: Arc<dyn Clock>,
    carried: Arc<Mutex<Carried>>,
}

impl Client for Bus {
    fn subscribe(&mut self, _pattern: &str) -> Result<(), Error> {
        Ok(())
    }

    fn publish(&mut self, topic: &str, payload: &[u8], _retain: bool) -> Result<(), Error> {
        let at = isoformat(self.clock.now());
        let mut carried = self.carried.lock().unwrap();
        if topic.starts_with("agents/") {
            let text = String::from_utf8_lossy(payload);
            let kinds: Vec<&str> = KINDS.iter().copied().filter(|k| text.contains(k)).collect();
            carried.told.push(format!("{at}\t{topic}\t{}", kinds.join(",")));
            if let Some(trace) = &carried.trace {
                trace.note(&at, &format!("BUS told {topic} {}", kinds.join(",")));
            }
            let agent = topic.split('/').nth(1).unwrap_or_default().to_string();
            let lost = carried
                .dropping
                .as_ref()
                .is_some_and(|kind| agent == "courier_a" && text.contains(&format!("draw#{kind}")));
            if !lost && let Some(inbox) = carried.inboxes.get(&agent) {
                inbox.deliver(topic, payload, Some(self.clock.now()));
            }
        } else {
            let payload: Json = serde_json::from_slice(payload).map_err(|e| Error::Evaluation(e.to_string()))?;
            carried.commands.push(format!("{at}\t{topic}\t{payload}"));
            if let Some(trace) = &carried.trace {
                trace.note(&at, &format!("BUS drive {topic} {payload}"));
            }
            let now = self.clock.now();
            if let Some(road) = carried.road.as_mut() {
                road.command(now, topic, &payload);
            }
        }
        Ok(())
    }
}

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn repo() -> &'static Path {
    tree()
}

/// The lane with its documents rewritten, as `test_lane.py`'s `variant` rewrites it.
/// One rewrite of a document: the file, what it says, and what it says instead.
type Edit = (String, String, String);

fn variant(name: &str, edits: &[Edit]) -> PathBuf {
    let root = std::env::temp_dir().join(format!("orexis-lane-{name}-{}", std::process::id()));
    let world = root.join("world/lane");
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(world.join("beliefs")).unwrap();
    for dir in ["", "beliefs"] {
        for entry in fs::read_dir(repo().join("world/lane").join(dir)).unwrap() {
            let path = entry.unwrap().path();
            if path.is_file() {
                fs::copy(&path, world.join(dir).join(path.file_name().unwrap())).unwrap();
            }
        }
    }
    std::os::unix::fs::symlink(repo().join("domains"), root.join("domains")).unwrap();
    for (file, old, new) in edits {
        let path = world.join(file);
        let text = fs::read_to_string(&path).unwrap();
        assert!(text.contains(old.as_str()), "{file} no longer says {old:?}");
        fs::write(&path, text.replace(old.as_str(), new)).unwrap();
    }
    world
}

fn edit(file: &str, old: &str, new: &str) -> Edit {
    (file.to_string(), old.to_string(), new.to_string())
}

fn secret(who: &str, digit: &str) -> Edit {
    let file = format!("beliefs/courier_{who}.self.ttl");
    edit(
        &file,
        &format!(":courier_{who} planning:budget 256 ."),
        &format!(
            ":courier_{who} planning:budget 256 ; coordination:secret \"{}\" .",
            digit.repeat(64)
        ),
    )
}

fn from_the_corner() -> Vec<Edit> {
    vec![
        edit(
            "world.ttl",
            "sim:initialValue 1 ; sim:jitter 0 ] ;    # van A row 1",
            "sim:initialValue 0 ; sim:jitter 0 ] ;    # van A row 0",
        ),
        edit(
            "beliefs/courier_a.state.ttl",
            ":parcel_a courier:x 1 ; courier:y 1 .",
            ":parcel_a courier:x 0 ; courier:y 2 .",
        ),
    ]
}

fn head_on() -> Vec<Edit> {
    vec![
        edit(
            "world.ttl",
            "sim:initialValue 0 ; sim:jitter 0 ] ;    # van B row 0",
            "sim:initialValue 1 ; sim:jitter 0 ] ;    # van B row 1",
        ),
        edit(
            "beliefs/courier_b.state.ttl",
            ":parcel_b courier:x 6 ; courier:y 0 .",
            ":parcel_b courier:x 5 ; courier:y 1 .",
        ),
        edit(
            "beliefs/courier_b.state.ttl",
            ":east_road courier:x 6 ; courier:y 0 ;",
            ":east_road courier:x 0 ; courier:y 0 ;",
        ),
        secret("a", "0"),
        secret("b", "3"),
    ]
}

fn crossing(a: &str, b: &str) -> Vec<Edit> {
    vec![
        edit(
            "world.ttl",
            "sim:initialValue 6 ; sim:jitter 0 ] ;    # van B column 6",
            "sim:initialValue 5 ; sim:jitter 0 ] ;    # van B column 5",
        ),
        edit(
            "world.ttl",
            "sim:initialValue 0 ; sim:jitter 0 ] ;    # van B row 0",
            "sim:initialValue -4 ; sim:jitter 0 ] ;    # van B row -4",
        ),
        edit(
            "beliefs/courier_b.state.ttl",
            ":parcel_b courier:x 6 ; courier:y 0 .",
            ":parcel_b courier:x 5 ; courier:y -4 .",
        ),
        edit(
            "beliefs/courier_b.state.ttl",
            ":east_road courier:x 6 ; courier:y 0 ;",
            ":east_road courier:x 5 ; courier:y 4 ;",
        ),
        secret("a", a),
        secret("b", b),
    ]
}

fn peer_on_the_way() -> Vec<Edit> {
    let mut out = from_the_corner();
    out.extend([
        edit(
            "world.ttl",
            "sim:initialValue 6 ; sim:jitter 0 ] ;    # van B column 6",
            "sim:initialValue 0 ; sim:jitter 0 ] ;    # van B column 0",
        ),
        edit(
            "world.ttl",
            "sim:initialValue 0 ; sim:jitter 0 ] ;    # van B row 0",
            "sim:initialValue 1 ; sim:jitter 0 ] ;    # van B row 1",
        ),
        edit(
            "beliefs/courier_b.state.ttl",
            ":parcel_b courier:x 6 ; courier:y 0 .",
            ":parcel_b courier:x 0 ; courier:y 1 .",
        ),
        edit(
            "beliefs/courier_b.state.ttl",
            ":east_road courier:x 6 ; courier:y 0 ;",
            ":east_road courier:x 0 ; courier:y 1 ;",
        ),
    ]);
    out
}

fn passing_place() -> Vec<Edit> {
    vec![edit(
        "beliefs/courier_a.state.ttl",
        ":east_end courier:x 6 ; courier:y 1 ;",
        ":east_end courier:x 3 ; courier:y 2 ;",
    )]
}

fn won(store: &Store) -> String {
    let beliefs = store.graphs_of(&[BELIEF], &Within::default()).unwrap();
    let beliefs: Vec<&str> = beliefs.iter().map(String::as_str).collect();
    let mut found: Vec<String> = store
        .rows(WON_Q, &beliefs)
        .unwrap()
        .iter()
        .filter_map(|r| iri(r, "w"))
        .collect();
    found.sort();
    found.dedup();
    found.join(",")
}

/// What a walk left: the road with where each van stood at every step, each drive sent, who each courier concluded
/// won, where each believes its parcel is, and each one's journal where one was kept.
struct Walked {
    road: Road,
    commands: Vec<String>,
    won: BTreeMap<String, String>,
    parcels: BTreeMap<String, Cell>,
    journals: Vec<Arc<orexis::journal::Journal>>,
}

impl Walked {
    /// How many drives the van named `van` was sent.
    fn drives(&self, van: &str) -> usize {
        let topic = format!("actuators/{van}/command");
        self.commands.iter().filter(|c| c.contains(&topic)).count()
    }
}

const PARCEL_Q: &str = "PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?p ?x ?y WHERE { ?p a courier:Parcel ; courier:x ?x ; courier:y ?y }";

fn start() -> DateTime {
    instant("2026-01-01T12:00:00+00:00").unwrap()
}

/// Walk the two couriers of `world` on its road until the vans stand at `home`, the bus losing what `dropping` says,
/// and hold the walk to the road's rules. A walk not home within forty minutes of the world's time has failed.
async fn walked(name: &str, world: &Path, home: &[(&str, Cell)], dropping: Option<&str>, kept: bool) -> Walked {
    let namespaces = Arc::new(Namespaces::of_tree(tree()).unwrap());
    let stores = [Store::new(namespaces.clone()).unwrap(), Store::new(namespaces).unwrap()];
    let clock: Arc<dyn Clock> = common::clock(start());
    let carried = Arc::new(Mutex::new(Carried {
        dropping: dropping.map(str::to_string),
        ..Carried::default()
    }));
    let names = ["courier_a", "courier_b"];
    //  A WALK BEING LOOKED INTO says where to write what every agent did: `LANE_TRACE=<file>`, and `LANE_STEPS=<n>`
    //  to stop it after so many steps of the road.
    let traced = std::env::var("LANE_TRACE").ok().map(|_| trace::Trace::default());
    carried.lock().unwrap().trace = traced.clone();
    let journals: Vec<Arc<orexis::journal::Journal>> = if kept {
        names
            .iter()
            .map(|_| Arc::new(orexis::journal::Journal::new(None, 600.0, Arc::new(start)).unwrap()))
            .collect()
    } else {
        Vec::new()
    };
    let mut runtimes: Vec<Running> = Vec::new();
    for (store, name) in stores.iter().zip(names) {
        let loaded = booted(store, tree(), world, name, start()).unwrap();
        if carried.lock().unwrap().road.is_none() {
            carried.lock().unwrap().road = Some(Road::of(store));
        }
        let bus = Bus {
            clock: clock.clone(),
            carried: carried.clone(),
        };
        let member = Mqtt::new(store, &format!("{L}{name}"), vec![(None, Box::new(bus))]);
        carried
            .lock()
            .unwrap()
            .inboxes
            .insert(name.to_string(), member.inbox.clone());
        let watching = orexis_agent::Watching {
            journal: journals.get(runtimes.len()).cloned(),
            ..Default::default()
        };
        let wiring = Wiring {
            mqtt: Some(member),
            watching,
            ..Wiring::default()
        };
        let running = orexis_agent::start(store, name, clock.clone(), &loaded, None, wiring).unwrap();
        if let Some(trace) = &traced {
            trace.watch(name, &running, clock.clone());
        }
        runtimes.push(running);
    }
    let inboxes: Vec<Inbox> = names
        .iter()
        .map(|n| carried.lock().unwrap().inboxes[*n].clone())
        .collect();
    let obstacles = carried.lock().unwrap().road.as_ref().unwrap().obstacles();
    //  HOME IS HELD FOR A MINUTE before the walk is over, so a van that only passed through is not taken as arrived
    //  and what the couriers conclude of the last fix is in what is looked at.
    let mut held = 0;
    for step in 0..240 {
        let now = clock.now();
        let reading = {
            let mut carried = carried.lock().unwrap();
            let carried = &mut *carried;
            let road = carried.road.as_mut().unwrap();
            let reading = road.step(now);
            let at = &road.trail.last().unwrap().1;
            if let Some(trace) = &carried.trace {
                trace.note(&isoformat(now), &format!("ROAD {at:?}"));
            }
            let cells: BTreeSet<&Cell> = at.values().collect();
            assert_eq!(
                cells.len(),
                at.len(),
                "{name}: two vans on one cell at {}: {at:?}",
                isoformat(now)
            );
            for (van, cell) in at {
                assert!(
                    !obstacles.contains(cell),
                    "{name}: {van} on a hedge at {}: {at:?}",
                    isoformat(now)
                );
            }
            held = if !road.moving() && home.iter().all(|(van, cell)| road.at(van) == *cell) {
                held + 1
            } else {
                0
            };
            reading
        };
        for inbox in &inboxes {
            inbox.deliver("sensors/simulation/reading", reading.as_bytes(), Some(now));
        }
        common::settled_all(&runtimes).await;
        if let (Some(trace), Ok(steps)) = (&traced, std::env::var("LANE_STEPS"))
            && step + 1 == steps.parse::<usize>().unwrap()
        {
            fs::write(std::env::var("LANE_TRACE").unwrap(), trace.lines().join("\n")).unwrap();
            panic!("{name}: stopped after {steps} steps, as asked");
        }
        if held > 6 {
            break;
        }
        assert!(
            step < 239,
            "{name}: the vans are not home within forty minutes: {:?} of {home:?}",
            {
                let carried = carried.lock().unwrap();
                carried.road.as_ref().unwrap().trail.last().unwrap().1.clone()
            }
        );
        common::pass_all(&runtimes, 10.0).await;
    }
    for runtime in runtimes {
        runtime.stop().await;
    }
    if let (Some(trace), Ok(file)) = (&traced, std::env::var("LANE_TRACE")) {
        fs::write(file, trace.lines().join("\n")).unwrap();
    }
    let mut carried = carried.lock().unwrap();
    let road = carried.road.take().unwrap();
    assert!(
        road.refused.is_empty(),
        "{name}: a van was told what it cannot do: {:?}",
        road.refused
    );
    let won = names
        .iter()
        .zip(&stores)
        .map(|(n, s)| (n.to_string(), won(s)))
        .collect();
    let mut parcels = BTreeMap::new();
    for store in &stores {
        let beliefs = store.graphs_of(&[BELIEF], &Within::default()).unwrap();
        let beliefs: Vec<&str> = beliefs.iter().map(String::as_str).collect();
        for r in store.rows(PARCEL_Q, &beliefs).unwrap() {
            let whole = |v: &str| value(&r, v).unwrap().parse::<f64>().unwrap().round() as i64;
            parcels.insert(road::local(&iri(&r, "p").unwrap()), (whole("x"), whole("y")));
        }
    }
    Walked {
        road,
        commands: std::mem::take(&mut carried.commands),
        won,
        parcels,
        journals,
    }
}

const A: &str = "http://example.org/orexis/world/lane#courier_a";
const B: &str = "http://example.org/orexis/world/lane#courier_b";

/// Courier A carries its parcel a cell east to the eastern end, past courier B standing on the eastern road with
/// nothing to deliver: B's van is never told anything, and A, arrived beside it, believes it where it stands.
#[tokio::test(start_paused = true)]
async fn two_couriers_each_drive_their_own_van_and_see_the_other_within_four_cells() {
    let walk = walked(
        "lane",
        &repo().join("world/lane"),
        &[("van_a", (6, 1)), ("van_b", (6, 0))],
        None,
        false,
    )
    .await;
    assert_eq!(walk.parcels["parcel_a"], (6, 1), "the parcel is where it is owed");
    assert_eq!(
        walk.drives("van_a"),
        6,
        "six cells east, and no detour: {:?}",
        walk.commands
    );
    assert_eq!(walk.drives("van_b"), 0, "nothing drives the van that is home");
    assert!(
        walk.won.values().all(String::is_empty),
        "nothing was drawn for: {:?}",
        walk.won
    );
}

/// The two meet head on in the single-track lane, each owed where the other came from: they draw lots, both conclude
/// the same winner, and both get home without ever standing on one cell, which only one giving way allows. And each one's journal holds
/// the exchange.
#[tokio::test(start_paused = true)]
async fn two_couriers_meeting_head_on_draw_lots_and_the_loser_gives_way() {
    let home = [("van_a", (6, 1)), ("van_b", (0, 0))];
    let walk = walked("head_on", &variant("head_on", &head_on()), &home, None, true).await;
    assert_eq!(walk.won["courier_a"], B, "by the secrets, B wins: {:?}", walk.won);
    assert_eq!(walk.won["courier_b"], B, "and both conclude it: {:?}", walk.won);
    assert_eq!(walk.parcels["parcel_a"], (6, 1));
    assert_eq!(walk.parcels["parcel_b"], (0, 0));
    assert!(
        walk.drives("van_a") > 6,
        "the loser left the straight way to let the winner by: {:?}",
        walk.commands
    );
    the_meeting_is_journaled_and_both_agree_who_won(&walk.journals);
}

/// The two cross at one cell, A along the lane and B down the eastern road: whoever the secrets make the winner
/// stands on the crossing first, and the other after.
#[tokio::test(start_paused = true)]
async fn two_couriers_at_a_crossing_draw_lots_and_the_winner_goes_first() {
    let home = [("van_a", (6, 1)), ("van_b", (5, 4))];
    for (name, secrets, winner, first, second) in [
        ("crossing_a_first", ("0", "1"), A, "van_a", "van_b"),
        ("crossing_b_first", ("0", "3"), B, "van_b", "van_a"),
    ] {
        let walk = walked(
            name,
            &variant(name, &crossing(secrets.0, secrets.1)),
            &home,
            None,
            false,
        )
        .await;
        assert_eq!(walk.won["courier_a"], winner, "{name}: {:?}", walk.won);
        assert_eq!(walk.won["courier_b"], winner, "{name}: {:?}", walk.won);
        let (winners, losers) = (
            walk.road.first_on(first, (5, 1)).expect("the winner crossed"),
            walk.road.first_on(second, (5, 1)).expect("the loser crossed"),
        );
        assert!(
            winners < losers,
            "{name}: {first} on the crossing at {winners}, {second} at {losers}"
        );
    }
}

/// Courier B stands on the cell between A and its parcel with nothing to deliver: A goes round it, and B is never
/// asked to move.
#[tokio::test(start_paused = true)]
async fn a_peer_seen_standing_on_a_cell_keeps_the_plan_out_of_it() {
    let home = [("van_a", (6, 1)), ("van_b", (0, 1))];
    let walk = walked(
        "peer_on_the_way",
        &variant("peer_on_the_way", &peer_on_the_way()),
        &home,
        None,
        false,
    )
    .await;
    assert_eq!(walk.parcels["parcel_a"], (6, 1));
    assert_eq!(walk.drives("van_b"), 0, "the van in the way is home, and stays");
}

/// Courier A is owed in the passing place, between two hedges it is told nothing of: it gets there, and the walk's
/// own rule holds that no van ever stood on a hedge.
#[tokio::test(start_paused = true)]
async fn a_van_never_drives_onto_a_hedge_its_radar_has_shown() {
    let home = [("van_a", (3, 2)), ("van_b", (6, 0))];
    let walk = walked(
        "passing_place",
        &variant("passing_place", &passing_place()),
        &home,
        None,
        false,
    )
    .await;
    assert_eq!(walk.parcels["parcel_a"], (3, 2));
    assert_eq!(walk.drives("van_b"), 0);
}

/// The head-on meeting with every commitment to courier A lost on the bus, so no draw is ever concluded by both: the
/// two still get home, and never stand on one cell.
#[tokio::test(start_paused = true)]
async fn two_couriers_silent_to_each_other_both_yield_and_still_part() {
    let home = [("van_a", (6, 1)), ("van_b", (0, 0))];
    let walk = walked(
        "lost_commitment",
        &variant("lost_commitment", &head_on()),
        &home,
        Some("Commitment"),
        false,
    )
    .await;
    assert_eq!(walk.parcels["parcel_a"], (6, 1));
    assert_eq!(walk.parcels["parcel_b"], (0, 0));
}

/// As `world/lane/tests/test_history.py` holds the head-on meeting recorded: each courier's journal holds the exchange,
/// each kind of it said by one and heard by the other, and the conflict won by the same courier in both.
fn the_meeting_is_journaled_and_both_agree_who_won(journals: &[Arc<orexis::journal::Journal>]) {
    let rows = |journal: &orexis::journal::Journal, text: &str| -> String {
        String::from_utf8(orexis::journal::answer(&journal.store, text).unwrap().1).unwrap()
    };
    let won: Vec<String> = journals
        .iter()
        .map(|j| {
            rows(
                j,
                "SELECT DISTINCT ?w WHERE { ?c <http://example.org/orexis/coordination#wonBy> ?w }",
            )
        })
        .collect();
    let winner = |body: &str| -> Vec<String> {
        body.split("\"value\":\"")
            .skip(1)
            .map(|v| v.split('"').next().unwrap().to_string())
            .collect()
    };
    assert_eq!(winner(&won[0]).len(), 1, "courier A concluded one winner: {}", won[0]);
    assert_eq!(winner(&won[0]), winner(&won[1]), "both agree who won");
    let mut spoken = BTreeSet::new();
    for journal in journals {
        let body = rows(
            journal,
            "SELECT ?k ?t WHERE { ?e a ?k ; <http://example.org/orexis/speech#statement> ?g . ?g a ?t }",
        );
        let values = winner(&body);
        for pair in values.chunks(2) {
            let local = |v: &str| v.rsplit('#').next().unwrap().to_string();
            spoken.insert((local(&pair[0]), local(&pair[1])));
        }
    }
    for kind in ["Said", "Heard"] {
        for graph in ["QuestionGraph", "AnswerGraph", "CommitmentGraph", "RevealGraph"] {
            assert!(
                spoken.contains(&(kind.to_string(), graph.to_string())),
                "{kind} {graph} in {spoken:?}"
            );
        }
    }
}
