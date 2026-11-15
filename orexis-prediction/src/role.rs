//! THE ROLE THIS PACKAGE IS LOADED FOR, AND WHAT IT SAYS: `prediction:Predictor`, read as one struct by this package's own query
//! (knowledge/domain/kernel/role.md).

use orexis::Error;
use orexis::ontology::SELF_GRAPH;
use orexis::store::{Store, Within};

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
pub const ROLE: &str = "http://example.org/orexis/prediction#Predictor";

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("prediction", include_str!("../ontology.ttl")));

/// WHAT THE ROLES THE SELF PLAYS SAY OF IT, a row per role, in the agent's self graph.
const SAID_Q: &str = "SELECT ?horizonS ?rateHeldS WHERE { ?me a orexis:Self ; orexis:plays ?role . \
OPTIONAL { ?role <http://example.org/orexis/prediction#horizonS> ?horizonS } \
OPTIONAL { ?role <http://example.org/orexis/prediction#rateHeldS> ?rateHeldS } }";

/// WHAT THIS PACKAGE'S ROLE SAYS, AS THE PACKAGE READS IT: a field for each thing the role may state, one to one. A
/// figure no role states is the default this ontology states.
#[derive(Debug, Clone, PartialEq)]
pub struct Role {
    /// How far past an observation the flows are integrated, in seconds (`prediction:horizonS`).
    pub horizon_s: f64,
    /// The longest a rate is held before the flows are asked again, in seconds (`prediction:rateHeldS`).
    pub rate_held_s: f64,
}

impl Role {
    /// The role as the agent's documents state it, read by this package's own query.
    pub fn read(store: &Store) -> Result<Self, Error> {
        let known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = store.rows(SAID_Q, &known)?;
        Ok(Role {
            horizon_s: DEFAULTS.said(&rows, "horizonS", crate::ontology::HORIZON_TERM)?,
            rate_held_s: DEFAULTS.said(&rows, "rateHeldS", crate::ontology::RATE_HELD_TERM)?,
        })
    }
}
