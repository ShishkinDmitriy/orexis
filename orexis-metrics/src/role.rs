//! THE ROLE THIS PACKAGE IS LOADED FOR, AND WHAT IT SAYS: `metrics:Meter`, read as one struct by this package's own query
//! (knowledge/domain/kernel/role.md).

use orexis::Error;
use orexis::ontology::{DEPLOYMENT, SELF_GRAPH};
use orexis::store::{Store, Within, value};

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
pub const ROLE: &str = "http://example.org/orexis/metrics#Meter";

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("metrics", include_str!("../ontology.ttl")));

/// How long a window is: a figure the meter's role states.
pub const WINDOW_S: &str = "http://example.org/orexis/metrics#windowS";

/// WHAT THE ROLES THE SELF PLAYS SAY OF IT, a row per role, in the agent's self graph, with where each service a role
/// names answers, as the world's deployment states it.
const SAID_Q: &str = "SELECT ?windowS ?store WHERE { ?me a orexis:Self ; orexis:plays ?role . \
OPTIONAL { ?role <http://example.org/orexis/metrics#windowS> ?windowS } \
OPTIONAL { ?role <http://example.org/orexis/metrics#writtenTo> ?storeNamed . ?storeNamed <https://schema.org/url> ?store } }";

/// WHAT THIS PACKAGE'S ROLE SAYS, AS THE PACKAGE READS IT: a field for each thing the role may state, one to one. A
/// figure no role states is the default this ontology states, and a link is where the service the role names answers,
/// none where the role names none or the world says nothing of the one named.
#[derive(Debug, Clone, PartialEq)]
pub struct Role {
    /// How long a window is, in real seconds (`metrics:windowS`).
    pub window_s: f64,
    /// Where the series store the role names answers (`metrics:writtenTo`).
    pub written_to: Option<String>,
}

impl Role {
    /// The role as the agent's documents state it, read by this package's own query.
    pub fn read(store: &Store) -> Result<Self, Error> {
        let mut known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        known.extend(store.graphs_of(&[DEPLOYMENT], &Within::common())?);
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = store.rows(SAID_Q, &known)?;
        Ok(Role {
            window_s: DEFAULTS.said(&rows, "windowS", WINDOW_S)?,
            written_to: rows
                .iter()
                .find_map(|row| value(row, "store"))
                .filter(|url| !url.is_empty()),
        })
    }
}
