//! The greenhouse on the binary, held to what `world/greenhouse/tests/test_greenhouse.py` holds the Python runtime to:
//! readings arrive over MQTT, sensing writes them and the rules conclude what they are of, climate's transitions make
//! the bed's soil and air of them, the grower's desire mints a want where the bed is believed dry or cold, the plan's
//! step takes the bed and is taken by sending the device a command sized from the bed's latest reading, and the next
//! reading's transition answers it. The broker is a fake client: what is subscribed to and published is what is held.
//! And its history and journal: every reading a point in the series, and the dose published, taken and landed.

mod common;

use std::collections::BTreeSet;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use oxsdatatypes::DateTime;
use serde_json::{Value as Json, json};

use orexis::Error;
use orexis::boot::TREE;
use orexis::clock::Elapsing;
use orexis::clock::{Clock, instant, seconds};
use orexis::namespaces::Namespaces;
use orexis::ontology::BELIEF;
use orexis::store::{Store, Within, iri, value};
use orexis::task::Running;
use orexis_agent::{Wiring, booted};
use orexis_transport_mqtt::driver::{Client, Inbox, Mqtt};

const GH: &str = "http://example.org/orexis/world/greenhouse#";
const OBSERVATION: &str = "http://example.org/orexis/sensing#ObservationGraph";
const COMMITTED: &str = "http://example.org/orexis/execution#CommittedStepGraph";

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn world() -> PathBuf {
    tree().join("world/greenhouse")
}

fn noon() -> DateTime {
    instant("2026-01-01T12:00:00+00:00").unwrap()
}

fn plus(at: DateTime, s: f64) -> DateTime {
    at.checked_add_day_time_duration(seconds(s)).unwrap()
}

/// What the grower subscribes to and publishes, and nothing else of MQTT.
#[derive(Clone, Default)]
struct Broker(Arc<Mutex<Asked>>);

/// The patterns subscribed to, and what was published: the topic, the document and whether it is retained.
type Asked = (Vec<String>, Vec<(String, Json, bool)>);

impl Broker {
    fn subscribed(&self) -> Vec<String> {
        self.0.lock().unwrap().0.clone()
    }

    fn published(&self) -> Vec<(String, Json, bool)> {
        self.0.lock().unwrap().1.clone()
    }

    fn topics(&self) -> Vec<String> {
        self.published().into_iter().map(|(t, _, _)| t).collect()
    }
}

impl Client for Broker {
    fn subscribe(&mut self, pattern: &str) -> Result<(), Error> {
        self.0.lock().unwrap().0.push(pattern.to_string());
        Ok(())
    }

    fn publish(&mut self, topic: &str, payload: &[u8], retain: bool) -> Result<(), Error> {
        let payload = serde_json::from_slice(payload).map_err(|e| Error::Evaluation(e.to_string()))?;
        self.0.lock().unwrap().1.push((topic.to_string(), payload, retain));
        Ok(())
    }
}

fn store() -> Store {
    Store::new(Arc::new(Namespaces::of_tree(tree()).unwrap())).unwrap()
}

/// The grower booted and started over the fake broker, on a clock from noon.
struct Grower {
    running: Running,
    clock: Arc<Elapsing>,
    inbox: Inbox,
    broker: Broker,
}

fn grower(store: &Store) -> Grower {
    grower_watched(store, orexis_agent::Watching::default())
}

fn grower_watched(store: &Store, watching: orexis_agent::Watching) -> Grower {
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
    let wiring = Wiring {
        mqtt: Some(member),
        watching,
        ..Wiring::default()
    };
    let clock = common::clock(noon());
    let running = orexis_agent::start(store, "grower", clock.clone(), &loaded, None, wiring).unwrap();
    Grower {
        running,
        clock,
        inbox,
        broker,
    }
}

/// Let the grower's time run to `at`, the agent doing whatever falls due on the way.
async fn until(g: &Grower, at: DateTime) {
    let ahead = orexis::clock::seconds_of(at.checked_sub(g.clock.now()).unwrap());
    common::pass(&g.running, ahead.max(0.0)).await;
}

/// What the grower told a device to do: the commands, and none of what it asks its sensors.
fn commands(broker: &Broker) -> Vec<(String, Json, bool)> {
    broker
        .published()
        .into_iter()
        .filter(|(topic, _, _)| topic.starts_with("actuators/"))
        .collect()
}

fn reading(inbox: &Inbox, payload: &str, at: DateTime) {
    inbox.deliver("sensors/bed_board/reading", payload.as_bytes(), Some(at));
}

/// The wants the grower is walking, read off its intentions by an executor of the test's own.
fn walking(store: &Store) -> Vec<String> {
    let clock = Arc::new(orexis::clock::Manual::at(noon()));
    let executor = orexis_execution::Executor::new(store, "grower", None, None, clock).unwrap();
    executor.walking().unwrap()
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

#[tokio::test(start_paused = true)]
async fn the_grower_listens_to_the_instruments_of_the_bed_it_acts_for() {
    let store = store();
    let g = grower(&store);
    let broker = g.broker.clone();
    assert_eq!(
        broker.subscribed(),
        ["sensors/bed_board/reading"],
        "the board's one topic, named for it"
    );
}

#[tokio::test(start_paused = true)]
async fn a_reading_is_written_and_the_bed_believed_dry() {
    let store = store();
    let g = grower(&store);
    let inbox = g.inbox.clone();
    reading(&inbox, r#"{"moisture": 0.2}"#, noon());
    common::settled(&g.running).await;
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

#[tokio::test(start_paused = true)]
async fn a_dry_bed_is_dosed_by_a_command_sized_from_the_reading_and_the_next_reading_answers_it() {
    let store = store();
    let g = grower(&store);
    let (inbox, broker) = (g.inbox.clone(), g.broker.clone());
    reading(&inbox, r#"{"temperature": 21.0}"#, noon());
    reading(&inbox, r#"{"moisture": 0.2}"#, noon());
    common::settled(&g.running).await;
    assert_eq!(broker.published(), [pump(500)]);
    assert_eq!(walking(&store).len(), 1, "the world has not answered yet");
    let later = plus(noon(), 10.5 * 60.0);
    until(&g, later).await;
    reading(&inbox, r#"{"moisture": 0.45}"#, later);
    common::settled(&g.running).await;
    assert!(
        walking(&store).is_empty(),
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

/// The grounds a planner lays over the grower's beliefs at `now`: one of the test's own, with prediction's
/// foresight, since the grower's is its task's alone.
fn foreseen(store: &Store, now: DateTime) -> Vec<(DateTime, String)> {
    let mut planner = orexis_planning::Planner::new(store, "grower", None).unwrap();
    planner.foresee = Some(orexis_prediction::create::Prediction.offered());
    planner.plan(now).unwrap();
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

#[tokio::test(start_paused = true)]
async fn a_committed_dose_is_a_flow_the_beds_prediction_accumulates() {
    let store = store();
    let g = grower(&store);
    let (inbox, broker) = (g.inbox.clone(), g.broker.clone());
    reading(&inbox, r#"{"temperature": 21.0}"#, noon());
    reading(&inbox, r#"{"moisture": 0.2}"#, noon());
    common::settled(&g.running).await;
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
    common::settled(&g.running).await;
    let now = g.clock.now();
    let ahead: Vec<(DateTime, String)> = foreseen(&store, now).into_iter().filter(|(s, _)| *s > now).collect();
    assert!(
        !ahead.is_empty() && ahead[0].0 <= closes,
        "risen within the window: {ahead:?}"
    );
    assert!(
        ahead.iter().all(|(_, state)| state == "Moist"),
        "never dry again, not dried from 0.2: {ahead:?}"
    );
    let later = plus(noon(), 10.5 * 60.0);
    until(&g, later).await;
    reading(&inbox, r#"{"moisture": 0.45}"#, later);
    common::settled(&g.running).await;
    assert!(walking(&store).is_empty());
    assert!(
        store.graphs_of(&[COMMITTED], &Within::default()).unwrap().is_empty(),
        "answered: closed, then swept"
    );
}

#[tokio::test(start_paused = true)]
async fn a_cold_bed_is_heated_for_as_long_as_the_gap_takes() {
    let store = store();
    let g = grower(&store);
    let (inbox, broker) = (g.inbox.clone(), g.broker.clone());
    reading(&inbox, r#"{"moisture": 0.45}"#, noon());
    reading(&inbox, r#"{"temperature": 16.0}"#, noon());
    common::settled(&g.running).await;
    assert_eq!(
        broker.published(),
        [("actuators/heater/command".to_string(), json!({ "heat_s": 3600 }), false)]
    );
}

#[tokio::test(start_paused = true)]
async fn a_cold_dry_bed_is_two_wants_planned_apart() {
    let store = store();
    let g = grower(&store);
    let (inbox, broker) = (g.inbox.clone(), g.broker.clone());
    //  THE SCOPES A SEARCH IMAGINED IN, and the heads blocked as they were taken: what planning says of itself.
    let imagined: Arc<Mutex<Vec<String>>> = Arc::default();
    let blocked = Arc::new(Mutex::new(0));
    let (scopes, refused) = (imagined.clone(), blocked.clone());
    g.running.handed.events.watch().connect(move |event, _| {
        if event.metric() == Some("imaginarium") {
            for (name, mark) in event.marks() {
                if let ("scope", orexis::events::Mark::Tag(Some(scope))) = (name, mark) {
                    let mut scopes = scopes.lock().unwrap();
                    if !scopes.contains(&scope) {
                        scopes.push(scope);
                    }
                }
            }
        }
        if event.kind() == Some("http://example.org/orexis/planning#HeadChecked")
            && event
                .about()
                .iter()
                .any(|(p, t)| p.ends_with("#blocked") && t.to_string().starts_with("\"true\""))
        {
            *refused.lock().unwrap() += 1;
        }
    });
    reading(&inbox, r#"{"temperature": 12.0}"#, noon());
    reading(&inbox, r#"{"moisture": 0.2}"#, noon());
    common::settled(&g.running).await;
    let mut topics = broker.topics();
    topics.sort();
    assert_eq!(topics, ["actuators/heater/command", "actuators/pump/command"]);
    let worlds: Vec<String> = imagined.lock().unwrap().clone();
    assert_eq!(
        worlds.len(),
        2,
        "one imaginarium per scope, and the bed's two properties are two: {worlds:?}"
    );
    assert_eq!(walking(&store).len(), 2);
    common::settled(&g.running).await;
    assert_eq!(*blocked.lock().unwrap(), 0, "no head was blocked");
    assert_eq!(walking(&store).len(), 2);
}

#[tokio::test(start_paused = true)]
async fn a_foreseen_crossing_is_planned_ahead_and_dosed_when_it_arrives() {
    let store = store();
    let g = grower(&store);
    let (inbox, broker) = (g.inbox.clone(), g.broker.clone());
    reading(&inbox, r#"{"temperature": 21.0}"#, noon());
    reading(&inbox, r#"{"moisture": 0.31}"#, noon());
    common::settled(&g.running).await;
    assert!(broker.published().is_empty(), "comfortable now, so nothing is sent");
    let want = walking(&store);
    assert_eq!(want.len(), 1, "planned ahead");
    common::settled(&g.running).await;
    assert_eq!(walking(&store), want, "the plan placed ahead survives the passes");
    assert!(broker.published().is_empty());
    let later = plus(noon(), 7.0 * 3600.0);
    until(&g, later).await;
    reading(&inbox, r#"{"moisture": 0.2995}"#, later);
    common::settled(&g.running).await;
    assert_eq!(
        broker.topics(),
        ["actuators/pump/command"],
        "the foreseen crossing came, and the dose with it"
    );
}

/// WHAT THE JOURNAL HOLDS OF THE DOSE: the plan published and each step's taking and verdict, the action each step
/// fills and the values it takes in the domain's words, each at its instant.
const DOSE_Q: &str = "
PREFIX planning: <http://example.org/orexis/planning#> PREFIX execution: <http://example.org/orexis/execution#>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?kind ?at ?action ?valve ?subject ?taken ?landed WHERE { GRAPH ?e {
  { ?e a planning:PlanPublished ; planning:published ?plan . ?step execution:partOf ?plan BIND(planning:PlanPublished AS ?kind) }
  UNION { ?e a ?kind ; execution:act ?act . ?act execution:of ?step ; execution:taken ?taken
          FILTER(?kind IN (execution:StepTaken, execution:StepAnswered)) OPTIONAL { ?e execution:landed ?landed } }
  ?e prov:atTime ?at . ?step planning:fills ?action ; ?v ?valve ; ?s ?subject .
  FILTER(STRENDS(STR(?v), \"#valve\") && STRENDS(STR(?s), \"#subject\")) } } ORDER BY ?at ?kind";

#[tokio::test(start_paused = true)]
async fn history_holds_every_reading_and_the_journal_the_dose_published_taken_and_landed() {
    use orexis::events::{Field, Point};
    let store = store();
    let written: Arc<Mutex<Vec<Point>>> = Arc::default();
    let kept = written.clone();
    let sink = orexis::series::Sink::new(
        "HISTORY",
        "greenhouse-grower",
        Box::new(move |_, points| {
            kept.lock().unwrap().extend(points.iter().cloned());
            Ok(())
        }),
    );
    let journal = Arc::new(orexis::journal::Journal::new(None, 600.0, Arc::new(noon)).unwrap());
    let watching = orexis_agent::Watching {
        journal: Some(journal.clone()),
        history: Some(sink),
        metrics: None,
        traces: None,
    };
    let g = grower_watched(&store, watching);
    let (inbox, broker) = (g.inbox.clone(), g.broker.clone());
    {
        reading(&inbox, r#"{"temperature": 21.0}"#, noon());
        reading(&inbox, r#"{"moisture": 0.2}"#, noon());
        common::settled(&g.running).await;
        let later = plus(noon(), 10.5 * 60.0);
        until(&g, later).await;
        reading(&inbox, r#"{"moisture": 0.45}"#, later);
        common::settled(&g.running).await;
    }
    assert!(walking(&store).is_empty(), "the dose landed");
    let observed: Vec<(String, Field, Option<DateTime>)> = written
        .lock()
        .unwrap()
        .iter()
        .map(|p| (p.measurement.clone(), p.fields["value"].clone(), p.time))
        .collect();
    assert_eq!(
        observed,
        [
            ("AirTemperature".to_string(), Field::Float(21.0), Some(noon())),
            ("SoilMoisture".to_string(), Field::Float(0.2), Some(noon())),
            (
                "SoilMoisture".to_string(),
                Field::Float(0.45),
                Some(plus(noon(), 630.0))
            ),
        ],
        "the series holds the readings, and nothing else"
    );
    assert!(
        written
            .lock()
            .unwrap()
            .iter()
            .all(|p| p.fields.get("raw") == p.fields.get("value") && p.fields.len() == 2),
        "this world scales no sensor, so the raw count is the reading, said twice"
    );
    let tags: Vec<(String, String)> = written
        .lock()
        .unwrap()
        .iter()
        .map(|p| (p.tags["sensor"].clone(), p.tags["feature"].clone()))
        .collect();
    assert_eq!(
        tags,
        [
            pair("thermometer", "bed"),
            pair("moisture_probe", "bed"),
            pair("moisture_probe", "bed")
        ]
    );
    let (_, body) = orexis::journal::answer(&journal.store, DOSE_Q).unwrap();
    let body = String::from_utf8(body).unwrap();
    let mut dose = Vec::new();
    for row in body.split("{\"kind\"").skip(1) {
        let of = |var: &str| -> String {
            let found = if var == "kind" {
                Some(row)
            } else {
                row.split(&format!("\"{var}\":")).nth(1)
            };
            found
                .and_then(|f| f.split("\"value\":\"").nth(1))
                .and_then(|v| v.split('"').next())
                .map(|v| v.rsplit('#').next().unwrap().to_string())
                .unwrap_or_else(|| "-".into())
        };
        dose.push([
            of("kind"),
            of("action"),
            of("valve"),
            of("subject"),
            of("taken"),
            of("landed"),
        ]);
    }
    //  THE PLAN IS PUBLISHED AND ITS STEP TAKEN AT ONE INSTANT, which the journal's instants cannot order: the three
    //  are held in the order they happen.
    let rank = |kind: &str| {
        ["PlanPublished", "StepTaken", "StepAnswered"]
            .iter()
            .position(|k| *k == kind)
    };
    dose.sort_by_key(|row| rank(&row[0]));
    let said = |row: [&str; 6]| row.map(str::to_string);
    assert_eq!(
        dose,
        [
            said(["PlanPublished", "Dosing", "pump", "bed", "-", "-"]),
            said(["StepTaken", "Dosing", "pump", "bed", "true", "-"]),
            said(["StepAnswered", "Dosing", "pump", "bed", "true", "true"]),
        ],
        "the dose takes the bed, not a reading (#944): {body}"
    );
    assert_eq!(commands(&broker).len(), 1);
}

/// The dry bed dosed, and a day later the thermometer alone — with a metrics window written every pass and the last
/// as a stop writes it: every window written, as `_unanswered` in `world/greenhouse/tests/test_greenhouse.py` has them.
async fn unanswered() -> (Vec<Vec<orexis::events::Point>>, Broker) {
    use orexis::events::Point;
    let store = store();
    let writes: Arc<Mutex<Vec<Vec<Point>>>> = Arc::default();
    let kept = writes.clone();
    let sink = orexis::series::Sink::new(
        "METRICS",
        "greenhouse-grower-metrics",
        Box::new(move |_, points| {
            kept.lock().unwrap().push(points.to_vec());
            Ok(())
        }),
    );
    let watching = orexis_agent::Watching {
        metrics: Some(orexis_metrics::Window::new(
            sink,
            0.0,
            Some("greenhouse"),
            Some("grower"),
        )),
        ..Default::default()
    };
    let g = grower_watched(&store, watching);
    let (inbox, broker) = (g.inbox.clone(), g.broker.clone());
    {
        reading(&inbox, r#"{"temperature": 21.0}"#, noon());
        reading(&inbox, r#"{"moisture": 0.2}"#, noon());
        common::settled(&g.running).await;
        let later = plus(noon(), 86400.0);
        until(&g, later).await;
        reading(&inbox, r#"{"temperature": 21.0}"#, later);
        common::settled(&g.running).await;
        g.running.stop().await;
    }
    let windows = writes
        .lock()
        .unwrap()
        .iter()
        .filter(|w| !w.is_empty())
        .cloned()
        .collect();
    (windows, broker)
}

#[ignore = "written for a window a pass; to be held over a day of the agent's time (#1150)"]
#[tokio::test(start_paused = true)]
async fn a_dose_the_world_never_answers_is_a_failure_and_a_silent_probe_is_counted() {
    use orexis::events::{Field, Point};
    let (windows, broker) = unanswered().await;
    let (dosed, a_day_later) = (&windows[0], &windows[1]);
    let of = |window: &[Point], name: &str| -> Vec<Point> {
        window.iter().filter(|p| p.measurement == name).cloned().collect()
    };
    let one = |window: &[Point], name: &str| -> std::collections::BTreeMap<String, Field> {
        let found = of(window, name);
        assert_eq!(found.len(), 1, "{name}: {found:?}");
        found[0].fields.clone()
    };
    let int = |pairs: &[(&str, i64)]| -> std::collections::BTreeMap<String, Field> {
        pairs.iter().map(|(k, v)| (k.to_string(), Field::Int(*v))).collect()
    };
    let measured: BTreeSet<&str> = dosed.iter().map(|p| p.measurement.as_str()).collect();
    for m in ["pass", "imaginarium", "intentions", "act", "revisions", "silence"] {
        assert!(measured.contains(m), "{m} in {measured:?}");
    }
    assert_eq!(one(dosed, "intentions"), int(&[("standing", 1)]));
    assert_eq!(one(dosed, "silence"), int(&[("silent", 0)]));
    assert_eq!(
        (one(dosed, "act")["count"].clone(), one(dosed, "act")["taken"].clone()),
        (Field::Int(1), Field::Int(1))
    );
    let sum = |window: &[Point], name: &str, field: &str| -> i64 {
        of(window, name)
            .iter()
            .map(|p| match p.fields[field] {
                Field::Int(i) => i,
                _ => panic!("{field} is a level"),
            })
            .sum()
    };
    assert_eq!(sum(dosed, "imaginarium", "satisfied"), 1);
    assert_eq!(
        sum(dosed, "imaginarium", "met"),
        2,
        "the soil want in its dose's world, and the desire in the air's ground"
    );
    let revisions = one(dosed, "revisions");
    assert_eq!(revisions["unsettled"], Field::Int(0));
    assert!(matches!(revisions["revisions"], Field::Int(n) if n > 0));
    let ended: Vec<(String, Field)> = of(a_day_later, "intention")
        .iter()
        .map(|p| (p.tags["outcome"].clone(), p.fields["count"].clone()))
        .collect();
    assert_eq!(ended, [("failed".to_string(), Field::Int(2))]);
    assert_eq!(one(a_day_later, "intentions"), int(&[("standing", 0)]));
    assert_eq!(
        one(a_day_later, "act"),
        int(&[("count", 1), ("taken", 0)]),
        "the second dose, sized from no reading"
    );
    assert_eq!(
        one(a_day_later, "silence"),
        int(&[("silent", 1)]),
        "the probe, and not the thermometer"
    );
    let doubted: Vec<(String, std::collections::BTreeMap<String, Field>)> = of(a_day_later, "doubted")
        .iter()
        .map(|p| (p.tags["sensor"].clone(), p.fields.clone()))
        .collect();
    assert_eq!(
        doubted,
        [("moisture_probe".to_string(), int(&[("silent", 1), ("stuck", 0)]))]
    );
    assert!(of(dosed, "doubted").is_empty(), "a sensor nobody doubts is on no point");
    assert_eq!(broker.published().len(), 1);
}

/// The dry bed dosed and never answered, and a day later the thermometer alone, the moisture probe silent: the dose
/// planned then cannot be sized, so its step fails as it is taken. Planning does not plan it again in the present it
/// failed in (#1145): it was planned, taken and failed for as long as the agent ran.
#[tokio::test(start_paused = true)]
async fn a_plan_that_fails_as_it_is_taken_is_not_planned_again_until_something_new_is_heard() {
    const PUBLISHED: &str = "http://example.org/orexis/planning#PlanPublished";
    let store = store();
    let g = grower(&store);
    let published = Arc::new(Mutex::new(0));
    let counted = published.clone();
    g.running.handed.events.watch().connect(move |event, _| {
        if event.kind() == Some(PUBLISHED) {
            *counted.lock().unwrap() += 1;
        }
    });
    let inbox = g.inbox.clone();
    reading(&inbox, r#"{"temperature": 21.0}"#, noon());
    reading(&inbox, r#"{"moisture": 0.2}"#, noon());
    common::settled(&g.running).await;
    assert_eq!(*published.lock().unwrap(), 1, "the dry bed's dose");
    let later = plus(noon(), 86400.0);
    until(&g, later).await;
    let (before, sent) = (*published.lock().unwrap(), commands(&g.broker).len());
    reading(&inbox, r#"{"temperature": 21.0}"#, later);
    common::pass(&g.running, 600.0).await;
    let planned = *published.lock().unwrap() - before;
    assert!(
        planned <= 11,
        "{planned} plans published in ten minutes: the dose that cannot be sized was planned again and again"
    );
    assert_eq!(
        commands(&g.broker).len(),
        sent,
        "and no dose commanded, sized from no reading"
    );
    g.running.stop().await;
}
