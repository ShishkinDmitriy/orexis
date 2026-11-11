//! HOW OFTEN A SENSOR REPORTS, in SSN-System's words, as `agent/sensing/cadence.py` reads it — by `received` to say
//! until when an observation stands, and by `missed` to say when a silence has lasted long enough to be one.
//!
//! A sensor's `ssn-system:hasSystemCapability` carries an `ssn-system:hasSystemProperty` typed
//! `ssn-system:Frequency`, whose `schema:value` is the time between one observation and the next in the
//! `schema:unitCode` it states — seconds where it states none. A sensor stating no frequency has no cadence.
//!
//! **WHICH SENSORS ARE THE AGENT'S** (`sensors`): the ones an observer role it plays reads, declared in its self
//! graph. **WHEN A CADENCE HAS LAPSED** (`lapsed`): the sensors whose latest percept's period has ended — one read
//! and one owner, which `missed` asks and a transport beneath asks to nudge a board — and when one next will
//! (`next_lapse`), which that transport waits for.

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::instant as parse_instant;
use orexis::ontology::{BELIEF, SELF_GRAPH, local_of};
use orexis::store::{Store, Within, instant, iri, value};

use crate::ontology::default_of;

const CADENCE_Q: &str = "
SELECT ?every ?unit WHERE {
  $sensor ssn-system:hasSystemCapability/ssn-system:hasSystemProperty ?f .
  ?f a ssn-system:Frequency ; schema:value ?every .
  OPTIONAL { ?f schema:unitCode ?unit } }";

/// EVERY SENSOR WHOSE LATEST PERCEPT HAS LAPSED, with the instant it did: the latest is the one no percept names as
/// its previous, and a revision, of the same kind, holds no `sosa:madeBySensor` and is no match.
const LAPSED_Q: &str = "
SELECT ?sensor ?end WHERE {
  GRAPH $cat { ?g a sensing:ObservationGraph ; dcterms:temporal/orexis:end ?end . FILTER(?end < $now) }
  GRAPH ?g { ?obs sosa:madeBySensor ?sensor }
  FILTER NOT EXISTS { GRAPH ?h { ?later sensing:previous ?obs } GRAPH $cat { ?h a sensing:ObservationGraph } } }
ORDER BY ?end ?sensor";

/// THE SOONEST INSTANT A LATEST PERCEPT LAPSES, not yet come: the one a reading falls due and its grace runs out.
const NEXT_LAPSE_Q: &str = "
SELECT (MIN(?end) AS ?next) WHERE {
  GRAPH $cat { ?g a sensing:ObservationGraph ; dcterms:temporal/orexis:end ?end . FILTER(?end >= $now) }
  GRAPH ?g { ?obs sosa:madeBySensor ?sensor }
  FILTER NOT EXISTS { GRAPH ?h { ?later sensing:previous ?obs } GRAPH $cat { ?h a sensing:ObservationGraph } } }";

/// EVERY SENSOR THE AGENT READS: each an observer role it plays declares, in the self graph.
const SENSORS_Q: &str =
    "SELECT DISTINCT ?sensor WHERE { ?me a orexis:Self ; orexis:plays/sensing:sensor ?sensor } ORDER BY ?sensor";

/// WHAT AN OBSERVER ROLE READING THIS SENSOR STATES OF A LIMIT, in the self graph where it is played.
const LIMIT_Q: &str =
    "SELECT DISTINCT ?n WHERE { ?me a orexis:Self ; orexis:plays ?role . ?role sensing:sensor $sensor ; $limit ?n }";

/// A unit of time as its seconds, by the local name QUDT and UN/CEFACT spell it under.
fn seconds_in(unit: &str) -> Option<f64> {
    match unit {
        "SEC" => Some(1.0),
        "MIN" => Some(60.0),
        "HR" | "HUR" => Some(3600.0),
        "DAY" => Some(86400.0),
        _ => None,
    }
}

fn strs(names: &[String]) -> Vec<&str> {
    names.iter().map(String::as_str).collect()
}

/// The seconds between one of `sensor`'s observations and the next, as the world states them, or None where it
/// states no frequency, several, or a unit nothing here converts.
pub fn cadence_of(store: &Store, sensor: &str) -> Result<Option<f64>, Error> {
    let common = store.graphs_of(&[BELIEF], &Within::common())?;
    let found = store.rows(&bind(CADENCE_Q, &[("sensor", Value::iri(sensor))])?, &strs(&common))?;
    if found.len() != 1 {
        if !found.is_empty() {
            log::warn!(
                "{} states {} frequencies: none is its cadence",
                local_of(sensor),
                found.len()
            );
        }
        return Ok(None);
    }
    let unit = value(&found[0], "unit");
    let Some(seconds) = seconds_in(&unit.as_deref().map_or("SEC".to_string(), local_of)) else {
        log::warn!(
            "{} states its frequency in {}, which nothing here converts",
            local_of(sensor),
            unit.unwrap_or_default()
        );
        return Ok(None);
    };
    Ok(value(&found[0], "every")
        .and_then(|v| v.parse::<f64>().ok())
        .map(|every| every * seconds))
}

/// Every sensor whose latest percept had ended by `now` — its next reading due and a grace past it, and nothing
/// arrived — with the instant it ended, earliest first. Writes nothing.
pub fn lapsed(store: &Store, now: DateTime) -> Result<Vec<(String, DateTime)>, Error> {
    let Some(cat) = store.catalogue()? else {
        return Ok(Vec::new());
    };
    let text = bind(LAPSED_Q, &[("cat", Value::iri(cat)), ("now", instant(now))])?;
    let mut out = Vec::new();
    for row in store.rows(&text, &[])? {
        if let (Some(sensor), Some(end)) = (iri(&row, "sensor"), value(&row, "end")) {
            out.push((sensor, parse_instant(&end)?));
        }
    }
    Ok(out)
}

/// The soonest instant from `now` on that a sensor's latest percept ends and its cadence lapses, where one is yet to:
/// when `lapsed` next answers anything new, so whoever asks it waits until then. Writes nothing.
pub fn next_lapse(store: &Store, now: DateTime) -> Result<Option<DateTime>, Error> {
    let Some(cat) = store.catalogue()? else {
        return Ok(None);
    };
    let text = bind(NEXT_LAPSE_Q, &[("cat", Value::iri(cat)), ("now", instant(now))])?;
    match store.rows(&text, &[])?.first().and_then(|r| value(r, "next")) {
        Some(next) => Ok(Some(parse_instant(&next)?)),
        None => Ok(None),
    }
}

/// Every sensor the agent reads: each an observer role the self plays declares (`sensing:sensor`), in its self
/// graph, sorted — whose bytes a transport hands `received`.
pub fn sensors(store: &Store) -> Result<Vec<String>, Error> {
    let selves = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
    Ok(store
        .rows(SENSORS_Q, &strs(&selves))?
        .iter()
        .filter_map(|r| iri(r, "sensor"))
        .collect())
}

/// How many cadences or readings `limit` — `sensing:silentAfter`, `sensing:stuckAfter` — allows `sensor`: the
/// figure the observer role reading it states in the self graph, or the observer shape's default where it states
/// none, several, or one that is no number, said in the log, since two answers are never picked between.
pub fn limit_of(store: &Store, sensor: &str, limit: &str) -> Result<i64, Error> {
    let selves = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
    let text = bind(LIMIT_Q, &[("sensor", Value::iri(sensor)), ("limit", Value::iri(limit))])?;
    let found: Vec<String> = store
        .rows(&text, &strs(&selves))?
        .iter()
        .filter_map(|r| value(r, "n"))
        .collect();
    if let [one] = found.as_slice()
        && let Ok(n) = one.parse::<f64>()
    {
        return Ok(n as i64);
    }
    let default = default_of(limit)?;
    if !found.is_empty() {
        let mut said = found.clone();
        said.sort();
        log::warn!(
            "the roles reading {} state {} for {}: the default, {default}, holds",
            local_of(sensor),
            said.join(", "),
            local_of(limit)
        );
    }
    Ok(default)
}

#[cfg(test)]
mod tests {
    //! How often a sensor reports, held as `agent/sensing/tests/test_cadence.py` holds it — over the pot's probe and
    //! over a board whose peripherals each state theirs in a unit of their own — and when a sensor's cadence has
    //! lapsed.

    use std::path::Path;

    use orexis::clock::seconds;
    use orexis::snapshots::{ME, now, stand_in};

    use super::*;
    use crate::received::{GRACE, received};

    const TEST: &str = "http://example.org/test#";

    fn world(name: &str) -> Store {
        stand_in(&Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/worlds").join(name))
    }

    fn probe() -> String {
        format!("{TEST}probe")
    }

    #[test]
    fn the_pots_probe_reports_every_quarter_hour() {
        assert_eq!(
            cadence_of(&world("a_pot_and_its_probe.trig"), &probe()).unwrap(),
            Some(900.0)
        );
    }

    #[test]
    fn each_peripheral_reports_as_its_frequency_says_in_its_own_unit() {
        let store = world("a_board_and_its_peripherals.trig");
        assert_eq!(
            cadence_of(&store, &format!("{TEST}thermo")).unwrap(),
            Some(120.0),
            "two of QUDT's minutes"
        );
        assert_eq!(
            cadence_of(&store, &format!("{TEST}hygro")).unwrap(),
            Some(3600.0),
            "an hour by UN/CEFACT"
        );
        assert_eq!(
            cadence_of(&store, &format!("{TEST}gauge")).unwrap(),
            Some(30.0),
            "no unit is seconds"
        );
    }

    #[test]
    fn no_frequency_or_a_unit_nothing_converts_is_no_cadence() {
        let store = world("a_board_and_its_peripherals.trig");
        assert_eq!(
            cadence_of(&store, &probe()).unwrap(),
            None,
            "the board's probe states no frequency"
        );
        assert_eq!(cadence_of(&store, &format!("{TEST}nobody")).unwrap(), None);
        assert_eq!(cadence_of(&store, &format!("{TEST}barometer")).unwrap(), None);
    }

    #[test]
    fn a_sensor_has_lapsed_when_its_latest_percept_has_ended() {
        let store = world("a_pot_and_its_probe.trig");
        received(&store, ME, &probe(), br#"{"value": 0.2}"#, now()).unwrap();
        let due = now()
            .checked_add_day_time_duration(seconds(900.0 * (1.0 + GRACE)))
            .unwrap();
        let second = |at: DateTime, by: f64| at.checked_add_day_time_duration(seconds(by)).unwrap();
        let before = due.checked_sub_day_time_duration(seconds(1.0)).unwrap();
        assert_eq!(lapsed(&store, before).unwrap(), []);
        assert_eq!(lapsed(&store, second(due, 1.0)).unwrap(), [(probe(), due)]);
        received(&store, ME, &probe(), br#"{"value": 0.21}"#, second(now(), 900.0)).unwrap();
        assert_eq!(
            lapsed(&store, second(due, 1.0)).unwrap(),
            [],
            "the second reading holds"
        );
    }

    #[test]
    fn a_sensor_stating_no_frequency_never_lapses() {
        let store = world("a_board_and_its_peripherals.trig");
        assert!(
            !received(&store, ME, &probe(), br#"{"soil": {"moisture": 0.2}}"#, now())
                .unwrap()
                .is_empty()
        );
        let month = now().checked_add_day_time_duration(seconds(30.0 * 86400.0)).unwrap();
        assert_eq!(lapsed(&store, month).unwrap(), []);
    }
}
