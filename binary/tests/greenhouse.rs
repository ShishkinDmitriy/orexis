//! The greenhouse on the binary, held to what `world/greenhouse/tests/test_greenhouse.py` holds the Python runtime to:
//! readings arrive over MQTT, sensing writes them and the rules conclude what they are of, climate's transitions make
//! the bed's soil and air of them, the grower's desire mints a want where the bed is believed dry or cold, the plan's
//! step takes the bed and is taken by sending the device a command sized from the bed's latest reading, and the next
//! reading's transition answers it. The broker is a fake client: what is subscribed to and published is what is held.
//! The suite's history, journal, metrics and dashboard cases wait for those packages.

use std::cell::RefCell;
use std::collections::BTreeSet;
use std::path::{Path, PathBuf};
use std::rc::Rc;
use std::sync::{Arc, Mutex};

use oxsdatatypes::{DateTime, DayTimeDuration};
use serde_json::{Value as Json, json};

use orexis::Error;
use orexis::boot::TREE;
use orexis::clock::{Clock, instant, seconds};
use orexis::namespaces::Namespaces;
use orexis::ontology::BELIEF;
use orexis::runtime::{Part, Runtime, UNFINISHED};
use orexis::store::{Store, Within, iri, value};
use orexis_agent::{Seen, Wiring, assemble_seen, booted};
use orexis_mqtt::driver::{Client, Inbox, Mqtt};

const GH: &str = "http://example.org/orexis/world/greenhouse#";
const OBSERVATION: &str = "http://example.org/orexis/sensing#ObservationGraph";
const COMMITTED: &str = "http://example.org/orexis/execution#CommittedStepGraph";

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn world() -> PathBuf {
    tree().parent().unwrap().join("world/greenhouse")
}

fn noon() -> DateTime {
    instant("2026-01-01T12:00:00+00:00").unwrap()
}

fn plus(at: DateTime, s: f64) -> DateTime {
    at.checked_add_day_time_duration(seconds(s)).unwrap()
}

/// One timeline for the world and the agent: a test sets where it stands, and every read after that moves it on by a
/// second, as a running agent's clock does.
struct Ticking(Mutex<DateTime>);

impl Ticking {
    fn set(&self, at: DateTime) {
        *self.0.lock().unwrap() = at;
    }
}

impl Clock for Ticking {
    fn now(&self) -> DateTime {
        let mut at = self.0.lock().unwrap();
        *at = at.checked_add_day_time_duration(DayTimeDuration::new(1)).unwrap();
        *at
    }
}

/// What the grower subscribes to and publishes, and nothing else of MQTT.
#[derive(Clone, Default)]
struct Broker(Rc<RefCell<Asked>>);

/// The patterns subscribed to, and what was published: the topic, the document and whether it is retained.
type Asked = (Vec<String>, Vec<(String, Json, bool)>);

impl Broker {
    fn subscribed(&self) -> Vec<String> {
        self.0.borrow().0.clone()
    }

    fn published(&self) -> Vec<(String, Json, bool)> {
        self.0.borrow().1.clone()
    }

    fn topics(&self) -> Vec<String> {
        self.published().into_iter().map(|(t, _, _)| t).collect()
    }
}

impl Client for Broker {
    fn subscribe(&mut self, pattern: &str) -> Result<(), Error> {
        self.0.borrow_mut().0.push(pattern.to_string());
        Ok(())
    }

    fn publish(&mut self, topic: &str, payload: &[u8], retain: bool) -> Result<(), Error> {
        let payload = serde_json::from_slice(payload).map_err(|e| Error::Evaluation(e.to_string()))?;
        self.0.borrow_mut().1.push((topic.to_string(), payload, retain));
        Ok(())
    }
}

fn store() -> Store {
    Store::new(Arc::new(Namespaces::of_tree(tree()).unwrap())).unwrap()
}

/// The grower booted and assembled over the fake broker, its parts handed out for the runtime to lend.
struct Grower<'a> {
    parts: orexis_agent::Parts<'a>,
    seen: Seen<'a>,
    inbox: Inbox,
    broker: Broker,
}

fn grower<'a>(store: &'a Store, clock: &'a Ticking) -> Grower<'a> {
    let loaded = booted(store, tree(), &world(), "grower", noon()).unwrap();
    for package in [
        "belief",
        "planning",
        "execution",
        "sensing",
        "prediction",
        "transport/mqtt",
    ] {
        assert!(loaded.iter().any(|p| p == package), "{package}: {loaded:?}");
    }
    let broker = Broker::default();
    let member = Mqtt::new(store, &format!("{GH}grower"), vec![(None, Box::new(broker.clone()))]);
    let inbox = member.inbox.clone();
    let wiring = Wiring { mqtt: Some(member) };
    let (parts, seen) = assemble_seen(store, "grower", clock, &loaded, None, wiring).unwrap();
    Grower {
        parts,
        seen,
        inbox,
        broker,
    }
}

fn runtime<'a: 'p, 'p>(store: &'a Store, clock: &'a Ticking, parts: &'p mut orexis_agent::Parts<'a>) -> Runtime<'p> {
    let lent: Vec<(String, &mut dyn Part)> = parts
        .iter_mut()
        .map(|(p, part)| (p.clone(), part.as_mut() as &mut dyn Part))
        .collect();
    Runtime::new(store, "grower", clock, lent).unwrap()
}

fn reading(inbox: &Inbox, payload: &str, at: DateTime) {
    inbox.deliver("sensors/bed_board/reading", payload.as_bytes(), Some(at));
}

fn walking(seen: &Seen<'_>) -> Vec<String> {
    seen.executor.as_ref().unwrap().borrow().walking().unwrap()
}

/// What the grower holds of the bed — its soil and its air, in climate's words — read where the mind reads it.
fn held(store: &Store) -> BTreeSet<(String, String)> {
    let beliefs = store.graphs_of(&[BELIEF], &Within::default()).unwrap();
    let beliefs: Vec<&str> = beliefs.iter().map(String::as_str).collect();
    let q = "PREFIX climate: <http://example.org/orexis/climate#>
           SELECT ?p ?state WHERE { ?bed ?p ?state . VALUES ?p { climate:soil climate:air } }";
    store
        .rows(q, &beliefs)
        .unwrap()
        .iter()
        .map(|r| {
            let local = |v: String| v.rsplit('#').next().unwrap().to_string();
            (local(iri(r, "p").unwrap()), local(iri(r, "state").unwrap()))
        })
        .collect()
}

fn pair(a: &str, b: &str) -> (String, String) {
    (a.to_string(), b.to_string())
}

fn pump(dose: i64) -> (String, Json, bool) {
    ("actuators/pump/command".to_string(), json!({ "dose_ml": dose }), false)
}

#[test]
fn the_grower_listens_to_the_instruments_of_the_bed_it_acts_for() {
    let (store, clock) = (store(), Ticking(Mutex::new(noon())));
    let mut g = grower(&store, &clock);
    let broker = g.broker.clone();
    let _runtime = runtime(&store, &clock, &mut g.parts);
    assert_eq!(
        broker.subscribed(),
        ["sensors/bed_board/reading"],
        "the board's one topic, named for it"
    );
}

#[test]
fn a_reading_is_written_and_the_bed_believed_dry() {
    let (store, clock) = (store(), Ticking(Mutex::new(noon())));
    let mut g = grower(&store, &clock);
    let inbox = g.inbox.clone();
    let mut runtime = runtime(&store, &clock, &mut g.parts);
    reading(&inbox, r#"{"moisture": 0.2}"#, noon());
    runtime.drain(noon()).unwrap();
    assert_eq!(
        held(&store),
        BTreeSet::from([pair("soil", "Dry")]),
        "under the bed's floor of 0.30"
    );
    assert_eq!(
        store.graphs_of(&[OBSERVATION], &Within::default()).unwrap().len(),
        2,
        "the percept and what the rules concluded of it, both of sensing's kind"
    );
}

#[test]
fn a_dry_bed_is_dosed_by_a_command_sized_from_the_reading_and_the_next_reading_answers_it() {
    let (store, clock) = (store(), Ticking(Mutex::new(noon())));
    let mut g = grower(&store, &clock);
    let (inbox, broker) = (g.inbox.clone(), g.broker.clone());
    let seen = std::mem::take(&mut g.seen);
    let mut runtime = runtime(&store, &clock, &mut g.parts);
    reading(&inbox, r#"{"temperature": 21.0}"#, noon());
    reading(&inbox, r#"{"moisture": 0.2}"#, noon());
    assert_eq!(runtime.run(Some(1), 0.0).unwrap(), UNFINISHED);
    assert_eq!(broker.published(), [pump(500)]);
    assert_eq!(walking(&seen).len(), 1, "the world has not answered yet");
    let later = plus(noon(), 11.0 * 60.0);
    clock.set(later);
    reading(&inbox, r#"{"moisture": 0.45}"#, later);
    runtime.run(Some(2), 0.0).unwrap();
    assert!(
        walking(&seen).is_empty(),
        "the reading made the bed moist and answered the dose"
    );
    assert!(held(&store).contains(&pair("soil", "Moist")));
    assert_eq!(
        broker.published().len(),
        1,
        "one dose, and nothing more once the bed is comfortable"
    );
}

/// THE BED'S SOIL IN EVERY GROUND THE GROWER LAYS, and when each begins — read off the planner's imaginaria.
const FORESEEN_Q: &str = "
SELECT ?start ?state WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start }
  GRAPH ?g { <http://example.org/orexis/world/greenhouse#bed> <http://example.org/orexis/climate#soil> ?state } }
ORDER BY ?start";

fn foreseen(seen: &Seen<'_>) -> Vec<(DateTime, String)> {
    let planner = seen.planner.as_ref().unwrap().borrow();
    let mut out: Vec<(DateTime, String)> = planner
        .imaginaria
        .values()
        .flat_map(|im| im.rows(FORESEEN_Q, &[]).unwrap())
        .map(|r| {
            (
                instant(&value(&r, "start").unwrap()).unwrap(),
                iri(&r, "state").unwrap().rsplit('#').next().unwrap().to_string(),
            )
        })
        .collect();
    out.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap().then(a.1.cmp(&b.1)));
    out
}

#[test]
fn a_committed_dose_is_a_flow_the_beds_prediction_accumulates() {
    let (store, clock) = (store(), Ticking(Mutex::new(noon())));
    let mut g = grower(&store, &clock);
    let (inbox, broker) = (g.inbox.clone(), g.broker.clone());
    let seen = std::mem::take(&mut g.seen);
    let mut runtime = runtime(&store, &clock, &mut g.parts);
    reading(&inbox, r#"{"temperature": 21.0}"#, noon());
    reading(&inbox, r#"{"moisture": 0.2}"#, noon());
    runtime.run(Some(1), 0.0).unwrap();
    assert_eq!(broker.published(), [pump(500)]);
    let windows = store.graphs_of(&[COMMITTED], &Within::default()).unwrap();
    assert_eq!(windows.len(), 1);
    let period = store
        .rows(
            &format!(
                "SELECT ?s ?e WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{}> dcterms:temporal ?p . \
                 ?p orexis:start ?s ; orexis:end ?e }} }}",
                windows[0]
            ),
            &[],
        )
        .unwrap();
    let (opens, closes) = (
        instant(&value(&period[0], "s").unwrap()).unwrap(),
        instant(&value(&period[0], "e").unwrap()).unwrap(),
    );
    let window = orexis::clock::seconds_of(closes.checked_sub(opens).unwrap());
    assert!(
        (660.0..=665.0).contains(&window),
        "a cadence, and the patience: {window}"
    );
    runtime.run(Some(1), 0.0).unwrap();
    let now = clock.now();
    let ahead: Vec<(DateTime, String)> = foreseen(&seen).into_iter().filter(|(s, _)| *s > now).collect();
    assert!(
        !ahead.is_empty() && ahead[0].0 <= closes,
        "risen within the window: {ahead:?}"
    );
    assert!(
        ahead.iter().all(|(_, state)| state == "Moist"),
        "never dry again, not dried from 0.2: {ahead:?}"
    );
    let later = plus(noon(), 11.0 * 60.0);
    clock.set(later);
    reading(&inbox, r#"{"moisture": 0.45}"#, later);
    runtime.run(Some(2), 0.0).unwrap();
    assert!(walking(&seen).is_empty());
    assert!(
        store.graphs_of(&[COMMITTED], &Within::default()).unwrap().is_empty(),
        "answered: closed, then swept"
    );
}

#[test]
fn a_cold_bed_is_heated_for_as_long_as_the_gap_takes() {
    let (store, clock) = (store(), Ticking(Mutex::new(noon())));
    let mut g = grower(&store, &clock);
    let (inbox, broker) = (g.inbox.clone(), g.broker.clone());
    let mut runtime = runtime(&store, &clock, &mut g.parts);
    reading(&inbox, r#"{"moisture": 0.45}"#, noon());
    reading(&inbox, r#"{"temperature": 16.0}"#, noon());
    runtime.run(Some(1), 0.0).unwrap();
    assert_eq!(
        broker.published(),
        [("actuators/heater/command".to_string(), json!({ "heat_s": 3600 }), false)]
    );
}

#[test]
fn a_cold_dry_bed_is_two_wants_planned_apart() {
    let (store, clock) = (store(), Ticking(Mutex::new(noon())));
    let mut g = grower(&store, &clock);
    let (inbox, broker) = (g.inbox.clone(), g.broker.clone());
    let seen = std::mem::take(&mut g.seen);
    let mut runtime = runtime(&store, &clock, &mut g.parts);
    reading(&inbox, r#"{"temperature": 12.0}"#, noon());
    reading(&inbox, r#"{"moisture": 0.2}"#, noon());
    assert_eq!(runtime.run(Some(1), 0.0).unwrap(), UNFINISHED);
    let mut topics = broker.topics();
    topics.sort();
    assert_eq!(topics, ["actuators/heater/command", "actuators/pump/command"]);
    {
        let planner = seen.planner.as_ref().unwrap().borrow();
        assert_eq!(
            planner.imaginaria.len(),
            2,
            "one imaginarium per scope, and the bed's two properties are two"
        );
        let q = "SELECT ?w WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:PossibleGraph } }";
        let worlds: Vec<usize> = planner
            .imaginaria
            .values()
            .map(|im| im.rows(q, &[]).unwrap().len())
            .collect();
        assert_eq!(worlds, [1, 1], "one step each, searched apart");
    }
    assert_eq!(walking(&seen).len(), 2);
    assert_eq!(runtime.run(Some(1), 0.0).unwrap(), UNFINISHED);
    assert!(seen.planner.as_ref().unwrap().borrow().blocked.is_empty());
    assert_eq!(walking(&seen).len(), 2);
}

#[test]
fn a_foreseen_crossing_is_planned_ahead_and_dosed_when_it_arrives() {
    let (store, clock) = (store(), Ticking(Mutex::new(noon())));
    let mut g = grower(&store, &clock);
    let (inbox, broker) = (g.inbox.clone(), g.broker.clone());
    let seen = std::mem::take(&mut g.seen);
    let mut runtime = runtime(&store, &clock, &mut g.parts);
    reading(&inbox, r#"{"temperature": 21.0}"#, noon());
    reading(&inbox, r#"{"moisture": 0.31}"#, noon());
    runtime.run(Some(2), 0.0).unwrap();
    assert!(broker.published().is_empty(), "comfortable now, so nothing is sent");
    let want = walking(&seen);
    assert_eq!(want.len(), 1, "planned ahead");
    runtime.run(Some(2), 0.0).unwrap();
    assert_eq!(walking(&seen), want, "the plan placed ahead survives the passes");
    assert!(broker.published().is_empty());
    let later = plus(noon(), 7.0 * 3600.0);
    clock.set(later);
    reading(&inbox, r#"{"moisture": 0.2995}"#, later);
    runtime.run(Some(2), 0.0).unwrap();
    assert_eq!(
        broker.topics(),
        ["actuators/pump/command"],
        "the foreseen crossing came, and the dose with it"
    );
}
