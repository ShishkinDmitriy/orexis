//! WHAT A ROLE THE SELF PLAYS SAYS OF THIS TRANSPORT, read as one struct by this package's own query
//! (knowledge/domain/kernel/role.md). The MQTT member is loaded for no role of its own: it joins where the world wires the
//! agent through it (`create`).

use orexis::Error;
use orexis::ontology::SELF_GRAPH;
use orexis::store::{Store, Within};

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("the mqtt transport", include_str!("../ontology.ttl")));

/// How soon a silent board is told again: a figure a role states.
pub const ASKED_AGAIN_AFTER_S: &str = "http://example.org/orexis/mqtt#askedAgainAfterS";

/// WHAT THE ROLES THE SELF PLAYS SAY OF IT, a row per role, in the agent's self graph.
const SAID_Q: &str = "SELECT ?askedAgainAfterS WHERE { ?me a orexis:Self ; orexis:plays ?role . \
OPTIONAL { ?role <http://example.org/orexis/mqtt#askedAgainAfterS> ?askedAgainAfterS } }";

/// WHAT THIS PACKAGE'S ROLE SAYS, AS THE PACKAGE READS IT: a field for each thing the role may state, one to one. A
/// figure no role states is the default this ontology states.
#[derive(Debug, Clone, PartialEq)]
pub struct Role {
    /// How soon a board told to sense that sent no reading is told again, in the agent's seconds (`mqtt:askedAgainAfterS`).
    pub asked_again_after_s: f64,
}

impl Role {
    /// The role as the agent's documents state it, read by this package's own query.
    pub fn read(store: &Store) -> Result<Self, Error> {
        let known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = store.rows(SAID_Q, &known)?;
        Ok(Role {
            asked_again_after_s: DEFAULTS.said(&rows, "askedAgainAfterS", ASKED_AGAIN_AFTER_S)?,
        })
    }
}
