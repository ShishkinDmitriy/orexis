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

fn env(key: &str) -> Option<String> {
    std::env::var(key).ok().filter(|v| !v.is_empty())
}

/// ITS OWN JOURNAL, where the agent is deployed: in memory, on the agent's clock, its window and what counts as an
/// incident as the environment says; the process's log kept in it from here on, with what was said before; and
/// served read-only on the loopback where the environment names a port (`JOURNAL_PORT`), the past at `/sparql` -
/// the archive once what archives the journal has said where it is, the journal itself until then - and the
/// journal at `/live/sparql`.
fn own(handed: &Handed) -> Result<Arc<Journal>, Error> {
    let mut journal = Journal::new(journal::window_s(&env), {
        let clock = handed.clock.clone();
        Arc::new(move || clock.now())
    })?;
    journal.incident_level = journal::incident_level(&env);
    journal.incidents = journal::incidents(&env);
    let journal = Arc::new(journal);
    if let Some(orexis::task::Said(keep)) = handed.outside.take::<orexis::task::Said>() {
        let into = journal.clone();
        keep(Box::new(move |logger, level, message| {
            let _ = into.remark(logger, level, message, None);
        }));
    }
    #[cfg(feature = "serve")]
    if let Some(port) = env("JOURNAL_PORT").and_then(|p| p.parse().ok()) {
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
