//! `rules.ttl`: sensing's rule set, put in the store as a boot puts every document, and held — through belief's
//! deliberator, which a test here may use and the code may not — to what it concludes of a percept, as
//! `test_rules.py` and `test_scaling.py` beside this file hold the Python agent to it: what a percept is of, its
//! quantity through a scaling and a calibration, and whether its sensor is stuck on one number.
//!
//! STUCK IS A RULE OVER THE PERCEPTS KEPT (#462, #944): a sensor whose last `sensing:stuckAfter` readings all gave
//! one raw number is stuck on it, concluded in the revision of the percept arriving, so it holds while that percept
//! does, and the first reading whose number differs finds the kept ones no longer agree. It counts READINGS.

use std::path::{Path, PathBuf};

use oxsdatatypes::DateTime;

use orexis::bind::{Value, bind};
use orexis::clock::seconds;
use orexis::document::Document;
use orexis::hash::py_round;
use orexis::ontology::{BELIEF, RECORD};
use orexis::snapshots::{ME, now, stand_in};
use orexis::store::{Store, Within, iri, value};
use orexis_belief::Deliberator;
use orexis_sensing::ontology::{OBSERVATION_GRAPH, STUCK_AFTER_TERM, default_of};
use orexis_sensing::received::received;

const TEST: &str = "http://example.org/test#";
const PROBE: &str = "http://example.org/test#probe";
const CADENCE: f64 = 900.0;

fn here() -> &'static Path {
    Path::new(env!("CARGO_MANIFEST_DIR"))
}

fn stuck_after() -> usize {
    default_of(STUCK_AFTER_TERM).unwrap() as usize
}

fn plus(at: DateTime, by: f64) -> DateTime {
    if by >= 0.0 {
        at.checked_add_day_time_duration(seconds(by)).unwrap()
    } else {
        at.checked_sub_day_time_duration(seconds(-by)).unwrap()
    }
}

fn put(store: &Store, path: PathBuf) {
    store
        .put_document(&Document::read(&path).unwrap(), None, None, None, true)
        .unwrap();
}

/// `world` with sensing's rules and its ontology, the observer shape whose default the stuck rule reads.
fn with_rules(world: &str) -> Store {
    let store = stand_in(&here().join("tests/worlds").join(world));
    put(&store, here().join("rules.ttl"));
    put(&store, here().join("ontology.ttl"));
    store
}

fn strs(names: &[String]) -> Vec<&str> {
    names.iter().map(String::as_str).collect()
}

/// `payload` read by `sensor` at `at`, and each percept written revised as sensing has the deliberator revise it:
/// beside what is known then, into `kind`.
fn read(store: &Store, sensor: &str, payload: &str, at: DateTime, read: &[String], kind: &str) -> Vec<String> {
    let written = received(store, ME, sensor, payload.as_bytes(), at).unwrap();
    let mut deliberator = Deliberator::new(store, "keeper", None).unwrap();
    for graph in &written {
        deliberator.changed(graph, Some(read.to_vec()), kind);
    }
    deliberator.deliberate(at).unwrap();
    written
}

fn read_at(store: &Store, value: &str, at: DateTime) -> Vec<String> {
    let known = store.graphs_of(&[BELIEF, RECORD], &Within::at(at)).unwrap();
    read(
        store,
        PROBE,
        &format!(r#"{{"value": {value}}}"#),
        at,
        &known,
        OBSERVATION_GRAPH,
    )
}

fn holding(at: DateTime) -> Within {
    Within {
        at: Some(at),
        now: Some(at),
        ..Within::default()
    }
}

/// Every sensor said stuck at `at`, and on what: read where the percept holding then is.
fn stuck(store: &Store, at: DateTime) -> Vec<(String, f64)> {
    let graphs = store.graphs_of(&[OBSERVATION_GRAPH], &holding(at)).unwrap();
    store
        .rows("SELECT ?sensor ?n WHERE { ?sensor sensing:stuckOn ?n }", &strs(&graphs))
        .unwrap()
        .iter()
        .map(|r| {
            let sensor = iri(r, "sensor").unwrap();
            (
                sensor.rsplit('#').next().unwrap().to_string(),
                value(r, "n").unwrap().parse().unwrap(),
            )
        })
        .collect()
}

fn every_cadence(store: &Store, numbers: &[f64], start: DateTime) -> DateTime {
    let mut at = start;
    for number in numbers {
        read_at(store, &number.to_string(), at);
        at = plus(at, CADENCE);
    }
    plus(at, -CADENCE)
}

fn probe_stuck(n: f64) -> Vec<(String, f64)> {
    vec![("probe".to_string(), n)]
}

#[test]
fn what_is_concluded_of_a_percept_is_a_percept_and_no_belief() {
    let world = with_rules("a_pot_and_its_probe.trig");
    let graph = read_at(&world, "0.05", now()).remove(0);
    let revisions = world.revisions_of(&[&graph], OBSERVATION_GRAPH).unwrap();
    assert_eq!(revisions.len(), 1);
    assert!(
        world.revisions_of(&[&graph], BELIEF).unwrap().is_empty(),
        "no belief was concluded of a percept"
    );
    assert!(
        !world
            .rows(
                "SELECT ?f ?v WHERE { ?o sosa:hasFeatureOfInterest ?f ; sosa:hasSimpleResult ?v }",
                &[&revisions[0]]
            )
            .unwrap()
            .is_empty()
    );
    let kinds: Vec<String> = world
        .rows(
            &bind(
                "SELECT ?k WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $g a ?k } }",
                &[("g", Value::iri(revisions[0].as_str()))],
            )
            .unwrap(),
            &[],
        )
        .unwrap()
        .iter()
        .filter_map(|r| iri(r, "k"))
        .collect();
    assert!(
        kinds.iter().any(|k| k == OBSERVATION_GRAPH) && !kinds.iter().any(|k| k == BELIEF),
        "{kinds:?}"
    );
    let known = world.graphs_of(&[BELIEF, RECORD], &Within::at(now())).unwrap();
    assert!(!known.contains(&revisions[0]) && !known.contains(&graph));
    assert_eq!(
        world.closed(OBSERVATION_GRAPH).unwrap(),
        [OBSERVATION_GRAPH, "http://example.org/orexis#Graph"]
            .iter()
            .map(|s| s.to_string())
            .collect::<std::collections::BTreeSet<_>>()
            .into_iter()
            .collect::<Vec<_>>()
    );
}

#[test]
fn a_samples_observation_is_of_the_sample() {
    let world = with_rules("a_probe_in_a_sample_of_the_pot.trig");
    let graph = read_at(&world, "0.05", now()).remove(0);
    let revisions = world.revisions_of(&[&graph], OBSERVATION_GRAPH).unwrap();
    let of = world
        .rows("SELECT ?f WHERE { ?o sosa:hasFeatureOfInterest ?f }", &strs(&revisions))
        .unwrap();
    assert_eq!(of.len(), 1);
    assert!(iri(&of[0], "f").unwrap().ends_with("#patch"));
}

#[test]
fn stuck_holds_at_exactly_stuck_after_readings_of_one_number() {
    let world = with_rules("a_pot_and_its_probe.trig");
    let last = every_cadence(&world, &vec![0.25; stuck_after() - 1], now());
    assert_eq!(stuck(&world, last), [], "one short of the limit");
    let tipped = every_cadence(&world, &[0.25], plus(last, CADENCE));
    assert_eq!(stuck(&world, tipped), probe_stuck(0.25));
    assert_eq!(
        stuck(&world, plus(tipped, -1.0)),
        [],
        "not before the reading that made it so"
    );
    let again = every_cadence(&world, &[0.25], plus(tipped, CADENCE));
    assert_eq!(
        stuck(&world, again),
        probe_stuck(0.25),
        "said once, of the percept holding"
    );
}

#[test]
fn the_first_reading_that_differs_ends_it() {
    let world = with_rules("a_pot_and_its_probe.trig");
    let last = every_cadence(&world, &vec![0.25; stuck_after()], now());
    assert!(!stuck(&world, last).is_empty());
    let moved = every_cadence(&world, &[0.26], plus(last, CADENCE));
    assert_eq!(stuck(&world, moved), [], "the kept readings no longer agree");
    let last = every_cadence(&world, &vec![0.26; stuck_after() - 2], plus(moved, CADENCE));
    assert_eq!(stuck(&world, last), [], "counted from its first reading, and one short");
    let last = every_cadence(&world, &[0.26], plus(last, CADENCE));
    assert_eq!(stuck(&world, last), probe_stuck(0.26));
}

#[test]
fn it_counts_readings_not_time() {
    let world = with_rules("a_pot_and_its_probe.trig");
    let mut at = now();
    for _ in 0..stuck_after() - 1 {
        read_at(&world, "0.25", at);
        at = plus(at, 86400.0);
    }
    assert_eq!(
        stuck(&world, plus(at, -86400.0)),
        [],
        "five days of one number are five readings"
    );
    read_at(&world, "0.25", at);
    assert_eq!(stuck(&world, at), probe_stuck(0.25));
}

#[test]
fn a_number_a_count_apart_is_two_numbers() {
    let world = with_rules("a_pot_and_its_probe.trig");
    let numbers: Vec<f64> = (0..stuck_after() + 2).map(|n| 1330.0 + (n % 2) as f64).collect();
    let last = every_cadence(&world, &numbers, now());
    assert_eq!(stuck(&world, last), []);
}

#[test]
fn a_silence_ends_it() {
    let world = with_rules("a_pot_and_its_probe.trig");
    let last = every_cadence(&world, &vec![0.25; stuck_after()], now());
    assert_eq!(stuck(&world, plus(last, 2.0 * CADENCE - 1.0)), probe_stuck(0.25));
    assert_eq!(stuck(&world, plus(last, 2.0 * CADENCE)), []);
}

#[test]
fn a_sensor_stating_no_frequency_is_never_said_stuck() {
    let store = with_rules("a_board_and_its_peripherals.trig");
    let mut at = now();
    for _ in 0..stuck_after() + 2 {
        let known = store.graphs_of(&[BELIEF, RECORD], &Within::at(at)).unwrap();
        read(
            &store,
            PROBE,
            r#"{"soil": {"moisture": 0.2}}"#,
            at,
            &known,
            OBSERVATION_GRAPH,
        );
        at = plus(at, 86400.0);
    }
    assert_eq!(stuck(&store, plus(at, -86400.0)), []);
}

#[test]
fn the_stuck_limit_is_the_observer_roles_where_it_states_one() {
    let store = with_rules("a_pot_and_its_probe.trig");
    let selves = store
        .graphs_of(&[orexis::ontology::SELF_GRAPH], &Within::default())
        .unwrap();
    store
        .update(&format!(
            "INSERT DATA {{ GRAPH <{}> {{ <{ME}> orexis:plays [ a sensing:Observer ; sensing:sensor <{PROBE}> ; <{STUCK_AFTER_TERM}> 2 ] }} }}",
            selves[0]
        ))
        .unwrap();
    let first = every_cadence(&store, &[0.25], now());
    assert_eq!(stuck(&store, first), [], "one reading is short of two");
    let second = every_cadence(&store, &[0.25], plus(first, CADENCE));
    assert_eq!(stuck(&store, second), probe_stuck(0.25));
}

#[test]
fn a_defective_sensors_percept_keeps_its_number_carries_why_and_is_no_reading() {
    let world = with_rules("a_pot_and_its_probe.trig");
    world
        .update(&format!(
            "INSERT DATA {{ GRAPH <{TEST}world> {{ <{PROBE}> sensing:defect \"its channel reads another's charge\" }} }}"
        ))
        .unwrap();
    let graph = read_at(&world, "0.05", now()).remove(0);
    let mut percept = vec![graph.clone()];
    percept.extend(world.revisions_of(&[&graph], OBSERVATION_GRAPH).unwrap());
    let found = world
        .rows(
            "SELECT ?given ?why WHERE { ?o sensing:scaledResult ?given ; sensing:defect ?why }",
            &strs(&percept),
        )
        .unwrap();
    assert_eq!(found.len(), 1);
    assert_eq!(value(&found[0], "given").as_deref(), Some("0.05"));
    assert_eq!(
        value(&found[0], "why").as_deref(),
        Some("its channel reads another's charge")
    );
    assert!(
        world
            .rows("SELECT ?v WHERE { ?o sosa:hasSimpleResult ?v }", &strs(&percept))
            .unwrap()
            .is_empty(),
        "no reading of it"
    );
}

// --- the scaling: a number no scaling scales is its own quantity, a two-point scaling rescales it, unclamped, and a
// two-point calibration corrects a quantity in its own unit, after any scaling ----------------------------------

/// THE PROBE'S SCALING, as a world states it beside the sensor: 3200 in dry air, 1300 in water.
const SCALING: &str = r#"<http://example.org/test#probe_scaling> a sensing:TwoPointScaling ; sensing:scales <http://example.org/test#probe> ;
    sensing:point [ rdfs:label "dry" ; sensing:reads 3200 ; sensing:standsFor 0.0 ] ,
                  [ rdfs:label "wet" ; sensing:reads 1300 ; sensing:standsFor 1.0 ] ."#;
/// AND A CORRECTION OF ITS MOISTURE in its own unit: it reads 0.02 at nought and 0.98 at one.
const CALIBRATION: &str = r#"<http://example.org/test#probe_calibration> a sensing:TwoPointCalibration ; sensing:corrects <http://example.org/test#probe> ;
    sensing:point [ rdfs:label "low" ; sensing:reads 0.02 ; sensing:standsFor 0.0 ] ,
                  [ rdfs:label "high" ; sensing:reads 0.98 ; sensing:standsFor 1.0 ] ."#;

fn pot() -> Store {
    let store = stand_in(&here().join("tests/worlds/a_pot_and_its_probe.trig"));
    put(&store, here().join("rules.ttl"));
    store
}

/// What the world states beside the sensor, in a common graph of its own.
fn stated(store: &Store, said: &[&str]) {
    let graph = format!("{TEST}instruments");
    let entry = store
        .entry(
            &graph,
            &[BELIEF],
            "http://example.org/orexis#Asserted",
            None,
            None,
            None,
        )
        .unwrap();
    store
        .update(&format!(
            "INSERT DATA {{ GRAPH <{graph}> {{ {} }}\n  {entry} }}",
            said.join(" ")
        ))
        .unwrap();
}

/// A reading of `number`, revised beside what the world states as belief's part revises it: what the rules
/// concluded of it, the scaled number and the reading.
fn scaled(store: &Store, number: &str) -> Option<(f64, f64)> {
    let common = store.graphs_of(&[BELIEF], &Within::common()).unwrap();
    let graph = read(
        store,
        PROBE,
        &format!(r#"{{"value": {number}}}"#),
        now(),
        &common,
        BELIEF,
    )
    .remove(0);
    let found = store
        .rows(
            "SELECT ?scaled ?reading WHERE { ?o sensing:scaledResult ?scaled ; sosa:hasSimpleResult ?reading }",
            &[&graph, &format!("{graph}/revisions")],
        )
        .unwrap();
    found.first().map(|r| {
        (
            value(r, "scaled").unwrap().parse().unwrap(),
            value(r, "reading").unwrap().parse().unwrap(),
        )
    })
}

#[test]
fn a_number_no_scaling_scales_is_its_own_quantity() {
    assert_eq!(scaled(&pot(), "0.22"), Some((0.22, 0.22)));
}

#[test]
fn a_count_is_rescaled_on_the_line_through_the_two_points() {
    let store = pot();
    stated(&store, &[SCALING]);
    assert_eq!(scaled(&store, "2250"), Some((0.5, 0.5)));
    assert_eq!(
        scaled(&store, "1110").map(|(_, r)| r),
        Some(1.1),
        "past the wet point, unclamped"
    );
}

#[test]
fn a_calibration_corrects_the_scaled_quantity_in_its_own_unit() {
    let store = pot();
    stated(&store, &[SCALING, CALIBRATION]);
    assert_eq!(scaled(&store, "2250"), Some((0.5, 0.5)));
    assert_eq!(scaled(&store, "1300"), Some((1.0, py_round(0.98 / 0.96))));
}

#[test]
fn a_scaling_with_one_point_concludes_no_quantity() {
    let store = pot();
    let one = SCALING.replace(
        r#" ,
                  [ rdfs:label "wet" ; sensing:reads 1300 ; sensing:standsFor 1.0 ]"#,
        "",
    );
    stated(&store, &[&one]);
    assert_eq!(scaled(&store, "2250"), None);
}
