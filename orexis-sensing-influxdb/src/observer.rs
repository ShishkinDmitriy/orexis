//! THE OBSERVER: the role this package keeps house for, as a struct that reads itself for what it says of archiving: `sensing:Observer`, read as one struct by this
//! package's own query (knowledge/domain/kernel/role.md).

use orexis::Error;
use orexis::ontology::{DEPLOYMENT, SELF_GRAPH};
use orexis::store::{Store, Within, value};

/// WHAT HOLDS WHERE NO ROLE STATES A FIGURE: the defaults sensing's ontology states, the words being sensing's.
pub use orexis_sensing::observer::DEFAULTS;

/// How often readings are archived: a figure the observer's role states.
pub const ARCHIVED_EVERY_S: &str = "http://example.org/orexis/sensing#archivedEveryS";

/// WHAT THE ROLES THE SELF PLAYS SAY OF IT, a row per role, in the agent's self graph, with where each service a role
/// names answers, as the world's deployment states it.
const SAID_Q: &str = "SELECT ?archivedEveryS ?archive WHERE { ?me a orexis:Self ; orexis:plays ?role . \
OPTIONAL { ?role <http://example.org/orexis/sensing#archivedEveryS> ?archivedEveryS } \
OPTIONAL { ?role <http://example.org/orexis/sensing#archivedIn> ?archiveNamed . ?archiveNamed <https://schema.org/url> ?archive } }";

/// THE OBSERVER THE SELF PLAYS, AS THIS PACKAGE READS IT: a field for each thing the role may state, one to one. A
/// figure no role states is the default this ontology states, and a link is where the service the role names answers,
/// none where the role names none or the world says nothing of the one named.
#[derive(Debug, Clone, PartialEq)]
pub struct Observer {
    /// How often readings are archived, in the agent's seconds (`sensing:archivedEveryS`).
    pub archived_every_s: f64,
    /// Where the series store the role names answers (`sensing:archivedIn`).
    pub archive: Option<String>,
}

impl Observer {
    /// The observer the self plays, as the agent's documents state it, read by this package's own query.
    pub fn new(store: &Store) -> Result<Self, Error> {
        let mut known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        known.extend(store.graphs_of(&[DEPLOYMENT], &Within::common())?);
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = store.rows(SAID_Q, &known)?;
        Ok(Observer {
            archived_every_s: DEFAULTS.said(&rows, "archivedEveryS", ARCHIVED_EVERY_S)?,
            archive: rows
                .iter()
                .find_map(|row| value(row, "archive"))
                .filter(|url| !url.is_empty()),
        })
    }
}
