//! Prediction across the packages beside it, as `test_a_pot_and_its_probe.py`, and `test_create.py` hold the Python agent: bytes become a percept the rules revise to its quantity, the
//! foresight from it is the instants the reading changes range, a second reading follows the first and is what the
//! next foresight is made from. The story crosses sensing and belief, which a TEST here may use and the code may not;
//! the grounds the planner lays with the foresight are planning's own case, `lay_ground`'s.

use std::path::{Path, PathBuf};

use oxsdatatypes::DateTime;

use orexis::clock::{seconds, seconds_of};
use orexis::document::Document;
use orexis::foresight::Foresight;
use orexis::ontology::{BELIEF, FORECAST, RECORD};
use orexis::snapshots::{ME, now, stand_in};
use orexis::store::{Store, Within, value};
use orexis_belief::Deliberator;
use orexis_prediction::create::Prediction;
use orexis_prediction::foresee::foresee;
use orexis_prediction::ontology::OBSERVATION_GRAPH;
use orexis_sensing::received::received;

const PROBE: &str = "http://example.org/test#probe";
/// THE POT'S RANGES, as its world states them: operating 0.1 to 0.3, surviving 0.02 to 0.45.
const OPERATING: (f64, f64) = (0.1, 0.3);
const SURVIVAL: (f64, f64) = (0.02, 0.45);

fn here() -> &'static Path {
    Path::new(env!("CARGO_MANIFEST_DIR"))
}

fn agent() -> PathBuf {
    here().parent().unwrap().to_path_buf()
}

fn plus(at: DateTime, by: f64) -> DateTime {
    at.checked_add_day_time_duration(seconds(by)).unwrap()
}

fn pot() -> Store {
    let store = stand_in(&here().join("tests/worlds/a_pot_and_its_probe.trig"));
    for vocabulary in [
        agent().join("orexis-sensing/rules.ttl"),
        agent().join("orexis-belief/ontology.ttl"),
    ] {
        store
            .put_document(&Document::read(&vocabulary).unwrap(), None, None, None, true)
            .unwrap();
    }
    store
}

fn sides(number: f64) -> Vec<i32> {
    [OPERATING, SURVIVAL]
        .iter()
        .map(|(low, high)| {
            if number < *low {
                -1
            } else if number > *high {
                1
            } else {
                0
            }
        })
        .collect()
}

/// The number a percept holds, in what the rules concluded of it, which is of sensing's kind.
fn number(store: &Store, graph: &str) -> f64 {
    let mut graphs = vec![graph.to_string()];
    graphs.extend(store.revisions_of(&[graph], OBSERVATION_GRAPH).unwrap());
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let found = store
        .rows("SELECT ?v WHERE { ?o sosa:hasSimpleResult ?v }", &graphs)
        .unwrap();
    assert_eq!(found.len(), 1);
    value(&found[0], "v").unwrap().parse().unwrap()
}

/// Bytes arrive: received, the reading revised — the rules conclude what it is of and its quantity — then the
/// foresight is made from it, as a pass makes it.
fn reading(store: &Store, value: f64, minutes: f64) -> (String, Option<orexis_prediction::foresee::Foresight>) {
    let at = plus(now(), minutes * 60.0);
    let read = store
        .graphs_of(
            &[BELIEF],
            &Within {
                at: Some(at),
                common: true,
                ..Within::default()
            },
        )
        .unwrap();
    let graph = received(store, ME, PROBE, format!(r#"{{"value": {value}}}"#).as_bytes(), at)
        .unwrap()
        .remove(0);
    let mut deliberator = Deliberator::new(store, "keeper", None).unwrap();
    deliberator.changed(&graph, Some(read), OBSERVATION_GRAPH);
    deliberator.deliberate(at).unwrap();
    store.close_catalogue().unwrap();
    (graph, foresee(store, at, None).unwrap())
}

fn known(store: &Store, at: DateTime) -> Result<Vec<String>, orexis::Error> {
    store.graphs_of(
        &[BELIEF, RECORD],
        &Within {
            at: Some(at),
            until: Some(at),
            ..Within::default()
        },
    )
}

/// What the foresight answers from `at` to its horizon, as (minutes past `at`, the number laid).
fn knots(store: &Store, foresight: &mut dyn Foresight, at: DateTime) -> Vec<(f64, f64)> {
    let mut out = Vec::new();
    let mut t = at;
    let until = foresight.horizon();
    let mut graphs_at = |when: DateTime| known(store, when);
    while let Some((when, arrival)) = foresight.advance(store, t, until, &mut graphs_at).unwrap() {
        let laid: f64 = arrival
            .iter()
            .find(|t| t.predicate.as_str().ends_with("hasSimpleResult"))
            .and_then(|t| match &t.object {
                oxigraph::model::Term::Literal(l) => l.value().parse().ok(),
                _ => None,
            })
            .unwrap();
        out.push((when.checked_sub(at).map_or(0.0, seconds_of) / 60.0, laid));
        t = when;
    }
    out
}

#[test]
fn a_reading_under_the_floor_is_revised_to_its_quantity() {
    let store = pot();
    let (graph, _) = reading(&store, 0.05, 0.0);
    assert_eq!(number(&store, &graph), 0.05);
}

#[test]
fn a_reading_inside_is_foreseen_to_meet_the_floor_within_the_hour_and_each_number_lies_on_its_side() {
    let store = pot();
    let (_, foresight) = reading(&store, 0.25, 0.0);
    let mut foresight = foresight.unwrap();
    let knots = knots(&store, &mut foresight, now());
    let mut said = vec![sides(0.25)];
    said.extend(knots.iter().map(|(_, n)| sides(*n)));
    let crossings: Vec<(f64, f64)> = knots
        .iter()
        .zip(said.windows(2))
        .filter(|(_, pair)| pair[0] != pair[1])
        .map(|(k, _)| *k)
        .collect();
    assert_eq!(crossings.len(), 2, "{knots:?}");
    assert!(
        (crossings[0].0 - 54.0).abs() <= 1.0 && (crossings[1].0 - 83.0).abs() <= 4.0,
        "{knots:?}"
    );
    assert!(
        SURVIVAL.0 <= crossings[0].1 && crossings[0].1 < OPERATING.0,
        "{knots:?}"
    );
    assert!(crossings[1].1 < SURVIVAL.0, "{knots:?}");
}

#[test]
fn a_second_reading_follows_the_first_and_the_foresight_is_made_from_it() {
    let store = pot();
    let (before, first) = reading(&store, 0.25, 0.0);
    let (graph, second) = reading(&store, 0.09, 16.0);
    assert_eq!(
        first.unwrap().keys[0].lo,
        0.25,
        "each foresight from the reading in hand"
    );
    assert_eq!(second.unwrap().keys[0].lo, 0.09);
    assert_eq!(number(&store, &graph), 0.09);
    assert_eq!(number(&store, &before), 0.25, "and the first percept is kept");
    assert!(
        store.graphs_of(&[FORECAST], &Within::default()).unwrap().is_empty(),
        "no forecast of its own"
    );
}

#[test]
fn its_part_offers_the_foresight_and_hears_nothing() {
    let store = pot();
    let part = Prediction;
    assert!(
        part.foresee(&store, now(), None).unwrap().is_none(),
        "no percept in hand: nothing is foreseen"
    );
    let (_, made) = reading(&store, 0.25, 0.0);
    let made = made.unwrap();
    assert_eq!(made.keys.iter().map(|k| k.sensor.as_str()).collect::<Vec<_>>(), [PROBE]);
    assert!(made.keys[0].lo == 0.25 && made.keys[0].laid);
    assert!(part.foresee(&store, now(), None).unwrap().is_some());
    let nowhere = |_: &str, _: &str| false;
    assert!(
        part.foresee(&store, now(), Some(&nowhere)).unwrap().is_none(),
        "a scope laying none is handed none"
    );
}
