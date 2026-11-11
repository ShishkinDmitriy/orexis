//! The lane on the binary, held to what its two Python couriers did: `world/lane/tests/test_lane.py`'s walks — the
//! two couriers seeing each other down the lane, meeting head on and drawing lots, at a crossing with either winning,
//! one standing in the other's way, a passing place between hedges, and every commitment of one lost on the way —
//! replayed from what the Python simulator published to them at each ten-second step. The two Rust couriers run in one
//! process on one bus that hands each what the other tells it, and are held to the same drives at the same instants,
//! the same documents told each other at the same instants, and the same winners concluded. A replay is the closed
//! loop for as long as the drives agree, since the fixes answer the drives before them.

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
use orexis::runtime::Runtime;
use orexis::store::{Store, Within, iri};
use orexis_agent::{Wiring, booted};
use orexis_transport_mqtt::driver::{Client, Inbox, Mqtt};

const L: &str = "http://example.org/orexis/world/lane#";
const WON_Q: &str = "SELECT ?w WHERE { ?draw <http://example.org/orexis/coordination#wonBy> ?w }";
const KINDS: [&str; 4] = [
    "coordination#Question",
    "coordination#Answer",
    "draw#Commitment",
    "draw#Reveal",
];

#[derive(Clone)]
struct Standing(Arc<Mutex<DateTime>>);

impl Clock for Standing {
    fn now(&self) -> DateTime {
        *self.0.lock().unwrap()
    }
}

/// What the bus carried: each drive, each document told, and the inboxes it hands a document to.
#[derive(Default)]
struct Carried {
    inboxes: BTreeMap<String, Inbox>,
    commands: Vec<String>,
    told: Vec<String>,
    /// What the bus loses: a document to `courier_a` saying this kind, where a walk says so.
    dropping: Option<String>,
}

/// One courier's side of the bus.
struct Bus {
    clock: Standing,
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
        }
        Ok(())
    }
}

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn repo() -> &'static Path {
    tree().parent().unwrap()
}

/// A recorded walk: its steps, and what the Python couriers did over it.
struct Walk {
    steps: Vec<(DateTime, Vec<(String, String)>)>,
    commands: Vec<String>,
    told: Vec<String>,
    won: BTreeMap<String, String>,
}

fn walk_of(name: &str) -> Walk {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/lane")
        .join(format!("{name}.tsv"));
    let text = fs::read_to_string(path).unwrap();
    let mut walk = Walk {
        steps: Vec::new(),
        commands: Vec::new(),
        told: Vec::new(),
        won: BTreeMap::new(),
    };
    for line in text.lines().filter(|l| !l.starts_with('#') && !l.trim().is_empty()) {
        let (kind, rest) = line.split_once('\t').unwrap();
        match kind {
            "step" => {
                let mut fields = rest.splitn(3, '\t');
                let at = instant(fields.next().unwrap()).unwrap();
                let (topic, payload) = (fields.next().unwrap_or_default(), fields.next().unwrap_or_default());
                if walk.steps.last().is_none_or(|(t, _)| *t != at) {
                    walk.steps.push((at, Vec::new()));
                }
                if !topic.is_empty() {
                    walk.steps
                        .last_mut()
                        .unwrap()
                        .1
                        .push((topic.to_string(), payload.to_string()));
                }
            }
            "command" => walk.commands.push(rest.to_string()),
            "told" => walk.told.push(rest.to_string()),
            "won" => {
                let (agent, winners) = rest.split_once('\t').unwrap_or((rest, ""));
                walk.won.insert(agent.to_string(), winners.to_string());
            }
            other => panic!("{other}: no such line"),
        }
    }
    walk
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

/// Walk the two couriers of `world` through `name`'s recorded steps, and hold them to what the Python couriers did.
fn replayed(name: &str, world: &Path, dropping: Option<&str>) {
    replayed_keeping(name, world, dropping, false);
}

/// `replayed`, each courier keeping a journal where `kept` says so: the journals, courier A's first.
fn replayed_keeping(
    name: &str,
    world: &Path,
    dropping: Option<&str>,
    kept: bool,
) -> Vec<Arc<orexis::journal::Journal>> {
    let walk = walk_of(name);
    let namespaces = Arc::new(Namespaces::of_tree(tree()).unwrap());
    let stores = [Store::new(namespaces.clone()).unwrap(), Store::new(namespaces).unwrap()];
    let clock = Standing(Arc::new(Mutex::new(walk.steps[0].0)));
    let carried = Arc::new(Mutex::new(Carried {
        dropping: dropping.map(str::to_string),
        ..Carried::default()
    }));
    let names = ["courier_a", "courier_b"];
    let journals: Vec<Arc<orexis::journal::Journal>> = if kept {
        let at = walk.steps[0].0;
        names
            .iter()
            .map(|_| Arc::new(orexis::journal::Journal::new(None, 600.0, Arc::new(move || at)).unwrap()))
            .collect()
    } else {
        Vec::new()
    };
    let mut watches = Vec::new();
    let mut all_parts = Vec::new();
    for (store, name) in stores.iter().zip(names) {
        let loaded = booted(store, tree(), world, name, clock.now()).unwrap();
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
            journal: journals.get(watches.len()).cloned(),
            ..Default::default()
        };
        let (parts, seen) = orexis_agent::assemble_seen(
            store,
            name,
            Arc::new(clock.clone()),
            &loaded,
            None,
            Wiring {
                mqtt: Some(member),
                watching,
                ..Wiring::default()
            },
        )
        .unwrap();
        watches.push(seen.watch.clone());
        all_parts.push(parts);
    }
    let inboxes: Vec<Inbox> = names
        .iter()
        .map(|n| carried.lock().unwrap().inboxes[*n].clone())
        .collect();
    let mut runtimes: Vec<Runtime> = Vec::new();
    for ((parts, store), name) in all_parts.iter_mut().zip(&stores).zip(names) {
        let mut runtime = Runtime::new(store, name, Arc::new(clock.clone()), std::mem::take(parts)).unwrap();
        runtime.watch = watches[runtimes.len()].clone();
        runtimes.push(runtime);
    }
    for (when, published) in &walk.steps {
        *clock.0.lock().unwrap() = *when;
        for (topic, payload) in published {
            for inbox in &inboxes {
                inbox.deliver(topic, payload.as_bytes(), Some(*when));
            }
        }
        for runtime in &mut runtimes {
            runtime.run(Some(1), 0.0).unwrap();
        }
    }
    for runtime in &mut runtimes {
        runtime.stop();
    }
    let carried = carried.lock().unwrap();
    assert_eq!(
        carried.commands, walk.commands,
        "{name}: the drives, against the Python couriers'"
    );
    assert_eq!(
        carried.told, walk.told,
        "{name}: the documents told, against the Python couriers'"
    );
    let concluded: BTreeMap<String, String> = names
        .iter()
        .zip(&stores)
        .map(|(n, s)| (n.to_string(), won(s)))
        .collect();
    assert_eq!(concluded, walk.won, "{name}: who each concluded won");
    journals
}

#[test]
fn two_couriers_each_drive_their_own_van_and_see_the_other_within_four_cells() {
    replayed("lane", &repo().join("world/lane"), None);
}

#[test]
fn two_couriers_meeting_head_on_draw_lots_and_the_loser_gives_way() {
    replayed("head_on", &variant("head_on", &head_on()), None);
}

#[test]
fn two_couriers_at_a_crossing_draw_lots_and_the_winner_goes_first() {
    replayed(
        "crossing_a_first",
        &variant("crossing_a_first", &crossing("0", "1")),
        None,
    );
    replayed(
        "crossing_b_first",
        &variant("crossing_b_first", &crossing("0", "3")),
        None,
    );
}

#[test]
fn a_peer_seen_standing_on_a_cell_keeps_the_plan_out_of_it() {
    replayed("peer_on_the_way", &variant("peer_on_the_way", &peer_on_the_way()), None);
}

#[test]
fn a_van_never_drives_onto_a_hedge_its_radar_has_shown() {
    replayed("passing_place", &variant("passing_place", &passing_place()), None);
}

#[test]
fn two_couriers_silent_to_each_other_both_yield_and_still_part() {
    replayed(
        "lost_commitment",
        &variant("lost_commitment", &head_on()),
        Some("Commitment"),
    );
}

/// As `world/lane/tests/test_history.py` holds the head-on meeting recorded: each courier's journal holds the exchange,
/// each kind of it said by one and heard by the other, and the conflict won by the same courier in both.
#[test]
fn the_head_on_meeting_is_journaled_and_both_couriers_agree_who_won() {
    let journals = replayed_keeping("head_on", &variant("head_on_kept", &head_on()), None, true);
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
    for journal in &journals {
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
