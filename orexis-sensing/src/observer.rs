//! THE OBSERVER: the role this package is loaded for, as a struct that reads itself: `sensing:Observer`, read as one struct by this package's own query
//! (knowledge/domain/kernel/role.md). The sensors a role reads and its two limits are read per sensor, by `cadence`.

use orexis::Error;
use orexis::ontology::SELF_GRAPH;
use orexis::store::{Store, Within};

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("sensing", include_str!("../ontology.ttl")));

/// WHAT THE ROLES THE SELF PLAYS SAY OF IT, a row per role, in the agent's self graph.
const SAID_Q: &str = "SELECT ?askedEveryS WHERE { ?me a orexis:Self ; orexis:plays ?role . \
OPTIONAL { ?role <http://example.org/orexis/sensing#askedEveryS> ?askedEveryS } }";

/// THE OBSERVER THE SELF PLAYS, AS THIS PACKAGE READS IT: a field for each thing the role may state, one to one. A
/// figure no role states is the default this ontology states.
#[derive(Debug, Clone, PartialEq)]
pub struct Observer {
    /// How often sensing asks which sensors have fallen due or gone silent, in the agent's seconds (`sensing:askedEveryS`).
    pub asked_every_s: f64,
}

impl Observer {
    /// The observer the self plays, as the agent's documents state it, read by this package's own query.
    pub fn new(store: &Store) -> Result<Self, Error> {
        let known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = store.rows(SAID_Q, &known)?;
        Ok(Observer {
            asked_every_s: DEFAULTS.said(&rows, "askedEveryS", crate::ontology::ASKED_EVERY_S_TERM)?,
        })
    }
}

/// What holds of `limit` — `sensing:silentAfter`, `sensing:stuckAfter` — where no observer role states it: the
/// observer shape's `sh:defaultValue`, read off this layer's ontology. Refused where the ontology states none or
/// several, since a limit with no figure is a package shipped broken.
pub fn default_of(limit: &str) -> Result<i64, Error> {
    Ok(DEFAULTS.figure(limit)? as i64)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ontology::{SENSING, SILENT_AFTER_TERM, STUCK_AFTER_TERM};

    #[test]
    fn the_observer_shape_states_one_default_of_each_limit() {
        assert_eq!(default_of(SILENT_AFTER_TERM).unwrap(), 3);
        assert_eq!(default_of(STUCK_AFTER_TERM).unwrap(), 6);
        assert!(default_of(&format!("{SENSING}nothing")).is_err());
    }
}
