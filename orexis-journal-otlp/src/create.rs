//! THE PACKAGE'S START: it joins where the journal did and the recorder's role names a tracer, and ships on a timer.

use std::sync::Arc;

use orexis::task::{Handed, Package, Task};
use orexis_journal::Traced;
use orexis_journal::journal::Journal;

use crate::ship::{Send, post, ship};

/// What is shipped and where: made by this package from the journal handed on and the tracer the world names, or
/// handed outside by a test that ships to an endpoint of its own.
pub struct Ships {
    pub journal: Arc<Journal>,
    pub endpoint: String,
    pub every_s: f64,
}

inventory::submit! { Package { name: "journal-otlp", documents: &[], start } }

/// ITS START, which every package this binary holds is given: it keeps house for the journal, so it joins where the
/// journal did AND THE RECORDER'S ROLE NAMES A TRACER the world says where to reach, and where the role names none
/// its start ends there. Joined, it waits
/// for the journal's start, takes the journal that handed on, and makes its task: where to ship is the world's word,
/// and how often is its own stretch.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        let traced = |handed: &Handed| {
            Ok(handed.joined("journal") && orexis_journal::role::Role::read(&handed.store)?.tracer.is_some())
        };
        if !handed.joins(traced).await? || !handed.started("journal").await {
            return Ok(None);
        }
        make(&handed)
    })
}

fn make(handed: &Handed) -> Result<Option<Task>, orexis::Error> {
    //  HANDED ONE, by a test that ships to its own endpoint, it ships that; otherwise it makes its own.
    let ships = match handed.outside.take::<Ships>() {
        Some(ships) => ships,
        None => {
            let recorder = orexis_journal::role::Role::read(&handed.store)?;
            let (Some(endpoint), Some(journal)) = (recorder.tracer, handed.outside.read::<Traced>()) else {
                return Ok(None);
            };
            Ships {
                journal: journal.0,
                endpoint,
                every_s: recorder.traced_every_s,
            }
        }
    };
    log::info!(
        "{} ships its activities as spans to {} every {}s",
        handed.id,
        ships.endpoint,
        ships.every_s
    );
    let send = post(&ships.endpoint);
    Ok(Some(Box::pin(task(handed.clone(), ships, send))))
}

/// THE SHIPPER'S TASK: every stretch of the agent's time it ships what the journal holds unshipped, off the agent's
/// threads, and once more as the run ends.
async fn task(handed: Handed, ships: Ships, send: Send) -> Result<(), orexis::Error> {
    let agent = handed.id.clone();
    let shipping = |journal: Arc<Journal>, endpoint: String, send: Send, agent: String| async move {
        let _ = tokio::task::spawn_blocking(move || ship(&journal, &agent, &endpoint, &send)).await;
    };
    loop {
        let due = handed
            .clock
            .now()
            .checked_add_day_time_duration(orexis::clock::seconds(ships.every_s));
        let over = tokio::select! {
            biased;
            _ = handed.stopped() => true,
            _ = handed.sleep_until(due) => false,
        };
        shipping(
            ships.journal.clone(),
            ships.endpoint.clone(),
            send.clone(),
            agent.clone(),
        )
        .await;
        if over {
            break;
        }
    }
    Ok(())
}
