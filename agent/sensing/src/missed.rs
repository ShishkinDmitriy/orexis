//! WHICH SENSORS HAVE GONE SILENT AT AN INSTANT, as `agent/sensing/missed.py` answers it — asked every minute of the
//! timeline by sensing's own part.
//!
//! **A READING IS MISSING WHEN THE LATEST PERCEPT'S PERIOD HAS ENDED** (`cadence::lapsed`), later than due, since a
//! reading a little late is not missing (#870). **A SENSOR SILENT PAST THE LIMIT IS ANSWERED, AND KEPT BY THE
//! ASKER**: one whose reading has been missing for `sensing:silentAfter` cadences and more is silent since the
//! instant its latest percept ended; this writes nothing, and sensing's part keeps each silence the first ask finds.
//! **A SENSOR THAT HAS NEVER REPORTED IS NOT HERE**: its absence is the container's to count from boot.

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::clock::microseconds;

use crate::cadence::{cadence_of, lapsed, limit_of};
use crate::ontology::SILENT_AFTER_TERM;

/// The sensors silent at `now` — the latest percept ended and the limit of cadences the observer role reading it
/// allows gone since — each with the instant it fell silent, earliest first. A sensor stating no frequency is never
/// silent. Writes nothing.
pub fn missed(store: &orexis::store::Store, now: DateTime) -> Result<Vec<(String, DateTime)>, Error> {
    let mut out: Vec<(String, DateTime)> = Vec::new();
    for (sensor, since) in lapsed(store, now)? {
        if out.iter().any(|(s, _)| *s == sensor) {
            continue;
        }
        let Some(cadence) = cadence_of(store, &sensor)? else {
            continue;
        };
        let limit = limit_of(store, &sensor, SILENT_AFTER_TERM)?;
        if let Some(silent) = since.checked_add_day_time_duration(microseconds(limit as f64 * cadence))
            && now >= silent
        {
            out.push((sensor, since));
        }
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    //! `missed`, held as `agent/sensing/tests/test_missed.py` holds it, over the world: nothing is silent while the
    //! reading stands, nor while it is late inside its grace (#870), a lapsed reading is not yet a silence, a sensor
    //! past the limit is silent since its latest percept ended and stays so, a reading ends the silence, a sensor
    //! stating no frequency is never silent, the limit is the observer role's, and no ask writes anything.

    use std::path::Path;

    use orexis::bind::{Value, bind};
    use orexis::clock::seconds;
    use orexis::snapshots::{ME, now, stand_in};
    use orexis::store::{Store, Within, value};

    use super::*;
    use crate::ontology::{OBSERVATION_GRAPH, default_of};
    use crate::received::{GRACE, received};

    const PROBE: &str = "http://example.org/test#probe";
    const CADENCE: f64 = 900.0;

    fn plus(at: DateTime, by: f64) -> DateTime {
        if by >= 0.0 {
            at.checked_add_day_time_duration(seconds(by)).unwrap()
        } else {
            at.checked_sub_day_time_duration(seconds(-by)).unwrap()
        }
    }

    fn silent_after() -> f64 {
        default_of(SILENT_AFTER_TERM).unwrap() as f64
    }

    fn lapse() -> f64 {
        CADENCE * (1.0 + GRACE)
    }

    fn world(name: &str) -> Store {
        stand_in(&Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/worlds").join(name))
    }

    fn pot() -> Store {
        let store = world("a_pot_and_its_probe.trig");
        received(&store, ME, PROBE, br#"{"value": 0.2}"#, now()).unwrap();
        store
    }

    #[test]
    fn nothing_is_silent_while_the_reading_stands() {
        assert_eq!(missed(&pot(), plus(now(), 600.0)).unwrap(), []);
    }

    #[test]
    fn a_reading_late_inside_its_grace_is_still_the_present() {
        let store = pot();
        let late = plus(now(), CADENCE + 60.0);
        assert_eq!(lapsed(&store, late).unwrap(), []);
        assert_eq!(missed(&store, late).unwrap(), []);
        let within = Within {
            at: Some(late),
            now: Some(late),
            ..Within::default()
        };
        let holding = store.graphs_of(&[OBSERVATION_GRAPH], &within).unwrap();
        let holding: Vec<&str> = holding.iter().map(String::as_str).collect();
        let found = store
            .rows("SELECT ?v WHERE { ?o sensing:rawResult ?v }", &holding)
            .unwrap();
        assert_eq!(found.iter().filter_map(|r| value(r, "v")).collect::<Vec<_>>(), ["0.2"]);
    }

    #[test]
    fn a_percept_followed_by_the_next_is_not_missing() {
        let store = pot();
        received(&store, ME, PROBE, br#"{"value": 0.21}"#, plus(now(), CADENCE)).unwrap();
        assert_eq!(lapsed(&store, plus(now(), CADENCE + 600.0)).unwrap(), []);
    }

    #[test]
    fn a_lapsed_reading_is_missing_and_not_yet_silent() {
        let store = pot();
        let at = plus(now(), lapse() + 60.0);
        assert_eq!(lapsed(&store, at).unwrap(), [(PROBE.to_string(), plus(now(), lapse()))]);
        assert_eq!(missed(&store, at).unwrap(), []);
    }

    #[test]
    fn a_sensor_past_the_limit_is_silent_since_its_latest_percept_ended() {
        let store = pot();
        let fell_due = plus(now(), lapse());
        let late = plus(fell_due, CADENCE * silent_after());
        assert_eq!(missed(&store, plus(late, -1.0)).unwrap(), []);
        assert_eq!(missed(&store, late).unwrap(), [(PROBE.to_string(), fell_due)]);
        assert_eq!(
            missed(&store, plus(late, 3600.0)).unwrap(),
            [(PROBE.to_string(), fell_due)],
            "and stays so"
        );
    }

    #[test]
    fn asking_writes_nothing() {
        let store = pot();
        let before = store.len().unwrap();
        assert!(
            !missed(&store, plus(now(), lapse() + CADENCE * silent_after()))
                .unwrap()
                .is_empty()
        );
        assert_eq!(store.len().unwrap(), before);
    }

    #[test]
    fn a_reading_ends_the_silence() {
        let store = pot();
        let late = plus(now(), lapse() + CADENCE * silent_after());
        assert!(!missed(&store, late).unwrap().is_empty());
        received(&store, ME, PROBE, br#"{"value": 0.2}"#, late).unwrap();
        assert_eq!(missed(&store, plus(late, 60.0)).unwrap(), []);
    }

    #[test]
    fn a_sensor_stating_no_frequency_is_never_silent() {
        let store = world("a_board_and_its_peripherals.trig");
        assert!(
            !received(&store, ME, PROBE, br#"{"soil": {"moisture": 0.2}}"#, now())
                .unwrap()
                .is_empty()
        );
        let month = plus(now(), 30.0 * 86400.0);
        assert_eq!(lapsed(&store, month).unwrap(), []);
        assert_eq!(missed(&store, month).unwrap(), []);
    }

    #[test]
    fn the_silence_limit_is_the_observer_roles_where_it_states_one() {
        let store = pot();
        store
            .update(
                &bind(
                    "INSERT DATA { GRAPH <http://example.org/test#world> {
  $me orexis:plays [ a sensing:Observer ; sensing:sensor $probe ; sensing:silentAfter 1 ] } }",
                    &[("me", Value::iri(ME)), ("probe", Value::iri(PROBE))],
                )
                .unwrap(),
            )
            .unwrap();
        let fell_due = plus(now(), lapse());
        assert_eq!(
            missed(&store, plus(fell_due, CADENCE)).unwrap(),
            [],
            "a common belief is not the keeper's role"
        );
        crate::received::tests::observing(&store, PROBE, &[(SILENT_AFTER_TERM, 1)]);
        assert_eq!(missed(&store, plus(fell_due, CADENCE - 1.0)).unwrap(), []);
        assert_eq!(
            missed(&store, plus(fell_due, CADENCE)).unwrap(),
            [(PROBE.to_string(), fell_due)]
        );
    }
}
