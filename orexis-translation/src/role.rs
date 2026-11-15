//! THE ROLE THIS PACKAGE IS LOADED FOR, AND WHAT IT SAYS: `translation:Translator`, read as one struct by this package's own query
//! (knowledge/domain/kernel/role.md).

use orexis::Error;
use orexis::ontology::{DEPLOYMENT, SELF_GRAPH};
use orexis::store::{Store, Within, value};

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
pub const ROLE: &str = "http://example.org/orexis/translation#Translator";

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("translation", include_str!("../ontology.ttl")));

/// THE FIGURES A TRANSLATOR'S ROLE MAY STATE, each its own word.
pub const TURNS: &str = "http://example.org/orexis/translation#turns";
/// How many rows one read hands the model.
pub const ROWS: &str = "http://example.org/orexis/translation#rows";
/// How long the model's call waits for the agent.
pub const ANSWERED_WITHIN_S: &str = "http://example.org/orexis/translation#answeredWithinS";
/// How long one call of the model may take.
pub const CALLED_WITHIN_S: &str = "http://example.org/orexis/translation#calledWithinS";
/// How often a failing model is asked again.
pub const RETRIES: &str = "http://example.org/orexis/translation#retries";

/// WHAT THE ROLES THE SELF PLAYS SAY OF IT, a row per role, in the agent's self graph, with where each service a role
/// names answers, as the world's deployment states it.
const SAID_Q: &str = "SELECT ?turns ?rows ?answeredWithinS ?calledWithinS ?retries ?model WHERE { ?me a orexis:Self ; orexis:plays ?role . \
OPTIONAL { ?role <http://example.org/orexis/translation#turns> ?turns } \
OPTIONAL { ?role <http://example.org/orexis/translation#rows> ?rows } \
OPTIONAL { ?role <http://example.org/orexis/translation#answeredWithinS> ?answeredWithinS } \
OPTIONAL { ?role <http://example.org/orexis/translation#calledWithinS> ?calledWithinS } \
OPTIONAL { ?role <http://example.org/orexis/translation#retries> ?retries } \
OPTIONAL { ?role <http://example.org/orexis/translation#translatedBy> ?modelNamed . ?modelNamed <https://schema.org/url> ?model } }";

/// WHAT THIS PACKAGE'S ROLE SAYS, AS THE PACKAGE READS IT: a field for each thing the role may state, one to one. A
/// figure no role states is the default this ontology states, and a link is where the service the role names answers,
/// none where the role names none or the world says nothing of the one named.
#[derive(Debug, Clone, PartialEq)]
pub struct Role {
    /// How many turns one conversation with the model may take (`translation:turns`).
    pub turns: usize,
    /// How many rows one read hands the model (`translation:rows`).
    pub rows: usize,
    /// How long the model's call waits for the agent to hold a statement to its bounds, in real seconds (`translation:answeredWithinS`).
    pub answered_within_s: f64,
    /// How long one call of the model may take, in real seconds (`translation:calledWithinS`).
    pub called_within_s: f64,
    /// How often a failing model is asked again (`translation:retries`).
    pub retries: u32,
    /// Where the model the role names answers (`translation:translatedBy`).
    pub model: Option<String>,
}

impl Role {
    /// The role as the agent's documents state it, read by this package's own query.
    pub fn read(store: &Store) -> Result<Self, Error> {
        let mut known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        known.extend(store.graphs_of(&[DEPLOYMENT], &Within::common())?);
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = store.rows(SAID_Q, &known)?;
        Ok(Role {
            turns: DEFAULTS.said(&rows, "turns", TURNS)? as usize,
            rows: DEFAULTS.said(&rows, "rows", ROWS)? as usize,
            answered_within_s: DEFAULTS.said(&rows, "answeredWithinS", ANSWERED_WITHIN_S)?,
            called_within_s: DEFAULTS.said(&rows, "calledWithinS", CALLED_WITHIN_S)?,
            retries: DEFAULTS.said(&rows, "retries", RETRIES)? as u32,
            model: rows
                .iter()
                .find_map(|row| value(row, "model"))
                .filter(|url| !url.is_empty()),
        })
    }
}
