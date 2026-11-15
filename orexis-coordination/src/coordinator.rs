//! THE COORDINATOR: the role this package is loaded for, as a struct that reads itself: `coordination:Coordinator`, read as one struct by this package's own query
//! (knowledge/domain/kernel/role.md).

use orexis::Error;
use orexis::ontology::SELF_GRAPH;
use orexis::store::{Store, Within};

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("coordination", include_str!("../ontology.ttl")));

/// WHAT THE ROLES THE SELF PLAYS SAY OF IT, a row per role, in the agent's self graph.
const SAID_Q: &str = "SELECT ?patienceS ?rounds ?lookahead WHERE { ?me a orexis:Self ; orexis:plays ?role . \
OPTIONAL { ?role <http://example.org/orexis/coordination#patienceS> ?patienceS } \
OPTIONAL { ?role <http://example.org/orexis/coordination#rounds> ?rounds } \
OPTIONAL { ?role <http://example.org/orexis/coordination#lookahead> ?lookahead } }";

/// THE COORDINATOR THE SELF PLAYS, AS THIS PACKAGE READS IT: a field for each thing the role may state, one to one. A
/// figure no role states is the default this ontology states.
#[derive(Debug, Clone, PartialEq)]
pub struct Coordinator {
    /// How many seconds a draw may stand undecided, and a question holds (`coordination:patienceS`).
    pub patience_s: f64,
    /// How many rounds a draw may restart before the peer is taken as silent (`coordination:rounds`).
    pub rounds: f64,
    /// How many of a silent peer's steps are foreseen (`coordination:lookahead`).
    pub lookahead: i64,
}

impl Coordinator {
    /// The coordinator the self plays, as the agent's documents state it, read by this package's own query.
    pub fn new(store: &Store) -> Result<Self, Error> {
        let known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = store.rows(SAID_Q, &known)?;
        Ok(Coordinator {
            patience_s: DEFAULTS.said(&rows, "patienceS", crate::ontology::PATIENCE_S)?,
            rounds: DEFAULTS.said(&rows, "rounds", crate::ontology::ROUNDS)?,
            lookahead: DEFAULTS.said(&rows, "lookahead", crate::ontology::LOOKAHEAD)? as i64,
        })
    }
}
