//! THE RANGES THAT APPLY TO WHAT A SENSOR OBSERVES, in SSN-System's words, as `agent/prediction/ranges.py` reads
//! them: stated by what hosts the sensor, by what that host is a sample of, or by the sensor itself — an operating or
//! a survival range whose condition is for the property — answered together as their two numbers.

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::BELIEF;
use orexis::store::{Store, Within, value};

const BOUNDS_Q: &str = "
SELECT DISTINCT ?low ?high WHERE {
  $sensor (sosa:isHostedBy/(sosa:isSampleOf)?)? ?holder .
  ?holder ssn-system:hasOperatingRange|ssn-system:hasSurvivalRange ?range .
  ?range ssn-system:inCondition ?condition .
  ?condition ssn:forProperty $property ; schema:minValue ?low ; schema:maxValue ?high }
ORDER BY ?low ?high";

/// The floor and the ceiling of every range that applies to what `sensor` observes of `property`, off what the
/// world states.
pub fn ranges_of(store: &Store, sensor: &str, property: &str) -> Result<Vec<(f64, f64)>, Error> {
    let common = store.graphs_of(&[BELIEF], &Within::common())?;
    let common: Vec<&str> = common.iter().map(String::as_str).collect();
    let text = bind(
        BOUNDS_Q,
        &[("sensor", Value::iri(sensor)), ("property", Value::iri(property))],
    )?;
    Ok(store
        .rows(&text, &common)?
        .iter()
        .filter_map(|r| {
            let low = value(r, "low")?.parse().ok()?;
            let high = value(r, "high")?.parse().ok()?;
            Some((low, high))
        })
        .collect())
}

/// Which side of a range a number lies on: -1 under the floor, 0 inside, bounds included, +1 over the ceiling.
pub fn side(low: f64, high: f64, value: f64) -> i32 {
    if value < low {
        -1
    } else if value > high {
        1
    } else {
        0
    }
}

#[cfg(test)]
mod tests {
    //! The ranges, held as `agent/prediction/tests/test_ranges.py` holds them: its host's, its host's subject's where
    //! the host is a sample, and its own.

    use std::path::Path;

    use orexis::snapshots::stand_in;

    use super::*;

    const TEST: &str = "http://example.org/test#";
    /// The probe's own operating range, the pot's survival range, the pot's operating range.
    const BOUNDS: [(f64, f64); 3] = [(0.0, 1.0), (0.02, 0.45), (0.1, 0.3)];

    fn world(name: &str) -> Store {
        stand_in(&Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/worlds").join(name))
    }

    #[test]
    fn the_hosts_and_the_sensors_own_bounds_for_the_property() {
        let store = world("a_pot_and_its_probe.trig");
        let probe = format!("{TEST}probe");
        assert_eq!(ranges_of(&store, &probe, &format!("{TEST}moisture")).unwrap(), BOUNDS);
        assert_eq!(ranges_of(&store, &probe, &format!("{TEST}warmth")).unwrap(), []);
        assert_eq!(
            ranges_of(&store, &format!("{TEST}nobody"), &format!("{TEST}moisture")).unwrap(),
            []
        );
    }

    #[test]
    fn a_sensor_in_a_sample_gets_the_subjects_ranges() {
        let store = world("a_probe_in_a_patch.trig");
        assert_eq!(
            ranges_of(&store, &format!("{TEST}probe"), &format!("{TEST}moisture")).unwrap(),
            BOUNDS
        );
    }

    #[test]
    fn a_side_is_inclusive_at_the_bounds() {
        let sides: Vec<i32> = [0.05, 0.1, 0.2, 0.3, 0.31].iter().map(|v| side(0.1, 0.3, *v)).collect();
        assert_eq!(sides, [-1, 0, 0, 0, 1]);
    }
}
