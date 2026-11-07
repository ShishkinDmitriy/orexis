//! The sensing world on the binary, held to what `world/sensing/tests/test_sensing.py` holds the Python runtime to:
//! the governed board's one message is three observations, the agent watches and keeps running, and a cadence it would
//! set goes to the board's own command topic, retained.

use std::cell::RefCell;
use std::path::{Path, PathBuf};
use std::rc::Rc;
use std::sync::Arc;

use orexis::Error;
use orexis::boot::TREE;
use orexis::clock::{Manual, instant};
use orexis::namespaces::Namespaces;
use orexis::runtime::{Part, Runtime, UNFINISHED};
use orexis::store::{Store, Within, iri, value};
use orexis_agent::{Wiring, assemble_seen, booted};
use orexis_mqtt::driver::{Client, Mqtt};

const W: &str = "http://example.org/orexis/world/sensing#";
const OBSERVATION: &str = "http://example.org/orexis/sensing#ObservationGraph";
const MESSAGE: &str = r#"{"moisture": 0.41, "temperature": 21.5, "humidity": 0.55}"#;

/// The patterns subscribed to, and what was published: the topic, the document and whether it is retained.
type Asked = (Vec<String>, Vec<(String, String, bool)>);

#[derive(Clone, Default)]
struct Broker(Rc<RefCell<Asked>>);

impl Client for Broker {
    fn subscribe(&mut self, pattern: &str) -> Result<(), Error> {
        self.0.borrow_mut().0.push(pattern.to_string());
        Ok(())
    }

    fn publish(&mut self, topic: &str, payload: &[u8], retain: bool) -> Result<(), Error> {
        self.0
            .borrow_mut()
            .1
            .push((topic.to_string(), String::from_utf8_lossy(payload).into_owned(), retain));
        Ok(())
    }
}

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn world() -> PathBuf {
    tree().parent().unwrap().join("world/sensing")
}

fn store() -> Store {
    Store::new(Arc::new(Namespaces::of_tree(tree()).unwrap())).unwrap()
}

#[test]
fn booted_from_its_directory_the_agent_holds_no_hardware() {
    let store = store();
    booted(
        &store,
        tree(),
        &world(),
        "fern",
        instant("2026-01-01T12:00:00+00:00").unwrap(),
    )
    .unwrap();
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

#[test]
fn one_message_is_three_observations_the_agent_watches_and_a_cadence_goes_to_the_boards_command_topic() {
    let store = store();
    let now = instant("2026-01-01T12:00:00+00:00").unwrap();
    let loaded = booted(&store, tree(), &world(), "fern", now).unwrap();
    let broker = Broker::default();
    let member = Mqtt::new(
        &store,
        &format!("{W}fern_agent"),
        vec![(None, Box::new(broker.clone()))],
    );
    let inbox = member.inbox.clone();
    let clock = Manual::at(now);
    let wiring = Wiring {
        mqtt: Some(member),
        ..Wiring::default()
    };
    let (mut parts, _) = assemble_seen(&store, "fern", &clock, &loaded, None, wiring).unwrap();
    {
        let lent: Vec<(String, &mut dyn Part)> = parts
            .iter_mut()
            .map(|(p, part)| (p.clone(), part.as_mut() as &mut dyn Part))
            .collect();
        let mut runtime = Runtime::new(&store, "fern", &clock, lent).unwrap();
        assert_eq!(broker.0.borrow().0, ["sensors/moisture_sensor_fern/reading"]);
        inbox.deliver("sensors/moisture_sensor_fern/reading", MESSAGE.as_bytes(), Some(now));
        assert_eq!(runtime.run(Some(2), 0.0).unwrap(), UNFINISHED);
        runtime.stop();
    }
    let observed = store.graphs_of(&[OBSERVATION], &Within::default()).unwrap();
    let observed: Vec<&str> = observed.iter().map(String::as_str).collect();
    let read: std::collections::BTreeMap<String, f64> = store
        .rows(
            "SELECT ?p ?v WHERE { ?o sosa:observedProperty ?p ; sosa:hasSimpleResult ?v }",
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
    assert!(broker.0.borrow().1.is_empty());
    let store2 = self::store();
    booted(&store2, tree(), &world(), "fern", now).unwrap();
    let cadence = Broker::default();
    let mut member = Mqtt::new(
        &store2,
        &format!("{W}fern_agent"),
        vec![(None, Box::new(cadence.clone()))],
    );
    assert!(member.set_cadence(&format!("{W}moisture_sensor_fern"), 10).unwrap());
    assert_eq!(
        cadence.0.borrow().1,
        [(
            "sensors/moisture_sensor_fern/command".to_string(),
            r#"{"sleep_s": 10}"#.to_string(),
            true
        )],
        "the governed board keeps the interval it was last told, retained on the broker"
    );
}
