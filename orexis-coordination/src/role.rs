//! THE ROLE THIS PACKAGE IS LOADED FOR, AND WHAT IT SAYS: `coordination:Coordinator`, read as one struct by this package's own query
//! (knowledge/domain/kernel/role.md).

use orexis::Error;
use orexis::ontology::SELF_GRAPH;
use orexis::store::{Store, Within};

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
pub const ROLE: &str = "http://example.org/orexis/coordination#Coordinator";

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("coordination", include_str!("../ontology.ttl")));

/// WHAT THE ROLES THE SELF PLAYS SAY OF IT, a row per role, in the agent's self graph.
const SAID_Q: &str = "SELECT ?patienceS ?rounds ?lookahead WHERE { ?me a orexis:Self ; orexis:plays ?role . \
OPTIONAL { ?role <http://example.org/orexis/coordination#patienceS> ?patienceS } \
OPTIONAL { ?role <http://example.org/orexis/coordination#rounds> ?rounds } \
OPTIONAL { ?role <http://example.org/orexis/coordination#lookahead> ?lookahead } }";

/// WHAT THIS PACKAGE'S ROLE SAYS, AS THE PACKAGE READS IT: a field for each thing the role may state, one to one. A
/// figure no role states is the default this ontology states.
#[derive(Debug, Clone, PartialEq)]
pub struct Role {
    /// How many seconds a draw may stand undecided, and a question holds (`coordination:patienceS`).
    pub patience_s: f64,
    /// How many rounds a draw may restart before the peer is taken as silent (`coordination:rounds`).
    pub rounds: f64,
    /// How many of a silent peer's steps are foreseen (`coordination:lookahead`).
    pub lookahead: i64,
}

impl Role {
    /// The role as the agent's documents state it, read by this package's own query.
    pub fn read(store: &Store) -> Result<Self, Error> {
        let known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = store.rows(SAID_Q, &known)?;
        Ok(Role {
            patience_s: DEFAULTS.said(&rows, "patienceS", crate::ontology::PATIENCE_S)?,
            rounds: DEFAULTS.said(&rows, "rounds", crate::ontology::ROUNDS)?,
            lookahead: DEFAULTS.said(&rows, "lookahead", crate::ontology::LOOKAHEAD)? as i64,
        })
    }
}
