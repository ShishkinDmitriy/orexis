//! THE RECORDER: the role this package is loaded for, as a struct that reads itself: `journal:Recorder`, read as one struct by this package's own query
//! (knowledge/domain/kernel/role.md). What ships the journal's activities and what archives it read it here too.

use std::collections::BTreeSet;
use std::path::PathBuf;

use orexis::Error;
use orexis::ontology::{DEPLOYMENT, SELF_GRAPH};
use orexis::store::{Store, Within, value};

/// WHAT HOLDS WHERE NO ROLE THE SELF PLAYS STATES A FIGURE: the defaults this package's ontology states
/// (`sh:defaultValue`), the one place each lives.
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("the journal", include_str!("../ontology.ttl")));

/// How long the log and the activities no incident kept are kept: a figure the recorder's role states.
pub const WINDOW_S: &str = "http://example.org/orexis/journal#windowS";
/// From which level a line of the log is an incident: a word the recorder's role states.
pub const INCIDENT_FROM: &str = "http://example.org/orexis/journal#incidentFrom";
/// How often what lasts is taken to the archive: a figure the recorder's role states.
pub const ARCHIVED_EVERY_S: &str = "http://example.org/orexis/journal#archivedEveryS";
/// How often the activities are shipped: a figure the recorder's role states.
pub const TRACED_EVERY_S: &str = "http://example.org/orexis/journal#tracedEveryS";

/// WHAT THE ROLES THE SELF PLAYS SAY OF IT, a row per role and per incident a role adds, in the agent's self graph,
/// with where each service a role names answers, as the world's deployment states it.
const SAID_Q: &str = "SELECT ?windowS ?incidentFrom ?incident ?archivedEveryS ?tracedEveryS ?endpoint ?archive ?tracer WHERE { \
?me a orexis:Self ; orexis:plays ?role . \
OPTIONAL { ?role <http://example.org/orexis/journal#windowS> ?windowS } \
OPTIONAL { ?role <http://example.org/orexis/journal#incidentFrom> ?incidentFrom } \
OPTIONAL { ?role <http://example.org/orexis/journal#incident> ?incident } \
OPTIONAL { ?role <http://example.org/orexis/journal#archivedEveryS> ?archivedEveryS } \
OPTIONAL { ?role <http://example.org/orexis/journal#tracedEveryS> ?tracedEveryS } \
OPTIONAL { ?role <http://example.org/orexis/journal#servedAt> ?endpointNamed . ?endpointNamed <https://schema.org/url> ?endpoint } \
OPTIONAL { ?role <http://example.org/orexis/journal#archivedIn> ?archiveNamed . ?archiveNamed <https://schema.org/url> ?archive } \
OPTIONAL { ?role <http://example.org/orexis/journal#tracedBy> ?tracerNamed . ?tracerNamed <https://schema.org/url> ?tracer } }";

/// THE RECORDER THE SELF PLAYS, AS THIS PACKAGE READS IT: a field for each thing the role may state, one to one. A
/// figure or a word no role states is the default this ontology states, and a link is where the service the role
/// names answers, none where the role names none or the world says nothing of the one named.
#[derive(Debug, Clone, PartialEq)]
pub struct Recorder {
    /// How long the log and the activities no incident kept are kept, in the agent's seconds (`journal:windowS`).
    pub window_s: f64,
    /// From which level a line of the log is an incident (`journal:incidentFrom`).
    pub incident_level: log::Level,
    /// The classes that are incidents beside the vocabulary's (`journal:incident`).
    pub incidents: BTreeSet<String>,
    /// How often what lasts is taken to the archive, in the agent's seconds (`journal:archivedEveryS`).
    pub archived_every_s: f64,
    /// How often the activities are shipped, in the agent's seconds (`journal:tracedEveryS`).
    pub traced_every_s: f64,
    /// Where the journal is served, the port of its endpoint (`journal:servedAt`).
    pub endpoint: Option<u16>,
    /// Where what lasts is archived, the path of its archive (`journal:archivedIn`).
    pub archive: Option<PathBuf>,
    /// Where the activities are shipped, the url of its tracer (`journal:tracedBy`).
    pub tracer: Option<String>,
}

impl Recorder {
    /// The recorder the self plays, as the agent's documents state it, read by this package's own query.
    pub fn new(store: &Store) -> Result<Self, Error> {
        let mut known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        known.extend(store.graphs_of(&[DEPLOYMENT], &Within::common())?);
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = store.rows(SAID_Q, &known)?;
        let named = |what: &str| {
            rows.iter()
                .find_map(|row| value(row, what))
                .filter(|url| !url.is_empty())
        };
        let from = match named("incidentFrom") {
            Some(level) => level,
            None => DEFAULTS.word(INCIDENT_FROM)?,
        };
        Ok(Recorder {
            window_s: DEFAULTS.said(&rows, "windowS", WINDOW_S)?,
            incident_level: crate::journal::incident_level(Some(&from)),
            incidents: rows.iter().filter_map(|row| value(row, "incident")).collect(),
            archived_every_s: DEFAULTS.said(&rows, "archivedEveryS", ARCHIVED_EVERY_S)?,
            traced_every_s: DEFAULTS.said(&rows, "tracedEveryS", TRACED_EVERY_S)?,
            endpoint: named("endpoint").and_then(|url| {
                let authority = url.split("://").last()?.split('/').next()?;
                authority.rsplit(':').next()?.parse().ok()
            }),
            archive: named("archive").and_then(|url| url.strip_prefix("file://").map(PathBuf::from)),
            tracer: named("tracer").map(|url| url.trim_end_matches('/').to_string()),
        })
    }
}
