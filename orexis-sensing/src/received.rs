//! A TRANSPORT HANDS SENSING THE BYTES IT READ FOR A SENSOR, AND A PERCEPT IS WRITTEN — the callback, and the whole
//! of the translation row, as `agent/sensing/received.py` writes it.
//!
//! **BYTES TO A NUMBER TO A PERCEPT PER READING**: each reading is ONE `sosa:Observation`, in SOSA's words, named
//! for its sensor and its instant, in a graph of its own, `sensing:ObservationGraph`, received, the agent's; a
//! payload that does not decode writes nothing. **EACH LINKS TO THE ONE BEFORE IT**, and the latest holds from its
//! instant until the next is due and a grace past it, or until the next arrives, which ends it. **A SENSOR'S LAST
//! FEW ARE KEPT**, as deep as its stuck rule reads. **A READING LATE IS NOT A READING MISSING (#870)**: the grace is
//! how late a reading may be and still be the same promise kept. **THE READINGS ONE MESSAGE CARRIES** are percepts
//! in the chain, oldest first. **A SERIES IS A FORECAST**, one graph per stretch still ahead, every forecast the
//! sensor gave before forgotten first. **A READING ENDS A SILENCE**. Nothing is concluded here: what a percept is
//! of, its quantity and whether its sensor is stuck are revisions, which the rules conclude.

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{isoformat, microseconds};
use orexis::hash::{hash_named_graph, py_float_repr, py_round};
use orexis::ontology::{BELIEF, FORECAST, RECEIVED, local_of};
use orexis::store::{Store, Within, iri, value};

use crate::cadence::{cadence_of, limit_of};
use crate::ontology::{
    OBSERVATION_GRAPH, SILENCE_GRAPH, STUCK_AFTER_TERM, forecast_graph, forecast_of, percept_graph, percept_of,
};
use crate::pipeline::{decode, decode_series, reads_series};

/// HOW LATE A READING MAY BE, in its sensor's cadences: the percept before it stays the present until its successor
/// arrives or this long past the instant the successor was due. Not a stance: how late a reading arrives is the
/// instrument's and the path its bytes take.
pub const GRACE: f64 = 1.0;

/// THE KEY: what the sensor observes, of what it is mounted in — read for a series alone.
const KEY_Q: &str = "SELECT ?feature ?property WHERE { $sensor sosa:observes ?property ; sosa:isHostedBy ?feature }";

/// EVERY PERCEPT OF THIS SENSOR KEPT, newest first, and whether a percept names it as its previous.
const KEPT_Q: &str = "
SELECT ?g ?o ?t (BOUND(?later) AS ?followed) WHERE {
  GRAPH $cat { ?g a sensing:ObservationGraph }
  GRAPH ?g { ?o sosa:madeBySensor $sensor OPTIONAL { ?o sosa:resultTime ?t } }
  OPTIONAL { GRAPH ?h { ?later sensing:previous ?o } GRAPH $cat { ?h a sensing:ObservationGraph } } }
ORDER BY DESC(?t) DESC(?g)";

/// WHETHER A GRAPH OF THIS NAME IS ALREADY SAID — a second reading of one sensor at one instant.
const SAID_Q: &str = "SELECT ?p WHERE { GRAPH $cat { $g ?p ?o } } LIMIT 1";

/// THE SILENCE A READING ENDS: each kept of this sensor whose end is not yet said, found by its content.
const SILENT_Q: &str = "
SELECT ?g ?since WHERE { GRAPH $cat { ?g a sensing:SilenceGraph }
  GRAPH ?g { $sensor sensing:silentSince ?since FILTER NOT EXISTS { $sensor sensing:silentUntil ?until } } }";

/// THE FORECAST THIS SENSOR GAVE BEFORE: every graph of it, found by its content.
const FORECAST_Q: &str =
    "SELECT ?g WHERE { GRAPH $cat { ?g a orexis:ForecastGraph } GRAPH ?g { ?o sosa:madeBySensor $sensor } }";

fn later(at: DateTime, by: f64) -> Result<DateTime, Error> {
    at.checked_add_day_time_duration(microseconds(by))
        .ok_or_else(|| Error::Evaluation(format!("{} past {}", by, isoformat(at))))
}

fn literal(at: DateTime) -> String {
    format!("\"{}\"^^xsd:dateTime", isoformat(at))
}

/// Write what `sensor` read, `payload` decoded by its binding: a percept per reading, oldest first, each linked to
/// the one before it, the latest standing as the present until the next is due and a grace past it — or, for a
/// sensor reading a series, one forecast per stretch still ahead. The graphs written and kept, none where the
/// payload holds nothing it reads. `me` is who holds it, written as the percept's author and the graph's owner.
pub fn received(store: &Store, me: &str, sensor: &str, payload: &[u8], at: DateTime) -> Result<Vec<String>, Error> {
    received_by(store, me, sensor, payload, at, None, None)
}

/// `received`, with the instrument's word about how it read (`procedure`) and the instant a device that speaks for
/// itself says the result applies to (`phenomenon_at`, #101), where `at` is the arrival.
pub fn received_by(
    store: &Store,
    me: &str,
    sensor: &str,
    payload: &[u8],
    at: DateTime,
    procedure: Option<&str>,
    phenomenon_at: Option<DateTime>,
) -> Result<Vec<String>, Error> {
    if reads_series(store, sensor)? {
        let common = store.graphs_of(&[BELIEF], &Within::common())?;
        let common: Vec<&str> = common.iter().map(String::as_str).collect();
        let keys = store.rows(&bind(KEY_Q, &[("sensor", Value::iri(sensor))])?, &common)?;
        let key = match keys.as_slice() {
            [one] => (iri(one, "feature"), iri(one, "property")),
            _ => (None, None),
        };
        let (Some(feature), Some(property)) = key else {
            log::warn!(
                "{} has no key: one property observed of one host makes one, and the world states {}",
                local_of(sensor),
                keys.len()
            );
            return Ok(Vec::new());
        };
        return forecast(store, me, sensor, &feature, &property, payload, at);
    }
    let Some(readings) = decode(store, sensor, payload)? else {
        return Ok(Vec::new());
    };
    let Some(cat) = store.catalogue()? else {
        return Err(Error::Catalogue("no graph describes itself as the catalogue".into()));
    };
    let kept = store.rows(
        &bind(
            KEPT_Q,
            &[("cat", Value::iri(cat.as_str())), ("sensor", Value::iri(sensor))],
        )?,
        &[],
    )?;
    let latest = kept.iter().find(|r| value(r, "followed").as_deref() != Some("true"));
    //  EVERY READING THE MESSAGE CARRIES, oldest first, each placed that long before it arrived.
    let instants: Vec<DateTime> = readings
        .iter()
        .map(|(_, age)| {
            at.checked_sub_day_time_duration(microseconds(*age))
                .ok_or_else(|| Error::Evaluation(format!("{age}s before {}", isoformat(at))))
        })
        .collect::<Result<_, _>>()?;
    let cadence = cadence_of(store, sensor)?;
    if let Some(g) = latest.and_then(|r| iri(r, "g")) {
        store.end_graph(&g, instants[0], OBSERVATION_GRAPH)?;
    }
    let silences = store.rows(
        &bind(
            SILENT_Q,
            &[("cat", Value::iri(cat.as_str())), ("sensor", Value::iri(sensor))],
        )?,
        &[],
    )?;
    for silence in silences {
        let Some(g) = iri(&silence, "g") else { continue };
        store.update(&format!(
            "INSERT DATA {{ GRAPH <{g}> {{ <{sensor}> sensing:silentUntil {} }} }}",
            literal(instants[0])
        ))?;
        store.end_graph(&g, instants[0], SILENCE_GRAPH)?;
        log::info!(
            "{}: {} reads again, silent since {}",
            local_of(me),
            local_of(sensor),
            value(&silence, "since").unwrap_or_default()
        );
    }
    let mut before = latest.and_then(|r| iri(r, "o"));
    let mut written = Vec::new();
    for (n, ((number, _), when)) in readings.iter().zip(&instants).enumerate() {
        let last = n == readings.len() - 1;
        let until = if last {
            cadence.map(|c| later(*when, (1.0 + GRACE) * c)).transpose()?
        } else {
            Some(instants[n + 1])
        };
        let (node, graph) = named(store, &cat, me, sensor, *when)?;
        write(
            store,
            &Percept {
                me,
                sensor,
                graph: &graph,
                node: &node,
                number: *number,
                at: *when,
                until,
                before: before.as_deref(),
                procedure,
                phenomenon_at: if last { phenomenon_at } else { None },
            },
        )?;
        written.push(graph);
        before = Some(node);
    }
    let earlier: String = readings[..readings.len() - 1]
        .iter()
        .map(|(n, a)| format!(", and read {} {}s before", py_g(*n), py_g(*a)))
        .collect();
    log::info!(
        "{}: {} reads {}{earlier}",
        local_of(me),
        local_of(sensor),
        py_float_repr(readings[readings.len() - 1].0)
    );
    //  AS DEEP AS SENSING'S RULES READ: the sensor's last `stuckAfter` percepts, and never fewer than the latest.
    let depth = limit_of(store, sensor, STUCK_AFTER_TERM)?.max(1) as usize;
    let mut newest_first: Vec<String> = written.iter().rev().cloned().collect();
    newest_first.extend(kept.iter().filter_map(|r| iri(r, "g")));
    //  AN OLDER ONE IS FILED PAST, never forgotten here: what becomes of a reading sensing has done with is
    //  housekeeping, and whoever archives it removes it (`past`).
    for old in newest_first.iter().skip(depth) {
        crate::past::shelve(store, old)?;
    }
    let held: Vec<&String> = newest_first.iter().take(depth).collect();
    Ok(written.iter().filter(|g| held.contains(g)).cloned().collect())
}

/// A number as Python's `%g` spells it, for the log.
fn py_g(n: f64) -> String {
    if n.fract() == 0.0 && n.abs() < 1e16 {
        format!("{}", n as i64)
    } else {
        format!("{n}")
    }
}

/// The node and the graph of the reading `sensor` made at `when` — the second of that instant named apart from the
/// first, so a sensor read twice in one instant keeps both.
fn named(store: &Store, cat: &str, me: &str, sensor: &str, when: DateTime) -> Result<(String, String), Error> {
    let agent = local_of(me);
    let mut n = 1;
    while !store
        .rows(
            &bind(
                SAID_Q,
                &[
                    ("cat", Value::iri(cat)),
                    ("g", Value::iri(percept_graph(&agent, sensor, when, n))),
                ],
            )?,
            &[],
        )?
        .is_empty()
    {
        n += 1;
    }
    Ok((percept_of(sensor, when, n), percept_graph(&agent, sensor, when, n)))
}

/// One percept: what `sensor` gave, `number` at `at`, standing until `until` or for good, naming `before`.
struct Percept<'p> {
    me: &'p str,
    sensor: &'p str,
    graph: &'p str,
    node: &'p str,
    number: f64,
    at: DateTime,
    until: Option<DateTime>,
    before: Option<&'p str>,
    procedure: Option<&'p str>,
    phenomenon_at: Option<DateTime>,
}

fn write(store: &Store, p: &Percept<'_>) -> Result<(), Error> {
    let node = p.node;
    let mut said = vec![
        format!("<{node}> a sosa:Observation"),
        format!(
            "<{node}> sensing:rawResult \"{}\"^^xsd:decimal",
            py_float_repr(py_round(p.number))
        ),
        format!("<{node}> sosa:resultTime {}", literal(p.at)),
        format!("<{node}> sosa:madeBySensor <{}>", p.sensor),
        format!("<{node}> prov:wasGeneratedBy <{}>", p.me),
    ];
    if let Some(before) = p.before {
        said.push(format!("<{node}> sensing:previous <{before}>"));
    }
    if let Some(when) = p.phenomenon_at {
        said.push(format!("<{node}> sosa:phenomenonTime {}", literal(when)));
    }
    if let Some(procedure) = p.procedure.filter(|s| !s.is_empty()) {
        said.push(format!("<{node}> sosa:usedProcedure <{procedure}>"));
    }
    let entry = store.entry(p.graph, &[OBSERVATION_GRAPH], RECEIVED, Some(p.me), Some(p.at), p.until)?;
    store.update(&format!(
        "INSERT DATA {{\n  GRAPH <{}> {{ {} . }}\n  {entry} }}",
        p.graph,
        said.join(" . ")
    ))
}

/// A forecast's number as the Python writer spells it: six places, trailing noughts cut, a whole number keeping one.
fn forecast_number(value: f64) -> String {
    let fixed = format!("{:.6}", py_round(value) + 0.0);
    let cut = fixed.trim_end_matches('0');
    if cut.ends_with('.') {
        format!("{cut}0")
    } else {
        cut.to_string()
    }
}

/// One forecast graph per stretch of the series still ahead at `at`, the sensor's earlier forecast forgotten first;
/// the graphs, first stretch first.
fn forecast(
    store: &Store,
    me: &str,
    sensor: &str,
    feature: &str,
    property: &str,
    payload: &[u8],
    at: DateTime,
) -> Result<Vec<String>, Error> {
    let Some(stretches) = decode_series(store, sensor, payload)? else {
        return Ok(Vec::new());
    };
    let Some(cat) = store.catalogue()? else {
        return Err(Error::Catalogue("no graph describes itself as the catalogue".into()));
    };
    let old = store.rows(
        &bind(
            FORECAST_Q,
            &[("cat", Value::iri(cat.as_str())), ("sensor", Value::iri(sensor))],
        )?,
        &[],
    )?;
    for g in old.iter().filter_map(|r| iri(r, "g")) {
        store.forget_graph(&g, Some(BELIEF))?;
    }
    let agent = local_of(me);
    let mut written = Vec::new();
    for (start, end, value) in &stretches {
        if *end <= at {
            continue;
        }
        let graph = forecast_graph(&agent, sensor, *start);
        let node = forecast_of(sensor, *start);
        let said = [
            format!("<{node}> a sosa:Observation"),
            format!("<{node}> sosa:hasFeatureOfInterest <{feature}>"),
            format!("<{node}> sosa:observedProperty <{property}>"),
            format!(
                "<{node}> sosa:hasSimpleResult \"{}\"^^xsd:decimal",
                forecast_number(*value)
            ),
            format!("<{node}> sosa:resultTime {}", literal(at)),
            format!("<{node}> sosa:phenomenonTime {}", literal(*start)),
            format!("<{node}> sosa:madeBySensor <{sensor}>"),
            format!("<{node}> prov:wasGeneratedBy <{me}>"),
        ];
        let entry = store.entry(&graph, &[FORECAST], RECEIVED, Some(me), Some(*start), Some(*end))?;
        store.update(&format!(
            "INSERT DATA {{\n  GRAPH <{graph}> {{ {} . }}\n  {entry} }}",
            said.join(" . ")
        ))?;
        hash_named_graph(store, &graph, None)?;
        written.push(graph);
    }
    log::info!(
        "{}: {} of {} forecast for {} stretch(es)",
        local_of(me),
        local_of(property),
        local_of(feature),
        written.len()
    );
    Ok(written)
}

#[cfg(test)]
pub(crate) mod tests {
    //! `received`, held as `agent/sensing/tests/test_received.py` holds it: one case per file, held to a patch of the
    //! store it leaves — and the chain, held by code: each percept names the one before it, a message's readings
    //! oldest first; the latest is the one holding now, every older one's period ended where its successor's
    //! began; and a sensor's last `sensing:stuckAfter` are kept, the rest filed past (#944).

    use std::path::{Path, PathBuf};

    use orexis::clock::{instant, seconds};
    use orexis::snapshots::{ME, all_read, cases_in, held_to_diff, now, stand_in};

    use super::*;
    use crate::ontology::default_of;

    const TEST: &str = "http://example.org/test#";
    const OBSERVED: &str = "http://example.org/orexis/graph/observed/keeper/";
    const FORECAST_AT: &str = "http://example.org/orexis/graph/forecast/keeper/";
    const CADENCE: f64 = 900.0;

    fn here() -> &'static Path {
        Path::new(env!("CARGO_MANIFEST_DIR"))
    }

    fn cases() -> PathBuf {
        here().join("tests/received")
    }

    fn world(name: &str) -> Store {
        stand_in(&here().join("tests/worlds").join(name))
    }

    fn probe() -> String {
        format!("{TEST}probe")
    }

    fn plus(at: DateTime, by: f64) -> DateTime {
        if by >= 0.0 {
            at.checked_add_day_time_duration(seconds(by)).unwrap()
        } else {
            at.checked_sub_day_time_duration(seconds(-by)).unwrap()
        }
    }

    /// WHAT EACH CASE'S BYTES SAY, and which graphs they land in.
    fn bytes(case: &str) -> (&'static [u8], Vec<String>) {
        match case {
            "a_first_reading_becomes_an_observation" => {
                (br#"{"value": 0.22}"#, vec![format!("{OBSERVED}probe_20260101T120000Z")])
            }
            "a_second_reading_follows_the_first" => {
                (br#"{"value": 0.08}"#, vec![format!("{OBSERVED}probe_20260101T120000Z")])
            }
            "a_forecast_is_a_graph_per_stretch_ahead" => (
                br#"{"hourly": {"time": ["2026-01-01T11:00", "2026-01-01T12:00", "2026-01-01T13:00", "2026-01-01T14:00", "2026-01-01T15:00"], "precipitation": [0.5, 0.0, 1.2, null, 0.3]}}"#,
                vec![
                    format!("{FORECAST_AT}weather_20260101T120000Z"),
                    format!("{FORECAST_AT}weather_20260101T140000Z"),
                ],
            ),
            other => panic!("{other}: no bytes are said for it"),
        }
    }

    #[test]
    fn received_leaves_the_observation_the_patch_says() {
        all_read(&cases(), 3);
        for case in cases_in(&cases()) {
            let stem = case.file_stem().unwrap().to_string_lossy().into_owned();
            let store = stand_in(&case);
            let (payload, expected) = bytes(&stem);
            let sensor = format!("{TEST}{}", if stem.contains("forecast") { "weather" } else { "probe" });
            let written = received(&store, ME, &sensor, payload, now()).unwrap();
            assert_eq!(written, expected, "{stem}");
            held_to_diff(&case, &store, "received");
        }
    }

    #[test]
    fn bytes_that_hold_no_reading_write_nothing() {
        let store = stand_in(&cases().join("a_first_reading_becomes_an_observation.trig"));
        let before = store.graph_names().unwrap();
        assert!(
            received(&store, ME, &probe(), br#"{"temperature": 21}"#, now())
                .unwrap()
                .is_empty()
        );
        assert_eq!(store.graph_names().unwrap(), before);
    }

    #[test]
    fn a_sensor_mounted_nowhere_keeps_its_number_and_is_of_nothing() {
        let store = world("a_board_and_its_peripherals.trig");
        assert_eq!(
            received(&store, ME, &format!("{TEST}loose"), br#"{"value": 0.2}"#, now()).unwrap(),
            [format!("{OBSERVED}loose_20260101T120000Z")]
        );
        assert!(
            store
                .rows("SELECT ?f WHERE { GRAPH ?g { ?o sosa:hasFeatureOfInterest ?f } }", &[])
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn one_message_for_two_sensors_is_two_observations() {
        let store = world("a_board_and_its_peripherals.trig");
        let message = br#"{"temperature": 21.5, "soil": {"moisture": 0.22}}"#;
        let mut written = Vec::new();
        for sensor in [probe(), format!("{TEST}thermo")] {
            written.extend(received(&store, ME, &sensor, message, now()).unwrap());
        }
        assert_eq!(
            written,
            [
                format!("{OBSERVED}probe_20260101T120000Z"),
                format!("{OBSERVED}thermo_20260101T120000Z")
            ]
        );
        let found = store
            .rows(
                "SELECT ?s ?v WHERE { GRAPH ?g { ?o a sosa:Observation ; sosa:madeBySensor ?s ; sensing:rawResult ?v } } ORDER BY ?s",
                &[],
            )
            .unwrap();
        let got: Vec<(String, f64)> = found
            .iter()
            .map(|r| (local_of(&iri(r, "s").unwrap()), value(r, "v").unwrap().parse().unwrap()))
            .collect();
        assert_eq!(got, [("probe".to_string(), 0.22), ("thermo".to_string(), 21.5)]);
    }

    const CHAIN_Q: &str = "
SELECT ?o ?n ?t ?previous WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a sensing:ObservationGraph }
  GRAPH ?g { ?o sosa:madeBySensor $sensor ; sensing:rawResult ?n ; sosa:resultTime ?t
             OPTIONAL { ?o sensing:previous ?previous } } }
ORDER BY ?t";

    const PERIOD_Q: &str =
        "SELECT ?start ?end WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $g dcterms:temporal ?p .
               ?p orexis:start ?start . OPTIONAL { ?p orexis:end ?end } } }";

    fn chain(store: &Store) -> Vec<(String, f64, Option<String>)> {
        store
            .rows(&bind(CHAIN_Q, &[("sensor", Value::iri(probe()))]).unwrap(), &[])
            .unwrap()
            .iter()
            .map(|r| {
                (
                    iri(r, "o").unwrap(),
                    value(r, "n").unwrap().parse().unwrap(),
                    iri(r, "previous"),
                )
            })
            .collect()
    }

    fn period(store: &Store, graph: &str) -> (DateTime, Option<DateTime>) {
        let found = store
            .rows(&bind(PERIOD_Q, &[("g", Value::iri(graph))]).unwrap(), &[])
            .unwrap();
        assert_eq!(found.len(), 1, "{graph}");
        (
            instant(&value(&found[0], "start").unwrap()).unwrap(),
            value(&found[0], "end").map(|e| instant(&e).unwrap()),
        )
    }

    /// One reading of each of `numbers` by the probe, a cadence apart from `start`; the last one's instant.
    fn every_cadence(store: &Store, numbers: &[f64], start: DateTime) -> DateTime {
        let mut at = start;
        for number in numbers {
            received(store, ME, &probe(), format!(r#"{{"value": {number}}}"#).as_bytes(), at).unwrap();
            at = plus(at, CADENCE);
        }
        plus(at, -CADENCE)
    }

    fn holding(store: &Store, at: DateTime) -> Vec<String> {
        store
            .graphs_of(
                &[OBSERVATION_GRAPH],
                &Within {
                    at: Some(at),
                    now: Some(at),
                    ..Within::default()
                },
            )
            .unwrap()
    }

    #[test]
    fn a_sensor_stating_no_frequency_stands_until_the_next() {
        let store = world("a_board_and_its_peripherals.trig");
        let first = received(&store, ME, &probe(), br#"{"soil": {"moisture": 0.2}}"#, now()).unwrap();
        assert_eq!(period(&store, &first[0]), (now(), None));
        let next = plus(now(), 86400.0);
        let second = received(&store, ME, &probe(), br#"{"soil": {"moisture": 0.3}}"#, next).unwrap();
        assert_eq!(period(&store, &first[0]), (now(), Some(next)));
        assert_eq!(period(&store, &second[0]), (next, None));
    }

    #[test]
    fn each_reading_names_the_one_before_it_and_only_the_last_stuck_after_are_kept() {
        let stuck_after = default_of(STUCK_AFTER_TERM).unwrap() as usize;
        let store = world("a_pot_and_its_probe.trig");
        let numbers: Vec<f64> = (0..stuck_after + 2)
            .map(|n| py_round(0.20 + n as f64 / 100.0))
            .collect();
        every_cadence(&store, &numbers, now());
        let chain = chain(&store);
        let kept: Vec<f64> = chain.iter().map(|(_, n, _)| *n).collect();
        assert_eq!(
            kept,
            numbers[numbers.len() - stuck_after..],
            "the last six, oldest first"
        );
        for pair in chain.windows(2) {
            assert_eq!(pair[1].2.as_deref(), Some(pair[0].0.as_str()));
        }
        let oldest = chain[0].2.clone().expect("the oldest kept names one");
        assert!(!chain.iter().any(|(o, _, _)| *o == oldest), "and it is no longer read");
        assert_eq!(
            store.graphs_of(&[OBSERVATION_GRAPH], &Within::default()).unwrap().len(),
            stuck_after
        );
        //  AND THE REST ARE PAST, NOT GONE: filed in a kind of their own, for whoever archives them to remove.
        let past = crate::past::past(&store).unwrap();
        assert_eq!(
            past.len(),
            numbers.len() - stuck_after,
            "every reading older than the last six"
        );
        crate::past::forget(&store, &past[0]).unwrap();
        assert_eq!(
            crate::past::past(&store).unwrap().len(),
            past.len() - 1,
            "until one is forgotten"
        );
        assert_eq!(
            store.graphs_of(&[OBSERVATION_GRAPH], &Within::default()).unwrap().len(),
            stuck_after,
            "which takes nothing sensing reads"
        );
    }

    #[test]
    fn the_depth_kept_is_the_observer_roles_where_it_states_one() {
        let store = world("a_pot_and_its_probe.trig");
        observing(&store, &probe(), &[(STUCK_AFTER_TERM, 2)]);
        every_cadence(&store, &[0.2, 0.21, 0.22, 0.23], now());
        let kept: Vec<f64> = chain(&store).iter().map(|(_, n, _)| *n).collect();
        assert_eq!(kept, [0.22, 0.23]);
    }

    #[test]
    fn the_latest_is_the_one_holding_now_and_every_older_one_has_ended() {
        let store = world("a_pot_and_its_probe.trig");
        let last = every_cadence(&store, &[0.2, 0.21, 0.22], now());
        let at_last = format!("{OBSERVED}probe_20260101T123000Z");
        assert_eq!(holding(&store, last), std::slice::from_ref(&at_last));
        assert_eq!(
            holding(&store, plus(last, -1.0)),
            [format!("{OBSERVED}probe_20260101T121500Z")]
        );
        assert_eq!(
            period(&store, &at_last),
            (last, Some(plus(last, 2.0 * CADENCE))),
            "the next due and a grace"
        );
        assert!(
            holding(&store, plus(last, 2.0 * CADENCE)).is_empty(),
            "and none past that"
        );
        let beliefs = store.graphs_of(&[BELIEF], &Within::default()).unwrap();
        assert!(
            !store
                .graphs_of(&[OBSERVATION_GRAPH], &Within::default())
                .unwrap()
                .iter()
                .any(|g| beliefs.contains(g)),
            "a percept is no belief"
        );
    }

    #[test]
    fn a_message_carrying_several_readings_chains_them_in_order() {
        let store = stand_in(&cases().join("a_first_reading_becomes_an_observation.trig"));
        let quiet = received(&store, ME, &probe(), br#"{"value": 640}"#, plus(now(), -CADENCE)).unwrap();
        let alarm = br#"{"value": [{"value": 656, "age_s": 25}, {"value": 361, "age_s": 0}]}"#;
        let both = received(&store, ME, &probe(), alarm, now()).unwrap();
        assert_eq!(
            both,
            [
                format!("{OBSERVED}probe_20260101T115935Z"),
                format!("{OBSERVED}probe_20260101T120000Z")
            ]
        );
        let p = probe();
        assert_eq!(
            chain(&store),
            [
                (format!("{p}.20260101T114500Z"), 640.0, None),
                (
                    format!("{p}.20260101T115935Z"),
                    656.0,
                    Some(format!("{p}.20260101T114500Z"))
                ),
                (
                    format!("{p}.20260101T120000Z"),
                    361.0,
                    Some(format!("{p}.20260101T115935Z"))
                ),
            ],
            "named off the sensor, never in a vocabulary's namespace"
        );
        assert_eq!(
            period(&store, &quiet[0]).1,
            Some(plus(now(), -25.0)),
            "ended where the earlier began"
        );
        assert_eq!(period(&store, &both[0]), (plus(now(), -25.0), Some(now())));
        assert_eq!(holding(&store, now()), [both[1].clone()]);
        let beat = received(
            &store,
            ME,
            &probe(),
            br#"{"value": [{"value": 370, "age_s": 0}]}"#,
            now(),
        )
        .unwrap();
        assert_eq!(
            beat,
            [format!("{OBSERVED}probe_20260101T120000Z_2")],
            "a second at one instant is named apart"
        );
        let previous: Vec<Option<String>> = chain(&store)
            .into_iter()
            .filter(|(o, _, _)| o.ends_with("_2"))
            .map(|(_, _, p)| p)
            .collect();
        assert_eq!(previous, [Some(format!("{p}.20260101T120000Z"))]);
        assert_eq!(holding(&store, now()), beat);
    }

    /// `store` with the keeper's self graph saying it plays an observer role reading `sensor`, the role stating each
    /// of `limits`, as `agent/conftest.py`'s `observing` adds it.
    pub(crate) fn observing(store: &Store, sensor: &str, limits: &[(&str, i64)]) {
        let selves = store
            .graphs_of(&[orexis::ontology::SELF_GRAPH], &Within::default())
            .unwrap();
        let figures: String = limits.iter().map(|(t, n)| format!(" ; <{t}> {n}")).collect();
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{}> {{ <{ME}> orexis:plays [ a sensing:Observer ; sensing:sensor <{sensor}>{figures} ] }} }}",
                selves[0]
            ))
            .unwrap();
    }
}
