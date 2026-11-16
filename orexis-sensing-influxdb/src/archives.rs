//! WHAT ARCHIVES: where readings are archived and how often, what the store took this run, and what a turn has to do
//! - every reading whose point the store does not hold, and every past percept, forgotten once the store took it.

use std::collections::BTreeMap;
use std::sync::Arc;

use orexis::events::Point;
use orexis::series::Sink;
use orexis::store::Store;
use orexis_sensing::past;

/// How often readings are archived, in the agent's seconds, where no observer's role says: the default sensing's
/// ontology states on the observer's shape, for an archiver a test makes with no role to read.
pub fn archived_every_s() -> Result<f64, orexis::Error> {
    orexis_sensing::ontology::DEFAULTS.figure("http://example.org/orexis/sensing#archivedEveryS")
}

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
