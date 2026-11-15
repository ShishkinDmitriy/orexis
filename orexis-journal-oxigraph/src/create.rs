//! THE PACKAGE'S START: it joins where the journal did and the recorder's role names an archive, and takes what
//! lasts to it on a timer.

use std::sync::Arc;

use orexis::Error;
use orexis::task::{Handed, Package, Task};
use orexis_journal::Journal;

use crate::archive::Archive;

/// What archives: the journal read, the archive written and how often. Handed outside by a test that reads both; a
/// deployed agent is handed none and the package opens its own.
pub struct Archives {
    pub journal: Arc<Journal>,
    pub archive: Arc<Archive>,
    pub every_s: f64,
}

inventory::submit! { Package { name: "journal-oxigraph", documents: &[], start } }

/// ITS START, which every package this binary holds is given: it keeps house for the journal, so it joins where the
/// journal did AND THE RECORDER'S ROLE NAMES AN ARCHIVE the world says where to find, and where the role names none
/// its start ends there, and what lasts stays in the journal. Joined, it waits for the journal's start; handed a
/// journal and an archive, its task.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        let archived = |handed: &Handed| {
            Ok(handed.joined("journal") && orexis_journal::role::Role::read(&handed.store)?.archive.is_some())
        };
        if !handed.joins(archived).await? || !handed.started("journal").await {
            return Ok(None);
        }
        make(&handed)
    })
}

fn make(handed: &Handed) -> Result<Option<Task>, Error> {
    //  HANDED A JOURNAL AND AN ARCHIVE, by a test that reads both, it archives into that; deployed and handed none,
    //  it opens its own where the world says the archive is, over the journal handed on; and otherwise it has no task.
    let archives = match handed.outside.take::<Archives>() {
        Some(archives) => archives,
        None if handed.outside.has::<orexis::task::Deployed>() => match own(handed)? {
            Some(archives) => archives,
            None => return Ok(None),
        },
        None => return Ok(None),
    };
    log::info!(
        "{} archives what its journal keeps for good every {}s",
        handed.id,
        archives.every_s
    );
    //  READERS OF THE PAST ASK THE ARCHIVE from now on: the journal's endpoint, and a chat.
    archives.journal.archived_in(archives.archive.store.clone());
    handed
        .outside
        .share::<orexis::task::Reads>()
        .journal
        .lies_in(archives.archive.store.clone());
    //  THE LAST WORD: what was said after this task's last turn, while the others stopped, is taken too, and reaches
    //  the disk.
    let (journal, archive, agent) = (archives.journal.clone(), archives.archive.clone(), handed.id.clone());
    handed.finally(move || {
        if let Err(e) = archive.take(&journal) {
            eprintln!("{agent}: the journal's last entries were not archived: {e}");
        }
        archive.flush();
    });
    Ok(Some(Box::pin(task(handed.clone(), archives))))
}

/// ITS OWN ARCHIVE, where the agent is deployed: the store on disk at the path the world states of the archive the
/// recorder's role names, over the journal that package handed on, taken as often as the role says. A
/// binary built without the volume has nowhere to keep one, says so, and what lasts stays in the journal.
fn own(handed: &Handed) -> Result<Option<Archives>, Error> {
    //  READ AND LEFT, for what ships the activities, whichever of the two starts first.
    let recorder = orexis_journal::role::Role::read(&handed.store)?;
    let (Some(path), Some(journal)) = (recorder.archive, handed.outside.read::<orexis_journal::Traced>()) else {
        return Ok(None);
    };
    let kept = journal.0;
    #[cfg(feature = "volume")]
    {
        Ok(Some(Archives {
            journal: kept,
            archive: Arc::new(Archive::open(&path)?),
            every_s: recorder.archived_every_s,
        }))
    }
    #[cfg(not(feature = "volume"))]
    {
        let _ = kept;
        log::warn!(
            "{}: this binary was built without the volume feature, so no archive is kept at {} and what lasts \
             stays in the journal",
            handed.id,
            path.display()
        );
        Ok(None)
    }
}

/// THE ARCHIVER'S TASK: every stretch of the agent's time, or as an incident is kept, it takes what lasts where
/// anything was written, off the agent's threads, and once more as the run ends.
async fn task(handed: Handed, archives: Archives) -> Result<(), Error> {
    loop {
        let at = handed
            .clock
            .now()
            .checked_add_day_time_duration(orexis::clock::seconds(archives.every_s));
        let over = tokio::select! {
            biased;
            _ = handed.stopped() => true,
            _ = archives.journal.incident.notified() => false,
            _ = handed.sleep_until(at) => false,
        };
        if archives.journal.news() || over {
            let (journal, archive) = (archives.journal.clone(), archives.archive.clone());
            let took = tokio::task::spawn_blocking(move || archive.take(&journal)).await;
            match took {
                Ok(Ok(wrote)) => log::debug!("{}: {wrote} journal entries archived", handed.id),
                Ok(Err(e)) => {
                    archives.journal.renew();
                    log::warn!(
                        "{}: the archive refused the journal's entries, and they stay: {e}",
                        handed.id
                    );
                }
                Err(e) => {
                    archives.journal.renew();
                    log::warn!("{}: archiving the journal did not finish: {e}", handed.id);
                }
            }
        }
        if over {
            break;
        }
    }
    Ok(())
}
