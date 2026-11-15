//! THE ROLE THIS PACKAGE IS LOADED FOR, AND WHAT IT SAYS: `belief:Deliberator`, read as one struct by this package's own query
//! (knowledge/domain/kernel/role.md).

use orexis::Error;
use orexis::ontology::SELF_GRAPH;
use orexis::store::{Store, Within};

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
pub const ROLE: &str = "http://example.org/orexis/belief#Deliberator";

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("belief", include_str!("../ontology.ttl")));

/// WHAT THE ROLES THE SELF PLAYS SAY OF IT, a row per role, in the agent's self graph.
const SAID_Q: &str = "SELECT ?budget WHERE { ?me a orexis:Self ; orexis:plays ?role . \
OPTIONAL { ?role <http://example.org/orexis/belief#budget> ?budget } }";

/// WHAT THIS PACKAGE'S ROLE SAYS, AS THE PACKAGE READS IT: a field for each thing the role may state, one to one. A
/// figure no role states is the default this ontology states.
#[derive(Debug, Clone, PartialEq)]
pub struct Role {
    /// How many rule executions one pass of revision may spend (`belief:budget`).
    pub budget: usize,
}

impl Role {
    /// The role as the agent's documents state it, read by this package's own query.
    pub fn read(store: &Store) -> Result<Self, Error> {
        let known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = store.rows(SAID_Q, &known)?;
        Ok(Role {
            budget: DEFAULTS.said(&rows, "budget", crate::ontology::BUDGET_TERM)? as usize,
        })
    }
}
