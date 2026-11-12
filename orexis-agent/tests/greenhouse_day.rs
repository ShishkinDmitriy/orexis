//! The greenhouse's day on the binary, held to the commands the Python grower sent over the same day: the readings
//! its simulator published to the Python grower in `world/greenhouse/tests/test_season_bench.py`'s `day`, replayed
//! pass by pass, a reading every ten minutes for twenty-four hours, and the commands the binary sends digested as
//! the bench digests them — each command's instant, topic and payload — which must be the digest the bench's ledger
//! records, `7e9516c5e8e233ad` (knowledge/decisions/the-agent-moves-to-rust-one-package-at-a-time.md). A replay is
//! the closed loop for as long as the commands agree, since a reading answers the command before it; where the
//! binary sent another, the digest differs and the replay says so.

mod common;

use std::fs;
use std::path::Path;
use std::sync::{Arc, Mutex};

use oxsdatatypes::DateTime;
use serde_json::{Map, Value as Json};
use sha2::{Digest, Sha256};

use orexis::Error;
use orexis::boot::TREE;
use orexis::clock::{Clock, instant, isoformat};
use orexis::namespaces::Namespaces;
use orexis::store::Store;
use orexis_agent::{Wiring, booted};
use orexis_transport_mqtt::driver::{Client, Mqtt, dumps};

const GH: &str = "http://example.org/orexis/world/greenhouse#";
const DIGEST: &str = "7e9516c5e8e233ad";

/// Every command the grower sends, with the instant it was sent.
struct Bus {
    clock: Arc<dyn Clock>,
    commands: Arc<Mutex<Vec<(String, String, Json)>>>,
}

impl Client for Bus {
    fn subscribe(&mut self, _pattern: &str) -> Result<(), Error> {
        Ok(())
    }

    fn publish(&mut self, topic: &str, payload: &[u8], _retain: bool) -> Result<(), Error> {
        let payload = serde_json::from_slice(payload).map_err(|e| Error::Evaluation(e.to_string()))?;
        self.commands
            .lock()
            .unwrap()
            .push((isoformat(self.clock.now()), topic.to_string(), payload));
        Ok(())
    }
}

/// A document with its keys sorted, as `json.dumps(…, sort_keys=True)` writes it.
fn sorted(document: &Json) -> Json {
    match document {
        Json::Object(fields) => {
            let mut keys: Vec<&String> = fields.keys().collect();
            keys.sort();
            Json::Object(
                keys.into_iter()
                    .map(|k| (k.clone(), sorted(&fields[k])))
                    .collect::<Map<_, _>>(),
            )
        }
        Json::Array(items) => Json::Array(items.iter().map(sorted).collect()),
        other => other.clone(),
    }
}

/// The commands of the day, each its instant, topic and payload with sorted keys, hashed as the bench hashes them.
fn digest(commands: &[(String, String, Json)]) -> String {
    let text: Vec<String> = commands
        .iter()
        .map(|(at, topic, payload)| {
            dumps(&Json::Array(vec![
                at.clone().into(),
                topic.clone().into(),
                sorted(payload),
            ]))
        })
        .collect();
    let hash = Sha256::digest(text.join("\n").as_bytes());
    hash.iter().map(|b| format!("{b:02x}")).collect::<String>()[..16].to_string()
}

#[tokio::test(start_paused = true)]
async fn a_day_in_the_greenhouse_sends_the_commands_it_is_pinned_to() {
    let tree = Path::new(TREE);
    let world = tree.join("world/greenhouse");
    let day =
        fs::read_to_string(Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/greenhouse_day.tsv")).unwrap();
    let readings: Vec<(DateTime, String, String)> = day
        .lines()
        .filter(|l| !l.starts_with('#') && !l.trim().is_empty())
        .map(|l| {
            let mut fields = l.splitn(3, '\t');
            let at = instant(fields.next().unwrap()).unwrap();
            (
                at,
                fields.next().unwrap().to_string(),
                fields.next().unwrap_or_default().to_string(),
            )
        })
        .collect();
    assert_eq!(readings.len(), 144, "a reading every ten minutes for a day");
    let store = Store::new(Arc::new(Namespaces::of_tree(tree).unwrap())).unwrap();
    let clock: Arc<dyn Clock> = common::clock(readings[0].0);
    let loaded = booted(&store, tree, &world, "grower", readings[0].0).unwrap();
    let commands = Arc::new(Mutex::new(Vec::new()));
    let bus = Bus {
        clock: clock.clone(),
        commands: commands.clone(),
    };
    let member = Mqtt::new(&store, &format!("{GH}grower"), vec![(None, Box::new(bus))]);
    let inbox = member.inbox.clone();
    let wiring = Wiring {
        mqtt: Some(member),
        ..Wiring::default()
    };
    let running = orexis_agent::start(&store, "grower", clock.clone(), &loaded, None, wiring).unwrap();
    for (at, topic, payload) in &readings {
        //  THE DAY RUNS TO EACH READING'S INSTANT, the grower doing what falls due on the way, and the reading arrives.
        let ahead = orexis::clock::seconds_of(at.checked_sub(clock.now()).unwrap());
        common::pass(&running, ahead.max(0.0)).await;
        if !topic.is_empty() {
            inbox.deliver(topic, payload.as_bytes(), Some(*at));
        }
        common::settled(&running).await;
    }
    running.stop().await;
    if std::env::var("OREXIS_SHOW").is_ok() {
        for (at, topic, payload) in commands.lock().unwrap().iter() {
            eprintln!("SENT {at} {topic} {payload}");
        }
    }
    let sent = commands.lock().unwrap().clone();
    assert!(
        sent.iter().any(|(_, topic, _)| topic == "actuators/pump/command"),
        "the bed was dosed in a day"
    );
    assert_eq!(
        digest(&sent),
        DIGEST,
        "the day's commands, against the Python grower's: {sent:?}"
    );
}
