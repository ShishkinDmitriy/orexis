//! The sensing world on the binary, held to what `world/sensing/tests/test_sensing.py` holds the Python runtime to:
//! the governed board's one message is three observations, the agent watches and keeps running, and once the readings
//! lapse the board is told to sense on its own command topic, not retained.

mod common;

use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use orexis::Error;
use orexis::boot::TREE;
use orexis::clock::instant;
use orexis::store::{Store, Within, iri, value};
use orexis::task::{Provided, UNFINISHED};
use orexis_agent::boot_without_starting;
use orexis_transport_mqtt::driver::{Client, Mqtt};

const W: &str = "http://example.org/orexis/world/sensing#";
const OBSERVATION: &str = "http://example.org/orexis/sensing#ObservationGraph";
const MESSAGE: &str = r#"{"moisture": 0.41, "temperature": 21.5, "humidity": 0.55}"#;

/// The patterns subscribed to, and what was published: the topic, the document and whether it is retained.
type Asked = (Vec<String>, Vec<(String, String, bool)>);

#[derive(Clone, Default)]
struct Broker(Arc<Mutex<Asked>>);

impl Client for Broker {
    fn subscribe(&mut self, pattern: &str) -> Result<(), Error> {
        self.0.lock().unwrap().0.push(pattern.to_string());
        Ok(())
    }

    fn publish(&mut self, topic: &str, payload: &[u8], retain: bool) -> Result<(), Error> {
        self.0
            .lock()
            .unwrap()
            .1
            .push((topic.to_string(), String::from_utf8_lossy(payload).into_owned(), retain));
        Ok(())
    }
}

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn world() -> PathBuf {
    tree().join("world/sensing")
}

fn store() -> Store {
    Store::new().unwrap()
}

#[test]
fn booted_from_its_directory_the_agent_holds_no_hardware() {
    let store = store();
    boot_without_starting(&store, &world(), "fern").unwrap();
    let hardware = orexis::document::file_uri(&world().join("hardware.ttl")).unwrap();
    let held = store
        .rows(
            &format!("SELECT ?s WHERE {{ GRAPH <{hardware}> {{ ?s ?p ?o }} }} LIMIT 1"),
            &[],
        )
        .unwrap();
    let rowed = store
        .rows(
            &format!("SELECT ?p WHERE {{ GRAPH ?g {{ <{hardware}> ?p ?o }} }} LIMIT 1"),
            &[],
        )
        .unwrap();
    assert!(
        held.is_empty() && rowed.is_empty(),
        "the hardware is onboarding's kind and not the agent's"
    );
}

#[tokio::test(start_paused = true)]
async fn one_message_is_three_observations_the_agent_watches_and_the_board_is_told_to_sense_when_they_lapse() {
    let store = store();
    let now = instant("2026-01-01T12:00:00+00:00").unwrap();
    let broker = Broker::default();
    let member = Mqtt::new(
        &store,
        &format!("{W}fern_agent"),
        vec![(None, Box::new(broker.clone()))],
    );
    let inbox = member.inbox.clone();
    let journal = common::journal(move || now);
    let booted = orexis_agent::boot(
        &store,
        &world(),
        "fern",
        common::clock(now),
        Provided::default().with(member).with(orexis_journal::Keeps {
            journal: Some(journal.clone()),
        }),
    )
    .unwrap();
    let running = booted.start().await.unwrap();
    assert_eq!(broker.0.lock().unwrap().0, ["sensors/moisture_sensor_fern/reading"]);
    //  WHAT IS SAID OF THE MESSAGE: its three percepts perceived together and revised together, once each.
    let said: Arc<Mutex<Vec<(String, usize)>>> = Arc::default();
    let heard = said.clone();
    running.handed.events.watch().connect(move |event, _| {
        let kind = event.kind().unwrap_or_default();
        if kind.ends_with("#Perceived") || kind.ends_with("#Revised") {
            let sources = event
                .about()
                .iter()
                .filter(|(p, _)| p.ends_with("#revises") || p.ends_with("#revised"))
                .count();
            heard
                .lock()
                .unwrap()
                .push((kind.rsplit('#').next().unwrap().to_string(), sources));
        }
    });
    inbox.deliver("sensors/moisture_sensor_fern/reading", MESSAGE.as_bytes(), Some(now));
    assert_eq!(common::outcome(&running, 1).await, UNFINISHED);
    assert!(broker.0.lock().unwrap().1.is_empty(), "nothing due yet");
    //  THE READINGS LAPSE, AND THE BOARD IS TOLD TO SENSE: sensing says they are due, and the operator tells the board
    //  on its own command topic, not retained.
    common::pass(&running, 30.0).await;
    running.stop().await;
    common::traced_whole(&journal, "fern_agent");
    let published = broker.0.lock().unwrap().1.clone();
    assert!(!published.is_empty(), "the board was told");
    assert!(
        published.iter().all(|p| *p
            == (
                "sensors/moisture_sensor_fern/command".to_string(),
                r#"{"sense": true}"#.to_string(),
                false
            )),
        "{published:?}"
    );
    assert_eq!(
        *said.lock().unwrap(),
        [("Perceived".to_string(), 3), ("Revised".to_string(), 3)],
        "one message is one perceiving and one revision, each of its three percepts"
    );
    let observed = store.graphs_of(&[OBSERVATION], &Within::default()).unwrap();
    let observed: Vec<&str> = observed.iter().map(String::as_str).collect();
    let read: std::collections::BTreeMap<String, f64> = store
        .rows(
            "PREFIX sosa: <http://www.w3.org/ns/sosa/>
                SELECT ?p ?v WHERE { ?o sosa:observedProperty ?p ; sosa:hasSimpleResult ?v }",
            &observed,
        )
        .unwrap()
        .iter()
        .map(|r| {
            (
                iri(r, "p").unwrap().rsplit('#').next().unwrap().to_string(),
                value(r, "v").unwrap().parse().unwrap(),
            )
        })
        .collect();
    assert_eq!(
        read,
        [("AirHumidity", 0.55), ("AirTemperature", 21.5), ("SoilMoisture", 0.41)]
            .iter()
            .map(|(k, v)| (k.to_string(), *v))
            .collect()
    );
}
