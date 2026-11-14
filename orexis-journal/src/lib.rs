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
    let mut reads = handed.outside.take::<orexis::task::Reads>().unwrap_or_default();
    reads.journal = Some(journal.store.clone());
    handed.outside.hand(reads);
    //  AND HANDED ON to its housekeepers, which start after it and make themselves.
    handed.outside.hand(Traced(journal));
    Ok(None)
}

const WORDS: &str = "PREFIX journal: <http://example.org/orexis/journal#> ";
const SERVED_AT: &str = "?role journal:servedAt ?service . ?service a journal:Endpoint .";
/// WHAT THE RECORDER'S ROLE SAYS OF HOW ITS JOURNAL IS KEPT, a row per thing said.
const KEPT_Q: &str = "PREFIX journal: <http://example.org/orexis/journal#> \
SELECT ?window ?level ?incident WHERE { ?me a orexis:Self ; orexis:plays ?role . \
{ ?role journal:windowS ?window } UNION { ?role journal:incidentFrom ?level } UNION { ?role journal:incident ?incident } }";

/// How a recorder's journal is kept, as its role says in the agent's self graph, and the package's own where it
/// says nothing: how long the log is kept, from which level a line of it is an incident, and the classes that are
/// incidents beside the vocabulary's.
pub struct Kept {
    pub window_s: f64,
    pub incident_level: log::Level,
    pub incidents: std::collections::BTreeSet<String>,
}

/// What the self's recorder role says of how its journal is kept (`journal:windowS`, `journal:incidentFrom`,
/// `journal:incident`), read off the self graph alone.
pub fn kept(store: &orexis::store::Store) -> Result<Kept, Error> {
    let selves = store.graphs_of(&[orexis::ontology::SELF_GRAPH], &orexis::store::Within::default())?;
    let selves: Vec<&str> = selves.iter().map(String::as_str).collect();
    let rows = store.rows(KEPT_Q, &selves)?;
    let said = |variable: &'static str| -> Vec<String> {
        rows.iter()
            .filter_map(|row| orexis::store::value(row, variable))
            .collect()
    };
    let window_s = said("window")
        .iter()
        .find_map(|w| w.parse::<f64>().ok())
        .filter(|w| *w > 0.0);
    Ok(Kept {
        window_s: window_s.unwrap_or(journal::WINDOW_S),
        incident_level: journal::incident_level(said("level").first().map(String::as_str)),
        incidents: said("incident").into_iter().collect(),
    })
}

/// WHERE THE RECORDER'S JOURNAL IS SERVED: the port of the endpoint its role names (`journal:servedAt`), as the
/// world's deployment states its url, or None where the role names none or the world says nothing of the one named.
pub fn endpoint(store: &orexis::store::Store) -> Result<Option<u16>, Error> {
    Ok(orexis::boot::connected(store, WORDS, SERVED_AT)?.and_then(|url| {
        let authority = url.split("://").last()?.split('/').next()?.to_string();
        authority.rsplit(':').next()?.parse().ok()
    }))
}

/// ITS OWN JOURNAL, where the agent is deployed: in memory, on the agent's clock, its window and what counts as an
/// incident as its role says; the process's log kept in it from here on, with what was said before; and served
/// read-only on the loopback at the port of the endpoint its role names, the past at `/sparql` - the archive once
/// what archives the journal has said where it is, the journal itself until then - and the journal at
/// `/live/sparql`. A role naming no endpoint is served nowhere.
fn own(handed: &Handed) -> Result<Arc<Journal>, Error> {
    let kept = kept(&handed.store)?;
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
    if let Some(port) = endpoint(&handed.store)? {
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
