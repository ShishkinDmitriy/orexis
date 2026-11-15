//! THE PACKAGE'S START: it joins where sensing did and the observer's role names a series store, and archives the
//! readings on a timer.

use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

use orexis::events::{Point, as_of};
use orexis::series::Sink;
use orexis::task::{Handed, Package, Task};
use orexis_sensing::events::Observed;

use crate::archive::{Shipped, due, took};
use crate::role::Role;

/// Where readings are archived and how often. Handed outside by a test that reads the series; a deployed agent is
/// handed none and the package makes its own sink, where the world names a store that serves history.
pub struct Archives {
    pub sink: Arc<Sink>,
    pub every_s: f64,
}

inventory::submit! { Package { name: "sensing-influxdb", documents: &[], start } }

/// ITS START, which every package this binary holds is given: it keeps house for sensing, so it joins where sensing
/// did AND THE OBSERVER'S ROLE NAMES A SERIES STORE the world says where to reach (`sensing:archivedIn`), and where
/// the role names none its start ends there and the readings stay in the beliefs. It needs nothing of sensing's
/// start.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        let archived = |handed: &Handed| Ok(handed.joined("sensing") && Role::read(&handed.store)?.archive.is_some());
        if !handed.joins(archived).await? {
            return Ok(None);
        }
        make(&handed)
    })
}

fn make(handed: &Handed) -> Result<Option<Task>, orexis::Error> {
    //  HANDED A SINK, by a test that reads the series, it archives into that; deployed and handed none, it makes its
    //  own where the world says where the store its role names answers; and otherwise the readings stay in the beliefs.
    let archives = match handed.outside.take::<Archives>() {
        Some(archives) => archives,
        None if handed.outside.has::<orexis::task::Deployed>() => {
            match Sink::deployed(&handed.store, orexis::series::HISTORY, &orexis::series::environment)? {
                Some((sink, _)) => {
                    let every_s = Role::read(&handed.store)?.archived_every_s;
                    log::info!(
                        "{} archives its readings to the history store every {every_s}s",
                        handed.id
                    );
                    Archives {
                        sink: Arc::new(sink),
                        every_s,
                    }
                }
                None => return Ok(None),
            }
        }
        None => return Ok(None),
    };
    //  WHETHER SENSING OBSERVED ANYTHING SINCE THE LAST TURN: heard, so a quiet stretch asks the beliefs nothing. The
    //  readings a lived volume already holds are due at the first.
    let news = Arc::new(AtomicBool::new(true));
    let heard = news.clone();
    handed.events.watch().connect(move |event, _| {
        if as_of::<Observed>(event).is_some() {
            heard.store(true, Ordering::Relaxed);
        }
    });
    Ok(Some(Box::pin(task(handed.clone(), archives, news))))
}

/// THE ARCHIVER'S TASK: every stretch of the agent's time it archives what is due, the write off the agent's
/// threads, and once more as the run ends.
async fn task(handed: Handed, archives: Archives, news: Arc<AtomicBool>) -> Result<(), orexis::Error> {
    let mut shipped = Shipped::new();
    loop {
        let at = handed
            .clock
            .now()
            .checked_add_day_time_duration(orexis::clock::seconds(archives.every_s));
        let over = tokio::select! {
            biased;
            _ = handed.stopped() => true,
            _ = handed.sleep_until(at) => false,
        };
        if news.swap(false, Ordering::Relaxed) || over {
            let due = due(&handed.store, &shipped)?;
            let points: Vec<Point> = due.points.iter().map(|(_, p)| p.clone()).collect();
            let sink = archives.sink.clone();
            let wanted = points.len();
            let wrote = tokio::task::spawn_blocking(move || sink.write(&points))
                .await
                .unwrap_or(0);
            if wrote == wanted {
                let gone = took(&handed.store, due, &mut shipped)?;
                log::debug!("{}: {wanted} reading(s) archived, {gone} past removed", handed.id);
            } else {
                //  REFUSED: all is as it lay, and due again at the next turn.
                news.store(true, Ordering::Relaxed);
            }
        }
        if over {
            break;
        }
    }
    Ok(())
}
