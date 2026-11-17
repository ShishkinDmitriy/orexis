//! THE JOURNAL'S ARCHIVE: the half of the pair that keeps house. `orexis-journal/` writes what happens into the
//! journal, in memory, as it is said; this takes what the journal keeps for good out of it into a triplestore on
//! disk, on a timer, and has the journal forget what it took. One crate does a thing and another keeps house, as
//! `orexis-sensing-influxdb/` does for sensing's readings and `orexis-journal-otlp/` for the activities.
//!
//! WHAT IS TAKEN is what lasts (`Journal::lasting`): each event, and each log record and activity an incident kept.
//! An entry is a named graph in the archive as it is in the journal, so a text reads either alike. The log and the
//! activities no incident kept are never taken: the journal sweeps them past its window.
//!
//! WHAT THE JOURNAL THEN FORGETS is an event at once, and a kept log record or activity once the window has passed
//! it: until then a later incident keeps it again, and what ships the activities reads it there. One that changes
//! after it was taken, an activity told the graphs it wrote, is taken again whole.
//!
//! WHEN: every two of the agent's seconds where anything was written; at once as an incident is kept; and once more in its stopping, once the others have stopped. So an agent killed outright
//! loses what it said in its last stretch, and one that stops, nothing.
//!
//! THE ARCHIVE IS WHAT A READER OF THE PAST IS HANDED: the endpoint's `/sparql`, a chat's journal tool and a stopped
//! agent's store opened read-only all read it, a stretch behind the journal at most.
//!
//! - `archive`: the archive, and what archives;
//! - the start, below the modules, and nothing else: the archive taken or opened, and the task that takes what lasts.

use orexis::task::{Handed, Package};

mod archive;

pub use archive::{Archive, Archives};

inventory::submit! { Package { name: "journal-oxigraph", start } }

/// ITS START, which every package this binary holds is given: it keeps house for the journal, so it joins where the
/// journal did AND THE RECORDER'S ROLE NAMES AN ARCHIVE the world says where to find, and where the role names none
/// its start ends there, and what lasts stays in the journal. It says it booted, which waits until the journal's
/// package has; checked, it ends there; otherwise it takes the journal and the archive a test hands it, or,
/// deployed, opens its own; and what follows is ITS TASK, which every stretch of the agent's time, or as an incident
/// is kept, takes what lasts where anything was written, off the agent's threads, and once more in its stopping, once the others have stopped.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        //  IT RUNS WHERE THE RECORDER'S ROLE NAMES ITS SERVICE.
        if !handed.plays(&[orexis_journal::ROLE])? {
            return Ok(());
        }
        let recorder = orexis_journal::Recorder::new(&handed.store)?;
        let Some(path) = recorder.archived_in.clone() else {
            return Ok(());
        };
        //  ITS CORE IS MADE ONCE EVERY PACKAGE HAS MADE ITS OWN, so the journal it keeps house for is handed on.
        if !handed.booted().await? {
            return Ok(());
        }
        //  OVER THE JOURNAL that package handed on, where it keeps one: handed an archive, by a test that reads it, it
        //  archives into that; deployed and handed none, it opens its own on disk at the path the world states of the
        //  archive the recorder's role names; and otherwise it has no task. Taken as often as the role says, unless
        //  the test says otherwise. A binary built without the volume has nowhere to keep one, says so, and what lasts
        //  stays in the journal.
        let Some(orexis_journal::Traced(journal)) = handed.provided.read::<orexis_journal::Traced>() else {
            return Ok(());
        };
        let (archive, every_s) = match handed.provided.take::<Archives>() {
            Some(archives) => (archives.archive, archives.every_s),
            None if handed.provided.has::<orexis::task::Deployed>() => {
                #[cfg(feature = "volume")]
                {
                    (std::sync::Arc::new(Archive::open(&path)?), None)
                }
                #[cfg(not(feature = "volume"))]
                {
                    log::warn!(
                        "{}: this binary was built without the volume feature, so no archive is kept at {} and what \
                         lasts stays in the journal",
                        handed.id,
                        path.display()
                    );
                    return Ok(());
                }
            }
            None => return Ok(()),
        };
        let every_s = every_s.unwrap_or(recorder.archived_every_s);
        log::info!(
            "{} archives what its journal keeps for good every {every_s}s",
            handed.id
        );
        //  READERS OF THE PAST ASK THE ARCHIVE from now on: the journal's endpoint, and a chat.
        journal.archived_in(archive.store.clone());
        handed
            .provided
            .share::<orexis::series::Reads>()
            .journal
            .lies_in(archive.store.clone());
        //  THE LAST WORD: what was said after this task's last turn, while the others stopped, is taken too, and
        //  reaches the disk.
        loop {
            let at = handed
                .clock
                .now()
                .checked_add_day_time_duration(orexis::clock::seconds(every_s));
            let over = tokio::select! {
                biased;
                _ = handed.stopped() => true,
                _ = journal.incident.notified() => false,
                _ = handed.sleep_until(at) => false,
            };
            if journal.news() || over {
                let (taken, into) = (journal.clone(), archive.clone());
                let took = tokio::task::spawn_blocking(move || into.take(&taken)).await;
                match took {
                    Ok(Ok(wrote)) => log::debug!("{}: {wrote} journal entries archived", handed.id),
                    Ok(Err(e)) => {
                        journal.renew();
                        log::warn!(
                            "{}: the archive refused the journal's entries, and they stay: {e}",
                            handed.id
                        );
                    }
                    Err(e) => {
                        journal.renew();
                        log::warn!("{}: archiving the journal did not finish: {e}", handed.id);
                    }
                }
            }
            if over {
                break;
            }
        }
        //  AND ONCE EVERY RUNNING PACKAGE HAS ENDED, inside its stopping, the entries the others said as they stopped.
        handed.stopping().await?;
        if let Err(e) = archive.take(&journal) {
            log::warn!("{}: the journal's last entries were not archived: {e}", handed.id);
        }
        archive.flush();
        Ok(())
    })
}
