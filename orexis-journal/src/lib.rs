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

/// The journal to keep, handed outside by whoever runs the agent, where the deployment keeps one.
#[derive(Default)]
pub struct Keeps {
    pub journal: Option<Arc<Journal>>,
}

/// The journal this package keeps, handed on as it starts to what ships its activities to a tracer.
pub struct Traced(pub Arc<Journal>);

inventory::submit! { Package { name: "journal", documents: orexis::documents!("ontology.ttl"), start } }

/// THE START: where it is handed a journal it hears the watch from now on, the events and the activities, and has
/// no task.
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
    if let Some(journal) = handed.outside.take::<Keeps>().and_then(|keeps| keeps.journal) {
        events::History::new(
            handed.events.watch(),
            journal.clone(),
            events::incidents(&handed.store)?,
        );
        activities::connect(handed.events.watch(), journal.clone());
        //  AND HANDED ON to what ships its activities, which starts after it and makes itself.
        handed.outside.hand(Traced(journal));
    }
    Ok(None)
}
