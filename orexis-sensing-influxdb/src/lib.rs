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
//! EVERY TEN SECONDS of the agent's time, which is how far the series lags
//! a reading; and a stretch in which sensing observed nothing asks the beliefs nothing.

use std::collections::BTreeMap;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

use orexis::events::{Point, as_of};
use orexis::series::Sink;
use orexis::store::Store;
use orexis::task::{Handed, Package, Task};
use orexis_sensing::events::Observed;
use orexis_sensing::past;

/// How often readings are archived, in the agent's seconds.
pub const INTERVAL_S: f64 = 10.0;

/// Where readings are archived and how often. Handed outside by a test that reads the series; a deployed agent is
/// handed none and the package makes its own sink, where the world names a store that serves history.
pub struct Archives {
    pub sink: Arc<Sink>,
    pub every_s: f64,
}

/// What the store took this run: each reading still held, by its percept, with the point it was written as.
pub type Shipped = BTreeMap<String, Point>;

/// What a turn of the archiver has to do: the points to write, each with its percept, and the past percepts.
#[derive(Default)]
pub struct Due {
    pub points: Vec<(String, Point)>,
    pub past: Vec<String>,
}

/// What is due in `store`, given what was `shipped`: every reading whose point the store does not hold as it now
/// reads, and every past percept. A percept that holds no reading has no point.
pub fn due(store: &Store, shipped: &Shipped) -> Result<Due, orexis::Error> {
    let past = past::past(store)?;
    let mut points = Vec::new();
    for graph in past::read(store)?.into_iter().chain(past.iter().cloned()) {
        if let Some(point) = past::point(store, &graph)?
            && shipped.get(&graph) != Some(&point)
        {
            points.push((graph, point));
        }
    }
    Ok(Due { points, past })
}

/// The store took `due`'s points: remember them in `shipped`, and forget each past percept, which it now holds or
/// which held no reading. How many past readings went.
pub fn took(store: &Store, due: Due, shipped: &mut Shipped) -> Result<usize, orexis::Error> {
    shipped.extend(due.points);
    for graph in &due.past {
        past::forget(store, graph)?;
        shipped.remove(graph);
    }
    Ok(due.past.len())
}

/// Archive what is due in `store` to `sink` and remove the past readings it took; how many past readings went.
pub fn archive(store: &Store, sink: &Sink, shipped: &mut Shipped) -> Result<usize, orexis::Error> {
    let due = due(store, shipped)?;
    let points: Vec<Point> = due.points.iter().map(|(_, p)| p.clone()).collect();
    if sink.write(&points) != points.len() {
        return Ok(0);
    }
    took(store, due, shipped)
}

inventory::submit! { Package { name: "sensing-influxdb", documents: &[], start } }

/// THE ARCHIVER'S START: where it is handed a series store, its task; and none otherwise.
/// ITS START, which every package this binary holds is given: it joins the agent or declines, by its own reason, and
/// joined, makes its core.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        //  IT KEEPS HOUSE FOR SENSING, so it runs where sensing does. It needs nothing of sensing's start.
        if !handed.beside("sensing").await? {
            return Ok(None);
        }
        make(&handed)
    })
}

fn make(handed: &Handed) -> Result<Option<Task>, orexis::Error> {
    //  HANDED A SINK, by a test that reads the series, it archives into that; deployed and handed none, it makes its
    //  own where the world names a store that serves history; and otherwise the readings stay in the beliefs.
    let archives = match handed.outside.take::<Archives>() {
        Some(archives) => archives,
        None if handed.outside.has::<orexis::task::Deployed>() => {
            match Sink::deployed(&handed.store, orexis::series::HISTORY, &orexis::series::environment)? {
                Some((sink, _)) => {
                    log::info!(
                        "{} archives its readings to the history store every {INTERVAL_S}s",
                        handed.id
                    );
                    Archives {
                        sink: Arc::new(sink),
                        every_s: INTERVAL_S,
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
