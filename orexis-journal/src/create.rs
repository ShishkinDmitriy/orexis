//! THE JOURNAL PACKAGE'S START: it joins where the self plays a recorder, and keeps what the packages say from then
//! on. It has no task; what it keeps it keeps as it is said.

use std::sync::Arc;

use orexis::Error;
use orexis::task::{Handed, Package, Task};

use crate::journal::Journal;
use crate::role::{ROLE, Role};
use crate::{activities, events};

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

/// ITS OWN JOURNAL, where the agent is deployed: in memory, on the agent's clock, its window and what counts as an
/// incident as its role says; the process's log kept in it from here on, with what was said before; and served
/// read-only on the loopback at the port of the endpoint its role names, the past at `/sparql` - the archive once
/// what archives the journal has said where it is, the journal itself until then - and the journal at
/// `/live/sparql`. A role naming no endpoint is served nowhere.
fn own(handed: &Handed) -> Result<Arc<Journal>, Error> {
    let kept = Role::read(&handed.store)?;
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
        if let Err(e) = crate::journal::serve(
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
