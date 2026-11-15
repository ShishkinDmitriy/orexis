//! THE JOURNAL, KEPT: the half of the pair that does the work. Where the agent keeps a journal, this hears everything
//! its packages say and writes what happened there as it happens: each event that states triples, as an entry in its
//! package's words (`events`), and each activity as it ends, in PROV's words, with what started it and what it
//! generated (`activities`). It has no task; what it keeps it keeps as it is said. It knows no package's words.
//!
//! LOADED FOR A ROLE, as every package is: an agent keeps a journal where its self graph says it plays a
//! `journal:Recorder` (`ontology.ttl`), and where it plays none its packages say what happens and nobody writes it
//! down. The kernel knows no journal: an event may state triples (`Event::statements`), and that is all it says.
//!
//! The journal itself is here too (`journal`): the store, its window and its incidents. What ships the activities to
//! a tracer is the other half, `orexis-journal-otlp/`, which reads them here on a timer. A reading's point in the
//! series is neither's: what archives sensing's readings writes it (`orexis-sensing-influxdb/`).

use std::sync::Arc;

use orexis::Error;
use orexis::task::{Handed, Package, Task};

pub mod activities;
pub mod events;
pub mod journal;

pub use journal::Journal;

/// The journal to keep, handed outside by a test that reads what it kept. A deployed agent is handed none and the
/// package makes its own (`orexis::task::Deployed`).
#[derive(Default)]
pub struct Keeps {
    pub journal: Option<Arc<Journal>>,
}

/// The journal this package keeps, handed on as it starts to what ships its activities to a tracer.
#[derive(Clone)]
pub struct Traced(pub Arc<Journal>);

inventory::submit! { Package { name: "journal", documents: orexis::documents!("ontology.ttl"), start } }

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
const ROLE: &str = "http://example.org/orexis/journal#Recorder";

/// ITS START, which every package this binary holds is given: it joins the agent or declines, by its own reason, and
/// joined, makes its core.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[ROLE]).await? {
            return Ok(None);
        }
        make(&handed)
    })
}

fn make(handed: &Handed) -> Result<Option<Task>, Error> {
    //  HANDED ONE, by a test that reads what it kept, it keeps that; deployed and handed none, it makes its own;
    //  and otherwise it keeps none, so a check keeps nothing.
    let journal = match handed.outside.take::<Keeps>().and_then(|keeps| keeps.journal) {
        Some(journal) => journal,
        None if handed.outside.has::<orexis::task::Deployed>() => own(handed)?,
        None => return Ok(None),
    };
    events::History::new(
        handed.events.watch(),
        journal.clone(),
        events::incidents(&handed.store)?,
    );
    activities::connect(handed.events.watch(), journal.clone());
    //  WHAT A CHAT READS OF WHAT HAPPENED is this journal, until what archives it says otherwise.
    handed
        .outside
        .share::<orexis::task::Reads>()
        .journal
        .lies_in(journal.store.clone());
    //  AND HANDED ON to its housekeepers, which wait for this start and make themselves.
    handed.outside.hand(Traced(journal));
    Ok(None)
}

const JOURNAL: &str = "http://example.org/orexis/journal#";

/// THE RECORDER'S ROLE, AS THE JOURNAL'S CRATES READ IT: how the journal is kept and what it is linked to, each
/// field what the role says in the agent's self graph and, where it says nothing, the package's own (`Default`).
/// A link is where the service the role names answers, as the world's deployment states it, and None where the
/// role names none or the world says nothing of the one named.
#[derive(Debug, Clone, PartialEq)]
pub struct Recorder {
    /// How long the log and the activities no incident kept are kept, in the agent's seconds (`journal:windowS`).
    pub window_s: f64,
    /// From which level a line of the log is an incident (`journal:incidentFrom`).
    pub incident_level: log::Level,
    /// The classes that are incidents beside the vocabulary's (`journal:incident`).
    pub incidents: std::collections::BTreeSet<String>,
    /// Where the journal is served, the port of its endpoint (`journal:servedAt`).
    pub endpoint: Option<u16>,
    /// Where what lasts is archived, the path of its archive (`journal:archivedIn`).
    pub archive: Option<std::path::PathBuf>,
    /// How often what lasts is taken to the archive, in the agent's seconds (`journal:archivedEveryS`).
    pub archived_every_s: f64,
    /// Where the activities are shipped, the url of its tracer (`journal:tracedBy`).
    pub tracer: Option<String>,
    /// How often the activities are shipped, in the agent's seconds (`journal:tracedEveryS`).
    pub traced_every_s: f64,
}

impl Default for Recorder {
    fn default() -> Self {
        Recorder {
            window_s: journal::WINDOW_S,
            incident_level: log::Level::Warn,
            incidents: std::collections::BTreeSet::new(),
            endpoint: None,
            archive: None,
            archived_every_s: 2.0,
            tracer: None,
            traced_every_s: 10.0,
        }
    }
}

impl Recorder {
    /// The recorder the self plays, read off the store: None where it plays none.
    pub fn read(store: &orexis::store::Store) -> Result<Option<Self>, Error> {
        let Some(role) = orexis::role::played(store, ROLE)? else {
            return Ok(None);
        };
        let own = Recorder::default();
        let said = |word: &str| format!("{JOURNAL}{word}");
        Ok(Some(Recorder {
            window_s: role.figure(&said("windowS")).unwrap_or(own.window_s),
            incident_level: journal::incident_level(role.word(&said("incidentFrom"))),
            incidents: role.words(&said("incident")).iter().cloned().collect(),
            endpoint: role.answers(&said("servedAt")).and_then(|url| {
                let authority = url.split("://").last()?.split('/').next()?;
                authority.rsplit(':').next()?.parse().ok()
            }),
            archive: role
                .answers(&said("archivedIn"))
                .and_then(|url| url.strip_prefix("file://").map(std::path::PathBuf::from)),
            archived_every_s: role.figure(&said("archivedEveryS")).unwrap_or(own.archived_every_s),
            tracer: role
                .answers(&said("tracedBy"))
                .map(|url| url.trim_end_matches('/').to_string()),
            traced_every_s: role.figure(&said("tracedEveryS")).unwrap_or(own.traced_every_s),
        }))
    }
}

/// ITS OWN JOURNAL, where the agent is deployed: in memory, on the agent's clock, its window and what counts as an
/// incident as its role says; the process's log kept in it from here on, with what was said before; and served
/// read-only on the loopback at the port of the endpoint its role names, the past at `/sparql` - the archive once
/// what archives the journal has said where it is, the journal itself until then - and the journal at
/// `/live/sparql`. A role naming no endpoint is served nowhere.
fn own(handed: &Handed) -> Result<Arc<Journal>, Error> {
    let kept = Recorder::read(&handed.store)?.unwrap_or_default();
    let mut journal = Journal::new(kept.window_s, {
        let clock = handed.clock.clone();
        Arc::new(move || clock.now())
    })?;
    journal.incident_level = kept.incident_level;
    journal.incidents = kept.incidents;
    let journal = Arc::new(journal);
    if let Some(orexis::task::Said(keep)) = handed.outside.take::<orexis::task::Said>() {
        let into = journal.clone();
        keep(Box::new(move |logger, level, message| {
            let _ = into.remark(logger, level, message, None);
        }));
    }
    #[cfg(feature = "serve")]
    if let Some(port) = kept.endpoint {
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
