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
//!
//! - `recorder`: the package's core, the recorder the self plays and the journal it keeps;
//! - the start, below the modules, and nothing else: the journal taken or made, and connected to what is said.

use orexis::task::{Handed, Package};

pub mod activities;
pub mod events;
pub mod journal;
mod recorder;

pub use journal::Journal;
pub use recorder::{Keeps, Recorder, Traced};

inventory::submit! { Package { name: "journal", documents: orexis::documents!("ontology.ttl"), start } }

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
pub const ROLE: &str = "http://example.org/orexis/journal#Recorder";

/// THE JOURNAL'S START, which every package this binary holds is given: it joins where the self plays a recorder and
/// declines otherwise; joined, it keeps the journal a test hands it, or deployed and handed none its own, made as its
/// recorder says, and otherwise none, so a check keeps nothing; what it keeps hears every event and activity said
/// from here on, is what a chat reads of what happened, and is handed on to its housekeepers; and it says it has
/// started - and has no task, what it keeps being kept as it is said.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[ROLE])? {
            return Ok(());
        }
        handed.joins("journal").await?;
        let journal = match handed.outside.take::<Keeps>().and_then(|keeps| keeps.journal) {
            Some(journal) => Some(journal),
            None if handed.outside.has::<orexis::task::Deployed>() => Some(Recorder::new(&handed.store)?.own(&handed)?),
            None => None,
        };
        if let Some(journal) = journal {
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
        }
        handed.started("journal").await;
        Ok(())
    })
}
