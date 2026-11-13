//! THE JOURNAL, KEPT: the half of the pair that does the work. Where the agent keeps a journal, this hears everything
//! its packages say and writes what happened there as it happens: each event that states triples, as an entry in its
//! package's words (`events`), and each activity as it ends, in PROV's words, with what started it and what it
//! generated (`activities`). It has no task; what it keeps it keeps as it is said. It knows no package's words.
//!
//! The journal itself is the kernel's (`orexis/src/journal.rs`): the store, its window and its incidents. What ships
//! the activities to a tracer is the other half, `orexis-journal-otlp/`, which reads them here on a timer. A
//! reading's point in the series is neither's: what archives sensing's readings writes it
//! (`orexis-sensing-influxdb/`).

use std::sync::Arc;

use orexis::Error;
use orexis::journal::Journal;
use orexis::task::{Handed, Package, Task};

pub mod activities;
pub mod events;

/// The journal to keep, handed outside by whoever runs the agent, where the deployment keeps one.
#[derive(Default)]
pub struct Keeps {
    pub journal: Option<Arc<Journal>>,
}

inventory::submit! { Package { name: "journal", start } }

/// THE START: where it is handed a journal it hears the watch from now on, the events and the activities, and has
/// no task.
fn start(handed: &Handed) -> Result<Option<Task>, Error> {
    if let Some(journal) = handed.outside.take::<Keeps>().and_then(|keeps| keeps.journal) {
        events::History::new(
            handed.events.watch(),
            journal.clone(),
            events::incidents(&handed.store)?,
        );
        activities::connect(handed.events.watch(), journal);
    }
    Ok(None)
}
