//! THE RECORDER, the package's core: the role the self plays, read off its self graph and the world's deployment, and
//! the journal it keeps where the agent is deployed; and what hands a journal on, to a test or a housekeeper.

use std::sync::Arc;

use orexis::Error;
use orexis::task::Handed;

use crate::ROLE;
use crate::journal::{self, Journal};

/// The journal to keep, provided by a test that reads what it kept. A deployed agent is handed none and the
/// package makes its own (`orexis::task::Deployed`).
#[derive(Default)]
pub struct Keeps {
    pub journal: Option<Arc<Journal>>,
}

/// The journal this package keeps, handed on as it starts to what ships its activities to a tracer.
#[derive(Clone)]
pub struct Traced(pub Arc<Journal>);

/// THE RECORDER THE SELF PLAYS, AS THE JOURNAL'S CRATES READ IT: a field for each thing `journal:Recorder` may say,
/// how the journal is kept and what it is linked to. A figure the role does not state is the journal's own, and a
/// link is where the service the role names answers, as the world's deployment states it: None where the role
/// names none or the world says nothing of the one named.
#[derive(Debug, Clone, PartialEq)]
pub struct Recorder {
    /// How long the log and the activities no incident kept are kept, in the agent's seconds (`journal:windowS`).
    pub window_s: f64,
    /// From which level a line of the log is an incident (`journal:incidentFrom`).
    pub incident_from: log::Level,
    /// The classes that are incidents beside the vocabulary's (`journal:incident`).
    pub incidents: std::collections::BTreeSet<String>,
    /// Where the journal is served, the port of its endpoint (`journal:servedAt`).
    pub served_at: Option<u16>,
    /// Where what lasts is archived, the path of its archive (`journal:archivedIn`).
    pub archived_in: Option<std::path::PathBuf>,
    /// How often what lasts is taken to the archive, in the agent's seconds (`journal:archivedEveryS`).
    pub archived_every_s: f64,
    /// Where the activities are shipped, the url of its tracer (`journal:tracedBy`).
    pub traced_by: Option<String>,
    /// How often the activities are shipped, in the agent's seconds (`journal:tracedEveryS`).
    pub traced_every_s: f64,
}

impl Recorder {
    /// The recorder the self plays, read off its self graph and the world's deployment graph by this package's own
    /// query. An agent plays one recorder: two are refused, and where the self plays none nothing is said.
    pub fn new(store: &orexis::store::Store) -> Result<Self, Error> {
        /// THE RECORDER THE SELF PLAYS, IN ONE QUERY: each figure and word the role says or, where it says none, the
        /// default the journal's ontology states on its shape of the role (`sh:defaultValue`); and where each service
        /// the role names answers, as the world's deployment states it.
        const RECORDER_Q: &str = "SELECT ?role ?kind (COALESCE(?windowSaid, ?windowOwn) AS ?window) (COALESCE(?fromSaid, ?fromOwn) AS ?from) \
        ?incident ?served ?archive (COALESCE(?archivedEverySaid, ?archivedEveryOwn) AS ?archivedEvery) ?tracer \
        (COALESCE(?tracedEverySaid, ?tracedEveryOwn) AS ?tracedEvery) WHERE { \
        ?me a orexis:Self ; orexis:plays ?role . ?role a ?kind . \
        OPTIONAL { ?role <http://example.org/orexis/journal#windowS> ?windowSaid FILTER(?windowSaid > 0) } \
        OPTIONAL { ?shape sh:targetClass <{ROLE}> ; sh:property [ sh:path <http://example.org/orexis/journal#windowS> ; sh:defaultValue ?windowOwn ] } \
        OPTIONAL { ?role <http://example.org/orexis/journal#incidentFrom> ?fromSaid } \
        OPTIONAL { ?shape sh:targetClass <{ROLE}> ; sh:property [ sh:path <http://example.org/orexis/journal#incidentFrom> ; sh:defaultValue ?fromOwn ] } \
        OPTIONAL { ?role <http://example.org/orexis/journal#archivedEveryS> ?archivedEverySaid FILTER(?archivedEverySaid > 0) } \
        OPTIONAL { ?shape sh:targetClass <{ROLE}> ; sh:property [ sh:path <http://example.org/orexis/journal#archivedEveryS> ; sh:defaultValue ?archivedEveryOwn ] } \
        OPTIONAL { ?role <http://example.org/orexis/journal#tracedEveryS> ?tracedEverySaid FILTER(?tracedEverySaid > 0) } \
        OPTIONAL { ?shape sh:targetClass <{ROLE}> ; sh:property [ sh:path <http://example.org/orexis/journal#tracedEveryS> ; sh:defaultValue ?tracedEveryOwn ] } \
        OPTIONAL { ?role <http://example.org/orexis/journal#incident> ?incident } \
        OPTIONAL { ?role <http://example.org/orexis/journal#servedAt> ?endpoint . ?endpoint <https://schema.org/url> ?served } \
        OPTIONAL { ?role <http://example.org/orexis/journal#archivedIn> ?kept . ?kept <https://schema.org/url> ?archive } \
        OPTIONAL { ?role <http://example.org/orexis/journal#tracedBy> ?traced . ?traced <https://schema.org/url> ?tracer } }";
        use orexis::ontology::{DEPLOYMENT, ONTOLOGY, SELF_GRAPH};
        use orexis::store::{Within, value};
        let mut known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        known.extend(store.graphs_of(&[DEPLOYMENT], &Within::common())?);
        known.extend(store.graphs_of(&[ONTOLOGY], &Within::default())?);
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let mut rows = Vec::new();
        for row in store.rows(&RECORDER_Q.replace("{ROLE}", ROLE), &known)? {
            let kind = value(&row, "kind").unwrap_or_default();
            if kind == ROLE || store.closed(&kind)?.iter().any(|class| class == ROLE) {
                rows.push(row);
            }
        }
        //  ONE IS PLAYED: what the role says is said to this package once for the agent, and two are never picked
        //  between, which onboarding refuses before a boot does.
        let played: std::collections::BTreeSet<String> = rows.iter().filter_map(|row| value(row, "role")).collect();
        if played.len() > 1 {
            return Err(orexis::Error::Document(format!(
                "the self plays {} recorders, and an agent plays one",
                played.len()
            )));
        }
        if rows.is_empty() {
            return Err(orexis::Error::Document(format!(
                "the self plays no {}",
                orexis::ontology::local_of(ROLE)
            )));
        }
        let said = |what: &str| {
            rows.iter()
                .find_map(|row| value(row, what))
                .filter(|said| !said.is_empty())
        };
        //  A FIGURE NEITHER THE ROLE NOR THE SHAPE STATES is a package shipped broken.
        let figure = |what: &str| {
            said(what)
                .and_then(|figure| figure.parse::<f64>().ok())
                .ok_or_else(|| orexis::Error::Document(format!("the journal's ontology states no default for {what}")))
        };
        Ok(Recorder {
            window_s: figure("window")?,
            incident_from: journal::incident_level(said("from").as_deref()),
            incidents: rows.iter().filter_map(|row| value(row, "incident")).collect(),
            served_at: said("served").and_then(|url| {
                let authority = url.split("://").last()?.split('/').next()?;
                authority.rsplit(':').next()?.parse().ok()
            }),
            archived_in: said("archive").and_then(|url| url.strip_prefix("file://").map(std::path::PathBuf::from)),
            archived_every_s: figure("archivedEvery")?,
            traced_by: said("tracer").map(|url| url.trim_end_matches('/').to_string()),
            traced_every_s: figure("tracedEvery")?,
        })
    }

    /// ITS OWN JOURNAL, where the agent is deployed: in memory, on the agent's clock, its window and what counts as an
    /// incident as its role says; the process's log kept in it from here on, with what was said before; and served
    /// read-only on the loopback at the port of the endpoint its role names, the past at `/sparql` - the archive once
    /// what archives the journal has said where it is, the journal itself until then - and the journal at
    /// `/live/sparql`. A role naming no endpoint is served nowhere.
    pub(crate) fn own(self, handed: &Handed) -> Result<Arc<Journal>, Error> {
        let kept = self;
        let mut journal = Journal::new(kept.window_s, {
            let clock = handed.clock.clone();
            Arc::new(move || clock.now())
        })?;
        journal.incident_level = kept.incident_from;
        journal.incidents = kept.incidents;
        let journal = Arc::new(journal);
        if let Some(orexis::task::Said(keep)) = handed.provided.take::<orexis::task::Said>() {
            let into = journal.clone();
            keep(Box::new(move |logger, level, message| {
                let _ = into.remark(logger, level, message, None);
            }));
        }
        #[cfg(feature = "serve")]
        if let Some(port) = kept.served_at {
            let (past, live) = (journal.clone(), journal.store.clone());
            if let Err(e) = journal::serve(
                vec![
                    ("/sparql", Box::new(move || past.past())),
                    ("/live/sparql", Box::new(move || live.clone())),
                ],
                "127.0.0.1",
                port,
            ) {
                log::warn!("{}: the journal cannot be served on {port}: {e}", handed.id);
            }
        }
        Ok(journal)
    }
}
