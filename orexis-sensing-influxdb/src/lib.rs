//! SENSING, TO INFLUXDB: the half of the pair that keeps house. `orexis-sensing/` observes, and keeps in the kind its
//! rules read exactly the readings they are about; an older one it files past and forgets nothing. This is what
//! writes a reading to the agent's series store, and nothing else does: on a timer it archives every reading sensing
//! holds that the store has not yet taken, read or past, and removes the past ones the store holds.
//!
//! OPTIONAL, AND THE DEPLOYMENT'S: the package has a task only where it is handed a series store to archive to. An
//! agent with none - a test, a world nobody monitors - keeps every reading where it lies, in its beliefs, and
//! nothing of sensing's logic differs, since no rule reads a past reading.
//!
//! ARCHIVED ONCE, THEN REMOVED WHEN PAST: what the store took is remembered by the point it took (`Shipped`), so a
//! reading is written once, and again only where its point has changed since - one read while sensing was still
//! concluding it. A past reading is forgotten only once the store holds its point. A store that refuses leaves all
//! as it lies for the next time, so nothing is lost for a store being away, and the beliefs grow by the readings it
//! missed and no more. What was shipped is remembered for the run alone: after a restart each reading still held is
//! written again, on its own instant, measurement and tags, so the series holds it once. The point is sensing's to
//! say (`past::point`) and the graphs are sensing's to remove (`past::forget`): this asks, and names no word of an
//! observation.
//!
//! AS OFTEN AS THE OBSERVER'S ROLE SAYS (`sensing:archivedEveryS`), in the agent's seconds, every ten where it says
//! nothing, which is how far the series lags a reading; and a stretch in which sensing observed nothing asks the
//! beliefs nothing.
//!
//! - `observer`: the observer the self plays, as what archives its readings reads it;
//! - `archives`: where readings are archived, what is due and what the store took;
//! - the start, below the modules, and nothing else: the sink handed or made, and the task that archives on a timer.

use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

use orexis::events::{Point, as_of};
use orexis::series::Sink;
use orexis::task::{Handed, Package};
use orexis_sensing::events::Observed;
use orexis_sensing::ontology::OBSERVER;

mod archives;
mod observer;

pub use archives::{Archives, Due, Shipped, archive, archived_every_s, due, took};
pub use observer::Observer;

inventory::submit! { Package { name: "sensing-influxdb", documents: &[], start } }

/// ITS START, which every package this binary holds is given: it keeps house for sensing, so it joins where sensing
/// did AND THE OBSERVER'S ROLE NAMES A SERIES STORE the world says where to reach (`sensing:archivedIn`), and where
/// the role names none its start ends there and the readings stay in the beliefs. Joined, it archives into the sink a
/// test hands it or, deployed, one of its own, and hears whether sensing observed anything; it says it has started;
/// checked, it ends there; otherwise what follows is ITS TASK, which every stretch of the agent's time archives what
/// is due, the write off the agent's threads, and once more as the run ends. It needs nothing of sensing's start.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        //  IT RUNS WHERE THE OBSERVER'S ROLE NAMES A SERIES STORE.
        if !handed.plays(&[OBSERVER])? {
            return Ok(());
        }
        let observer = Observer::new(&handed.store)?;
        if observer.archived_in.is_none() {
            return Ok(());
        }
        //  HANDED A SINK, by a test that reads the series, it archives into that; deployed and handed none, it makes
        //  its own where the world says where the store its role names answers; and otherwise the readings stay in the
        //  beliefs.
        let sink = match handed.provided.take::<Archives>() {
            Some(archives) => Some((archives.sink, archives.every_s)),
            None if handed.provided.has::<orexis::task::Deployed>() => {
                Sink::deployed(&handed.store, orexis::series::HISTORY, &orexis::series::environment)?
                    .map(|(sink, _)| (Arc::new(sink), None))
            }
            None => None,
        };
        let Some((sink, every_s)) = sink else {
            handed.started("sensing-influxdb").await;
            return Ok(());
        };
        let every_s = every_s.unwrap_or(observer.archived_every_s);
        log::info!(
            "{} archives its readings to the history store every {every_s}s",
            handed.id
        );
        //  WHAT A CHAT READS OF THE PAST is the series this writes.
        let reader = sink.reader();
        handed
            .provided
            .alter(|reads: &mut orexis::task::Reads| reads.history = Some(reader));
        //  WHETHER SENSING OBSERVED ANYTHING SINCE THE LAST TURN: heard, so a quiet stretch asks the beliefs nothing.
        //  The readings a lived volume already holds are due at the first.
        let news = Arc::new(AtomicBool::new(true));
        let heard = news.clone();
        handed.events.watch().connect(move |event, _| {
            if as_of::<Observed>(event).is_some() {
                heard.store(true, Ordering::Relaxed);
            }
        });
        handed.started("sensing-influxdb").await;
        if handed.checking().is_some() {
            return Ok(());
        }
        let mut shipped = Shipped::new();
        loop {
            let at = handed
                .clock
                .now()
                .checked_add_day_time_duration(orexis::clock::seconds(every_s));
            let over = tokio::select! {
                biased;
                _ = handed.stopped() => true,
                _ = handed.sleep_until(at) => false,
            };
            if news.swap(false, Ordering::Relaxed) || over {
                let due = due(&handed.store, &shipped)?;
                let points: Vec<Point> = due.points.iter().map(|(_, p)| p.clone()).collect();
                let sink = sink.clone();
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
    })
}
