//! SENSING, TO INFLUXDB: the half of the pair that keeps house. `orexis-sensing/` observes, and keeps in the kind its
//! rules read exactly the readings they are about; an older one it files past and forgets nothing. This archives the
//! past readings to the agent's series store and removes them, on a timer, hearing nothing.
//!
//! OPTIONAL, AND THE DEPLOYMENT'S: the package has a task only where it is handed a series store to archive to. An
//! agent with none - a test, a world nobody monitors - keeps every reading where it lies, in its beliefs, and
//! nothing of sensing's logic differs, since no rule reads a past reading.
//!
//! ARCHIVED, THEN REMOVED: a past reading is forgotten only once the store took the point it is. A store that refuses
//! leaves it where it lies for the next time, so nothing is lost for a store being away, and the beliefs grow by the
//! readings it missed and no more. A point written twice lands on its own instant, measurement and tags, so it is
//! written once. The point is sensing's to say, as it said it when the reading was observed (`past::point`), and the
//! graphs are sensing's to remove (`past::forget`): this asks, and names no word of an observation.
//!
//! EVERY `ARCHIVE_INTERVAL_S` of the agent's time, a minute where nothing says: an observation reaches the series as
//! it is observed, by the history part, so the series lags nothing; what waits for this is only the room in the
//! beliefs.

use std::sync::Arc;

use orexis::events::Point;
use orexis::series::Sink;
use orexis::store::Store;
use orexis::task::{Handed, Package, Task};
use orexis_sensing::past;

/// How often past readings are archived, in the agent's seconds, told as environment.
pub const INTERVAL: &str = "ARCHIVE_INTERVAL_S";
/// How often, where the environment says nothing.
pub const INTERVAL_S: f64 = 60.0;

/// Where past readings are archived and how often, handed outside by whoever runs the agent, where the deployment
/// keeps a series store.
pub struct Archives {
    pub sink: Arc<Sink>,
    pub every_s: f64,
}

/// How often to archive, as the environment says, or `INTERVAL_S`.
pub fn interval(env: &dyn Fn(&str) -> Option<String>) -> f64 {
    env(INTERVAL)
        .and_then(|s| s.parse::<f64>().ok())
        .filter(|s| *s > 0.0)
        .unwrap_or(INTERVAL_S)
}

/// Every past reading of `store` with the point it is; one that holds no reading has none, and goes unarchived.
pub fn due(store: &Store) -> Result<Vec<(String, Option<Point>)>, orexis::Error> {
    past::past(store)?
        .into_iter()
        .map(|graph| {
            let point = past::point(store, &graph)?;
            Ok((graph, point))
        })
        .collect()
}

/// Forget each of `graphs`: the store took what they were.
pub fn remove(store: &Store, graphs: &[String]) -> Result<(), orexis::Error> {
    for graph in graphs {
        past::forget(store, graph)?;
    }
    Ok(())
}

/// Archive every past reading of `store` to `sink` and remove what it took; how many readings went.
pub fn archive(store: &Store, sink: &Sink) -> Result<usize, orexis::Error> {
    let due = due(store)?;
    if due.is_empty() {
        return Ok(0);
    }
    let points: Vec<Point> = due.iter().filter_map(|(_, p)| p.clone()).collect();
    if !points.is_empty() && sink.write(&points) != points.len() {
        return Ok(0);
    }
    let graphs: Vec<String> = due.into_iter().map(|(g, _)| g).collect();
    remove(store, &graphs)?;
    Ok(graphs.len())
}

inventory::submit! { Package { name: "sensing-influxdb", start } }

/// THE ARCHIVER'S START: where it is handed a series store, its task; and none otherwise.
fn start(handed: &Handed) -> Result<Option<Task>, orexis::Error> {
    let Some(archives) = handed.outside.take::<Archives>() else {
        return Ok(None);
    };
    Ok(Some(Box::pin(task(handed.clone(), archives))))
}

/// THE ARCHIVER'S TASK: every stretch of the agent's time it archives what sensing has done with, the write off the
/// agent's threads, and once more as the run ends.
async fn task(handed: Handed, archives: Archives) -> Result<(), orexis::Error> {
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
        let due = due(&handed.store)?;
        if !due.is_empty() {
            let points: Vec<Point> = due.iter().filter_map(|(_, p)| p.clone()).collect();
            let sink = archives.sink.clone();
            let wanted = points.len();
            let took = tokio::task::spawn_blocking(move || sink.write(&points))
                .await
                .unwrap_or(0);
            if took == wanted {
                let graphs: Vec<String> = due.into_iter().map(|(g, _)| g).collect();
                remove(&handed.store, &graphs)?;
                log::debug!("{}: {} past reading(s) archived", handed.id, graphs.len());
            }
        }
        if over {
            break;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_interval_is_the_environments_and_a_minute_where_it_says_nothing() {
        assert_eq!(interval(&|k| (k == INTERVAL).then(|| "300".to_string())), 300.0);
        assert_eq!(interval(&|_| None), INTERVAL_S);
        assert_eq!(interval(&|_| Some("nought".to_string())), INTERVAL_S);
    }
}
