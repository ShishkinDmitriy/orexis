//! THE ROLE THIS PACKAGE IS LOADED FOR, AND WHAT IT SAYS: `planning:Planner`, read as one struct by this package's own query
//! (knowledge/domain/kernel/role.md).

use orexis::Error;
use orexis::ontology::SELF_GRAPH;
use orexis::store::{Store, Within};

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
pub const ROLE: &str = "http://example.org/orexis/planning#Planner";

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("planning", include_str!("../ontology.ttl")));

/// WHAT THE ROLES THE SELF PLAYS SAY OF IT, a row per role, in the agent's self graph.
const SAID_Q: &str = "SELECT ?budget ?budgetEveryS WHERE { ?me a orexis:Self ; orexis:plays ?role . \
OPTIONAL { ?role <http://example.org/orexis/planning#budget> ?budget } \
OPTIONAL { ?role <http://example.org/orexis/planning#budgetEveryS> ?budgetEveryS } }";

/// WHAT THIS PACKAGE'S ROLE SAYS, AS THE PACKAGE READS IT: a field for each thing the role may state, one to one. A
/// figure no role states is the default this ontology states.
#[derive(Debug, Clone, PartialEq)]
pub struct Role {
    /// How many candidates one want's search may weigh in one planning (`planning:budget`).
    pub budget: usize,
    /// How long a budget is for, in the agent's seconds (`planning:budgetEveryS`).
    pub budget_every_s: f64,
}

impl Role {
    /// The role as the agent's documents state it, read by this package's own query.
    pub fn read(store: &Store) -> Result<Self, Error> {
        let known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = store.rows(SAID_Q, &known)?;
        Ok(Role {
            budget: DEFAULTS.said(&rows, "budget", crate::ontology::BUDGET_TERM)? as usize,
            budget_every_s: DEFAULTS.said(&rows, "budgetEveryS", crate::ontology::BUDGET_EVERY_TERM)?,
        })
    }
}
