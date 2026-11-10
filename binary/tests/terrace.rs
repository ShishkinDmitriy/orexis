//! The terrace on the binary, held to what `world/terrace/tests/test_terrace.py` holds the Python runtime to: the
//! sentinel's one message is five observations, the soil concluded dry against the bed's range, and the agent — holding
//! no desire — watches and sends nothing and keeps running; every reading a point in the series under its own
//! property; a board gone quiet said silent; the forecast fetched for the terrace's place; and the sovereign saying
//! through the agent's own bot that the probe is defective, believed as the world's word. Booted from the world's
//! documents copied without its `secrets/`, the place and the chat written as a clone's own would hold them, and every
//! member over a stand-in, so nothing reaches the network.

use std::cell::RefCell;
use std::fs;
use std::path::{Path, PathBuf};
use std::rc::Rc;
use std::sync::{Arc, Mutex};

use serde_json::{Value as Json, json};

use orexis::Error;
use orexis::boot::TREE;
use orexis::clock::{Manual, instant};
use orexis::events::{Field, Point};
use orexis::namespaces::Namespaces;
use orexis::ontology::{BELIEF, FORECAST, SELF_GRAPH};
use orexis::runtime::{Part, Runtime, UNFINISHED};
use orexis::store::{Store, Within, iri, value};
use orexis_agent::{Watching, Wiring, assemble_seen, booted};
use orexis_mqtt::driver::{Client, Mqtt};
use orexis_translation::model::{Answer, Failure, Model, Turn};

const T: &str = "http://example.org/orexis/world/terrace#";
const OBSERVATION: &str = "http://example.org/orexis/sensing#ObservationGraph";
const SILENCE: &str = "http://example.org/orexis/sensing#SilenceGraph";
const REVISION: &str = "http://example.org/orexis/belief#RevisionGraph";
const COMMITTED: &str = "http://example.org/orexis/execution#CommittedStepGraph";
const READINGS: &str = "sensors/moisture_sensor_terrace/reading";
const MESSAGE: &str = r#"{"moisture_raw": [{"value": 710, "age_s": 0}], "temperature": 14.5, "humidity": 0.8, "pressure": 1012, "battery": 3.91}"#;
const PLACE: &str = "@prefix : <http://example.org/orexis/world/terrace#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix schema: <https://schema.org/> .
<> a orexis:WorldGraph .
:terrace schema:geo [ schema:latitude 50.12 ; schema:longitude 10.34 ] .
";
const CHAT: &str = "@prefix : <http://example.org/orexis/world/terrace#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix telegram: <http://example.org/orexis/telegram#> .
<> a orexis:SocietyGraph .
:sovereign_telegram telegram:chatId \"4242\" .
";
const FORECAST_BODY: &[u8] =
    br#"{"hourly": {"time": ["2026-01-01T13:00", "2026-01-01T14:00", "2026-01-01T15:00"], "precipitation": [0.0, 10.0, 0.0]}}"#;
const PROBE: &str = "http://example.org/orexis/world/terrace#moisture_sensor_terrace";

fn tree() -> &'static Path {
    Path::new(TREE)
}

fn noon() -> oxsdatatypes::DateTime {
    instant("2026-01-01T12:00:00+00:00").unwrap()
}

fn plus(s: f64) -> oxsdatatypes::DateTime {
    noon().checked_add_day_time_duration(orexis::clock::seconds(s)).unwrap()
}

/// The terrace's documents copied without its secrets, with the place and the chat its own directory under `secrets/`
/// would hold where the test says.
fn variant(name: &str, place: bool, chat: bool) -> PathBuf {
    let root = std::env::temp_dir().join(format!("orexis-terrace-{name}-{}", std::process::id()));
    let _ = fs::remove_dir_all(&root);
    let world = root.join("world/terrace");
    let from = tree().parent().unwrap().join("world/terrace");
    copy(&from, &world, &["tests", "secrets", "mosquitto", "__pycache__"]);
    std::os::unix::fs::symlink(tree().parent().unwrap().join("domains"), root.join("domains")).unwrap();
    let secrets = world.join("secrets/terrace");
    fs::create_dir_all(&secrets).unwrap();
    if place {
        fs::write(secrets.join("place.ttl"), PLACE).unwrap();
    }
    if chat {
        fs::write(secrets.join("chat.ttl"), CHAT).unwrap();
    }
    world
}

fn copy(from: &Path, to: &Path, skipped: &[&str]) {
    fs::create_dir_all(to).unwrap();
    for entry in fs::read_dir(from).unwrap() {
        let path = entry.unwrap().path();
        let name = path.file_name().unwrap().to_string_lossy().into_owned();
        if skipped.contains(&name.as_str()) {
            continue;
        }
        if path.is_dir() {
            copy(&path, &to.join(&name), skipped);
        } else {
            fs::copy(&path, to.join(&name)).unwrap();
        }
    }
}

/// What the agent subscribes to and publishes over MQTT.
#[derive(Clone, Default)]
struct Broker(Rc<RefCell<(Vec<String>, Vec<String>)>>);

impl Client for Broker {
    fn subscribe(&mut self, pattern: &str) -> Result<(), Error> {
        self.0.borrow_mut().0.push(pattern.to_string());
        Ok(())
    }

    fn publish(&mut self, topic: &str, _payload: &[u8], _retain: bool) -> Result<(), Error> {
        self.0.borrow_mut().1.push(topic.to_string());
        Ok(())
    }
}

/// The Bot API as the bot calls it: what is queued answered by `getUpdates`, and everything sent kept.
#[derive(Clone, Default)]
struct Api {
    updates: Arc<Mutex<Vec<Json>>>,
    sent: Arc<Mutex<Vec<Json>>>,
}

impl Api {
    fn call(&self) -> orexis_telegram::driver::Call {
        let (updates, sent) = (self.updates.clone(), self.sent.clone());
        Arc::new(move |url, body| {
            if url.ends_with("/getUpdates") {
                return Ok(json!({"ok": true, "result": std::mem::take(&mut *updates.lock().unwrap())}));
            }
            if url.ends_with("/getMe") {
                return Ok(json!({"ok": true, "result": {"id": 900, "is_bot": true, "username": "terrace_bot"}}));
            }
            sent.lock().unwrap().push(body.clone());
            Ok(json!({"ok": true}))
        })
    }
}

/// A model that states what the test hands it, once, then answers in words; what each statement was answered, kept.
struct Stating {
    inputs: Mutex<Json>,
    answers: Arc<Mutex<Vec<String>>>,
}

impl Model for Stating {
    fn converse(&self, _system: &[String], messages: &[Json], _tools: &[Json], _last: bool) -> Result<Turn, Failure> {
        if messages.len() == 1 {
            let inputs = self.inputs.lock().unwrap().clone();
            return Ok(Turn {
                calls: vec![("c".into(), "state".into(), inputs.clone())],
                content: vec![json!({"type": "tool_use", "id": "c", "name": "state", "input": inputs})],
                ..Turn::default()
            });
        }
        let answered = messages.last().unwrap()["content"][0]["content"]
            .as_str()
            .unwrap_or_default()
            .to_string();
        self.answers.lock().unwrap().push(answered);
        Ok(Turn {
            text: "noted".into(),
            content: vec![json!({"type": "text", "text": "noted"})],
            ..Turn::default()
        })
    }

    fn ask(&self, _system: &str, _text: &str) -> Result<Answer, Failure> {
        Ok(Answer::default())
    }
}

/// The terrace booted from `world` and assembled over stand-ins: the broker, the web answering `web`, the bot over
/// `api`, the model where one is handed, and what watches it.
struct Terrace {
    store: Store,
    broker: Broker,
    asked: Arc<Mutex<Vec<String>>>,
}

fn store() -> Store {
    Store::new(Arc::new(Namespaces::of_tree(tree()).unwrap())).unwrap()
}

/// Run the terrace of `world` through `walk`, its parts lent to a runtime on a clock standing where the walk sets it.
fn terrace(
    world: &Path,
    web: Option<&'static [u8]>,
    api: &Api,
    model: Option<Arc<dyn Model>>,
    watching: Watching,
    walk: impl FnOnce(&Terrace, &mut Runtime<'_>, &Manual, &orexis_mqtt::driver::Inbox),
) {
    let t = Terrace {
        store: store(),
        broker: Broker::default(),
        asked: Arc::default(),
    };
    let loaded = booted(&t.store, tree(), world, "terrace", noon()).unwrap();
    for package in [
        "belief",
        "sensing",
        "prediction",
        "speech",
        "translation",
        "transport/mqtt",
        "transport/http",
        "transport/telegram",
    ] {
        assert!(loaded.iter().any(|p| p == package), "{package}: {loaded:?}");
    }
    let member = Mqtt::new(
        &t.store,
        &format!("{T}terrace_agent"),
        vec![(None, Box::new(t.broker.clone()))],
    );
    let inbox = member.inbox.clone();
    let asked = t.asked.clone();
    let mut http = orexis_http::driver::Http::new(
        &t.store,
        &format!("{T}terrace_agent"),
        Arc::new(move |url| {
            asked.lock().unwrap().push(url.to_string());
            web.map(<[u8]>::to_vec).ok_or_else(|| "no web here".to_string())
        }),
    );
    http.spawn = Box::new(|work| work());
    let mut telegram = orexis_telegram::driver::Telegram::new(
        &t.store,
        &format!("{T}terrace_agent"),
        "token",
        "https://bots.example",
        api.call(),
    );
    telegram.spawn = Box::new(|work| work());
    let wiring = Wiring {
        mqtt: Some(member),
        http: Some(http),
        telegram: Some(telegram),
        model,
        watching,
        ..Wiring::default()
    };
    let clock = std::sync::Arc::new(Manual::at(noon()));
    let (mut parts, seen) = assemble_seen(&t.store, "terrace", clock.clone(), &loaded, None, wiring).unwrap();
    assert!(parts.iter().any(|(p, _)| p == "translation"));
    let lent: Vec<(String, &mut dyn Part)> = parts
        .iter_mut()
        .map(|(p, part)| (p.clone(), part.as_mut() as &mut dyn Part))
        .collect();
    let mut runtime = Runtime::new(&t.store, "terrace", &clock, lent).unwrap();
    runtime.watch = seen.watch.clone();
    walk(&t, &mut runtime, &clock, &inbox);
    runtime.stop();
}

/// The agent's own beliefs of the present: no world's document, no self graph, no revision, no committed step and no
/// forecast.
fn present(store: &Store) -> Vec<String> {
    let mut shared = store.graphs_of(&[BELIEF], &Within::common()).unwrap();
    shared.extend(
        store
            .graphs_of(&[SELF_GRAPH, REVISION, COMMITTED, FORECAST], &Within::default())
            .unwrap(),
    );
    store
        .graphs_of(&[BELIEF], &Within::default())
        .unwrap()
        .into_iter()
        .filter(|g| !shared.contains(g))
        .collect()
}

fn local(iri: &str) -> String {
    iri.rsplit(['#', '/']).next().unwrap().to_string()
}

#[test]
fn the_agent_listens_on_the_boards_one_topic_alone_and_one_message_is_five_observations() {
    let world = variant("message", false, false);
    terrace(
        &world,
        None,
        &Api::default(),
        None,
        Watching::default(),
        |t, runtime, _, inbox| {
            assert_eq!(
                t.broker.0.borrow().0,
                [READINGS],
                "the board's readings; its chat is on Telegram"
            );
            inbox.deliver(READINGS, MESSAGE.as_bytes(), Some(noon()));
            assert_eq!(runtime.run(Some(2), 0.0).unwrap(), UNFINISHED, "it watches for good");
            let observed = t.store.graphs_of(&[OBSERVATION], &Within::default()).unwrap();
            let observed: Vec<&str> = observed.iter().map(String::as_str).collect();
            let read: std::collections::BTreeMap<String, f64> = t
                .store
                .rows(
                    "SELECT ?p ?v WHERE { ?o sosa:observedProperty ?p ; sosa:hasSimpleResult ?v }",
                    &observed,
                )
                .unwrap()
                .iter()
                .map(|r| (local(&iri(r, "p").unwrap()), value(r, "v").unwrap().parse().unwrap()))
                .collect();
            assert_eq!(
                read,
                [
                    ("AirHumidity", 0.8),
                    ("AirPressure", 1012.0),
                    ("AirTemperature", 14.5),
                    ("SoilMoisture", 0.2)
                ]
                .iter()
                .map(|(k, v)| (k.to_string(), *v))
                .collect(),
                "the battery's sensor is defective (#939): its number is kept, and is no reading"
            );
            let held = present(&t.store);
            let held: Vec<&str> = held.iter().map(String::as_str).collect();
            let facts: Vec<(String, String, String)> = t
                .store
                .rows("SELECT ?s ?p ?o WHERE { ?s ?p ?o }", &held)
                .unwrap()
                .iter()
                .map(|r| {
                    (
                        local(&iri(r, "s").unwrap()),
                        local(&iri(r, "p").unwrap()),
                        local(&iri(r, "o").unwrap()),
                    )
                })
                .collect();
            assert_eq!(
                facts,
                [("terrace_bed".into(), "soil".into(), "Dry".into())],
                "under the bed's floor, and nothing else"
            );
            assert!(
                t.broker.0.borrow().1.is_empty(),
                "nothing is wanted, so nothing is sent"
            );
            assert!(
                t.asked.lock().unwrap().is_empty(),
                "a clone holds no place, so no forecast is asked for"
            );
        },
    );
}

#[test]
fn a_board_that_goes_quiet_is_said_silent_with_nothing_else_arriving() {
    let world = variant("quiet", false, false);
    terrace(
        &world,
        None,
        &Api::default(),
        None,
        Watching::default(),
        |t, runtime, clock, inbox| {
            inbox.deliver(READINGS, MESSAGE.as_bytes(), Some(noon()));
            runtime.run(Some(1), 0.0).unwrap();
            clock.set(plus(100.0 * 60.0));
            runtime.run(Some(1), 0.0).unwrap();
            let silences = t.store.graphs_of(&[SILENCE], &Within::default()).unwrap();
            let silences: Vec<&str> = silences.iter().map(String::as_str).collect();
            let mut silent: Vec<String> = t
                .store
                .rows("SELECT ?s WHERE { ?s sensing:silentSince ?since }", &silences)
                .unwrap()
                .iter()
                .map(|r| local(&iri(r, "s").unwrap()))
                .collect();
            silent.sort();
            assert_eq!(
                silent,
                [
                    "air_humidity_terrace",
                    "air_pressure_terrace",
                    "air_temp_terrace",
                    "battery_sensor_terrace",
                    "moisture_sensor_terrace"
                ]
            );
            assert!(t.broker.0.borrow().1.is_empty(), "nothing is sent");
        },
    );
}

fn history() -> (Watching, Rc<RefCell<Vec<Point>>>) {
    let written: Rc<RefCell<Vec<Point>>> = Rc::default();
    let kept = written.clone();
    let sink = orexis::series::Sink::new(
        "HISTORY",
        "terrace-terrace",
        Box::new(move |_, points| {
            kept.borrow_mut().extend(points.iter().cloned());
            Ok(())
        }),
    );
    (
        Watching {
            history: Some(sink),
            ..Watching::default()
        },
        written,
    )
}

#[test]
fn each_reading_reaches_the_series_under_its_own_property() {
    let world = variant("series", false, false);
    let (watching, written) = history();
    terrace(&world, None, &Api::default(), None, watching, |_, runtime, _, inbox| {
        inbox.deliver(READINGS, MESSAGE.as_bytes(), Some(noon()));
        runtime.drain(noon()).unwrap();
    });
    let written = written.borrow();
    let mut points: Vec<(String, String, Field)> = written
        .iter()
        .map(|p| {
            (
                p.measurement.clone(),
                p.tags["sensor"].clone(),
                p.fields["value"].clone(),
            )
        })
        .collect();
    points.sort_by(|a, b| a.0.cmp(&b.0));
    assert_eq!(
        points,
        [
            (
                "AirHumidity".to_string(),
                "air_humidity_terrace".to_string(),
                Field::Float(0.8)
            ),
            (
                "AirPressure".to_string(),
                "air_pressure_terrace".to_string(),
                Field::Float(1012.0)
            ),
            (
                "AirTemperature".to_string(),
                "air_temp_terrace".to_string(),
                Field::Float(14.5)
            ),
            (
                "BatteryVoltage".to_string(),
                "battery_sensor_terrace".to_string(),
                Field::Float(3.91)
            ),
            (
                "SoilMoisture".to_string(),
                "moisture_sensor_terrace".to_string(),
                Field::Float(0.2)
            ),
        ]
    );
    let features: std::collections::BTreeSet<String> =
        written.iter().filter_map(|p| p.tags.get("feature").cloned()).collect();
    assert_eq!(
        features,
        ["terrace_battery".to_string(), "terrace_bed".to_string()]
            .into_iter()
            .collect()
    );
    let defective: Vec<&str> = written
        .iter()
        .filter(|p| p.tags.contains_key("defective"))
        .map(|p| p.tags["sensor"].as_str())
        .collect();
    assert_eq!(
        defective,
        ["battery_sensor_terrace"],
        "its number still reaches the series, tagged as no reading"
    );
    assert!(
        written.iter().all(|p| p.time == Some(noon())),
        "at the reading's own instant"
    );
}

#[test]
fn an_alarm_is_two_points_in_the_history_and_a_step_not_a_slope() {
    let world = variant("alarm", false, false);
    let (watching, written) = history();
    terrace(&world, None, &Api::default(), None, watching, |_, runtime, _, inbox| {
        let alarm = r#"{"moisture_raw": [{"value": 710, "age_s": 25}, {"value": 410, "age_s": 0}], "sensor": "moisture_sensor_terrace", "wake": "alarm"}"#;
        inbox.deliver(READINGS, alarm.as_bytes(), Some(noon()));
        runtime.drain(noon()).unwrap();
    });
    let mut soil: Vec<(oxsdatatypes::DateTime, Field)> = written
        .borrow()
        .iter()
        .filter(|p| p.measurement == "SoilMoisture")
        .map(|p| (p.time.unwrap(), p.fields["value"].clone()))
        .collect();
    soil.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
    let before = noon()
        .checked_sub_day_time_duration(orexis::clock::seconds(25.0))
        .unwrap();
    assert_eq!(soil, [(before, Field::Float(0.2)), (noon(), Field::Float(1.0))]);
}

#[test]
fn every_metric_the_terrace_writes_is_an_observers_and_no_planners() {
    let world = variant("metrics", false, false);
    let written: Rc<RefCell<Vec<Point>>> = Rc::default();
    let kept = written.clone();
    let sink = orexis::series::Sink::new(
        "METRICS",
        "terrace-terrace-metrics",
        Box::new(move |_, points| {
            kept.borrow_mut().extend(points.iter().cloned());
            Ok(())
        }),
    );
    let watching = Watching {
        metrics: Some(orexis_metrics::Window::new(
            sink,
            3600.0,
            Some("terrace"),
            Some("terrace"),
        )),
        ..Watching::default()
    };
    terrace(&world, None, &Api::default(), None, watching, |_, runtime, _, inbox| {
        for _ in 0..2 {
            inbox.deliver(READINGS, MESSAGE.as_bytes(), Some(noon()));
            runtime.run(Some(1), 0.0).unwrap();
        }
    });
    let wanted: std::collections::BTreeSet<(String, String)> = written
        .borrow()
        .iter()
        .flat_map(|p| {
            p.fields
                .keys()
                .map(|f| (p.measurement.clone(), f.clone()))
                .collect::<Vec<_>>()
        })
        .collect();
    for pair in [
        ("silence", "silent"),
        ("received", "interval_s_mean"),
        ("revisions", "revisions"),
        ("pass", "drain_s_max"),
    ] {
        assert!(
            wanted.contains(&(pair.0.to_string(), pair.1.to_string())),
            "{pair:?} in {wanted:?}"
        );
    }
    let measured: std::collections::BTreeSet<&str> = wanted.iter().map(|(m, _)| m.as_str()).collect();
    for m in ["planner", "reroot", "imaginarium", "intentions"] {
        assert!(!measured.contains(m), "no planner or executor runs here: {m}");
    }
}

#[test]
fn a_forecast_is_fetched_for_the_terraces_place_and_written_an_hour_a_graph() {
    let world = variant("forecast", true, false);
    terrace(
        &world,
        Some(FORECAST_BODY),
        &Api::default(),
        None,
        Watching::default(),
        |t, runtime, _, inbox| {
            inbox.deliver(READINGS, MESSAGE.as_bytes(), Some(noon()));
            runtime.run(Some(2), 0.0).unwrap();
            assert_eq!(
                *t.asked.lock().unwrap(),
                [
                    "https://api.open-meteo.com/v1/forecast?latitude=50.12&longitude=10.34&hourly=precipitation&timezone=GMT&forecast_days=2"
                ]
            );
            let forecasts = t.store.graphs_of(&[FORECAST], &Within::default()).unwrap();
            let forecasts: Vec<&str> = forecasts.iter().map(String::as_str).collect();
            let mut hours: Vec<f64> = t
                .store
                .rows(
                    &format!(
                        "SELECT ?v WHERE {{ ?o sosa:madeBySensor <{T}forecast_terrace> ; sosa:hasSimpleResult ?v }}"
                    ),
                    &forecasts,
                )
                .unwrap()
                .iter()
                .map(|r| value(r, "v").unwrap().parse().unwrap())
                .collect();
            hours.sort_by(f64::total_cmp);
            assert_eq!(hours, [0.0, 0.0, 10.0]);
            assert!(
                !forecasts.iter().any(|g| g.contains("terrace_bed")),
                "no forecast of the soil is written"
            );
        },
    );
}

#[test]
fn the_sovereign_says_through_the_agents_own_bot_that_the_probe_is_defective_and_its_next_number_is_no_reading() {
    let world = variant("sovereign", true, true);
    let api = Api::default();
    let answers: Arc<Mutex<Vec<String>>> = Arc::default();
    let model = Arc::new(Stating {
        inputs: Mutex::new(Json::Null),
        answers: answers.clone(),
    });
    let shared: Arc<dyn Model> = model.clone();
    terrace(
        &world,
        None,
        &api,
        Some(shared),
        Watching::default(),
        |t, runtime, clock, inbox| {
            let texts = || {
                api.sent
                    .lock()
                    .unwrap()
                    .iter()
                    .filter(|m| m.get("text").is_some())
                    .count()
            };
            let say = |runtime: &mut Runtime<'_>, text: &str, inputs: Json, n: usize| {
                *model.inputs.lock().unwrap() = inputs;
                api.updates.lock().unwrap().push(
                json!({"update_id": 7 + n, "message": {"chat": {"id": 4242, "type": "private"}, "from": {"id": 1}, "text": text}}),
            );
                //  THE BOT POLLS AS ITS TIMER FALLS DUE, the conversation runs on its own thread, and what it said is handed
                //  back to a pass: passes run until the answer is sent.
                for _ in 0..200 {
                    clock.advance(3.0);
                    runtime.run(Some(1), 0.0).unwrap();
                    if answers.lock().unwrap().len() >= n && texts() >= n {
                        return;
                    }
                    std::thread::sleep(std::time::Duration::from_millis(20));
                }
                panic!("no answer to {text:?}");
            };
            let soil = |runtime: &mut Runtime<'_>, at| {
                inbox.deliver(READINGS, MESSAGE.as_bytes(), Some(at));
                clock.set(at);
                runtime.run(Some(1), 0.0).unwrap();
                let observed = t.store.graphs_of(&[OBSERVATION], &Within::default()).unwrap();
                let observed: Vec<&str> = observed.iter().map(String::as_str).collect();
                let found = t
                .store
                .rows(
                    &format!(
                        "SELECT ?v ?why WHERE {{ ?o sosa:resultTime ?t ; sosa:madeBySensor <{PROBE}> \
                         OPTIONAL {{ ?o sosa:hasSimpleResult ?v }} OPTIONAL {{ ?o sensing:defect ?why }} }} ORDER BY DESC(?t) LIMIT 1"
                    ),
                    &observed,
                )
                .unwrap();
                (
                    found[0].get("v").map(|_| value(&found[0], "v").unwrap()),
                    value(&found[0], "why"),
                )
            };
            say(
                runtime,
                "the probe shows strange numbers",
                json!({"says": format!("<{PROBE}> sensing:defect \"it shows strange numbers\" .")}),
                1,
            );
            assert_eq!(*answers.lock().unwrap(), ["kept: the agent believes it now"]);
            let said: Vec<Json> = api
                .sent
                .lock()
                .unwrap()
                .iter()
                .filter(|m| m.get("text").is_some())
                .cloned()
                .collect();
            assert_eq!(
                said.iter().map(|m| m["text"].as_str().unwrap()).collect::<Vec<_>>(),
                ["noted"]
            );
            assert_eq!(said[0]["chat_id"], "4242", "answered through its own bot");
            assert_eq!(
                soil(runtime, plus(60.0)),
                (None, Some("it shows strange numbers".to_string())),
                "kept, and no reading"
            );
            say(
                runtime,
                "the probe is fine again",
                json!({"unsays": [format!("<{PROBE}> sensing:defect")]}),
                2,
            );
            assert_eq!(answers.lock().unwrap().len(), 2);
            assert_eq!(answers.lock().unwrap()[1], "kept: the agent believes it now");
            assert_eq!(
                soil(runtime, plus(20.0 * 60.0 + 60.0)),
                (Some("0.2".to_string()), None),
                "unsaid, a reading again"
            );
        },
    );
}
