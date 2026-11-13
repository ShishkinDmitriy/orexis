//! THE READINGS SENSING HAS DONE WITH. A sensor's last `sensing:stuckAfter` percepts are what sensing's rules read,
//! and `received` keeps exactly those in the kind the rules ask, `sensing:ObservationGraph`. An older one it does
//! not forget: it FILES IT PAST, the percept and what was concluded of it, in `sensing:PastObservationGraph`. So how
//! many readings the rules see is sensing's logic, and what becomes of one done with is housekeeping, another's:
//! where the agent has a series store, what archives a past reading there forgets it, and where it has none the
//! reading stays where it lies.
//!
//! WHAT IS ASKED OF SENSING HERE, by whoever keeps house above it: which readings are past, the point each is in
//! the series, and to forget one. The graphs are sensing's, and sensing's code is what removes them.

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::instant;
use orexis::events::{Event, Point, round6};
use orexis::store::{Store, Within, iri, value};

use crate::events::{Observed, tag_of};
use crate::ontology::{OBSERVATION_GRAPH, PAST_OBSERVATION_GRAPH};

/// What an observation graph and its revisions say of the reading: asked over them alone.
pub(crate) const OBSERVED_Q: &str = "
SELECT ?sensor ?feature ?property ?value ?scaled ?defect ?t ?raw ?previous WHERE {
  ?o sosa:madeBySensor ?sensor ; sosa:resultTime ?t ; sosa:hasFeatureOfInterest ?feature ;
     sosa:observedProperty ?property
  OPTIONAL { ?o sosa:hasSimpleResult ?value } OPTIONAL { ?o sensing:scaledResult ?scaled }
  OPTIONAL { ?o sensing:defect ?defect }
  OPTIONAL { ?o sensing:rawResult ?raw } OPTIONAL { ?o sensing:previous ?previous } } LIMIT 1";

const REFILE_U: &str = "
DELETE { GRAPH $cat { ?g a $from } } INSERT { GRAPH $cat { ?g a $to } }
WHERE  { GRAPH $cat { VALUES ?g { $graphs } ?g a $from } }";

/// What a percept says of its reading: the observation, the sensor that made it, and the percept before it where it
/// names one.
pub(crate) type Seen = (Observed, String, Option<String>);

/// The observation the percept `graph` holds, read with its revisions of `kind`. None where the graph holds no
/// reading a point can be made of.
pub(crate) fn observed(store: &Store, graph: &str, kind: &str) -> Result<Option<Seen>, Error> {
    let mut read = vec![graph.to_string()];
    read.extend(store.revisions_of(&[graph], kind)?);
    let read: Vec<&str> = read.iter().map(String::as_str).collect();
    let Some(o) = store.rows(OBSERVED_Q, &read)?.into_iter().next() else {
        return Ok(None);
    };
    let number = |key: &str| value(&o, key).and_then(|v| v.parse::<f64>().ok());
    let defective = o.contains_key("defect");
    let Some(reading) = number("value").or_else(|| if defective { number("scaled") } else { None }) else {
        return Ok(None);
    };
    let (Some(sensor), Some(t)) = (iri(&o, "sensor"), value(&o, "t")) else {
        return Ok(None);
    };
    Ok(Some((
        Observed {
            observed_property: iri(&o, "property").unwrap_or_default(),
            value: round6(reading),
            at: instant(&t)?,
            sensor: Some(tag_of(&sensor)),
            sensor_id: Some(tag_of(&sensor)),
            feature_id: iri(&o, "feature").map(|f| tag_of(&f)),
            interval_s: None,
            cadence_s: None,
            raw: number("raw").map(round6),
            defective,
        },
        sensor,
        iri(&o, "previous"),
    )))
}

/// File the percept `graph` past, and what was concluded of it: sensing has done reading it.
pub(crate) fn shelve(store: &Store, graph: &str) -> Result<(), Error> {
    let Some(cat) = store.catalogue()? else { return Ok(()) };
    let mut graphs = vec![graph.to_string()];
    graphs.extend(store.revisions_of(&[graph], OBSERVATION_GRAPH)?);
    let graphs = graphs.iter().map(|g| format!("<{g}>")).collect::<Vec<_>>().join(" ");
    store.update(&bind(
        REFILE_U,
        &[
            ("cat", Value::iri(cat)),
            ("from", Value::iri(OBSERVATION_GRAPH)),
            ("to", Value::iri(PAST_OBSERVATION_GRAPH)),
            ("graphs", Value::Raw(graphs)),
        ],
    )?)
}

/// Every percept filed past, oldest first by name: the readings sensing has done with and nobody removed.
pub fn past(store: &Store) -> Result<Vec<String>, Error> {
    let mut found = Vec::new();
    for graph in store.graphs_of(&[PAST_OBSERVATION_GRAPH], &Within::default())? {
        //  A PERCEPT, and not what was concluded of one: a revision is derived from its percept, and goes with it.
        if !is_revision(store, &graph)? {
            found.push(graph);
        }
    }
    found.sort();
    Ok(found)
}

fn is_revision(store: &Store, graph: &str) -> Result<bool, Error> {
    let Some(cat) = store.catalogue()? else {
        return Ok(false);
    };
    store.ask(
        &format!("ASK {{ GRAPH <{cat}> {{ <{graph}> <http://www.w3.org/ns/prov#wasDerivedFrom> ?source }} }}"),
        &[],
    )
}

/// The point the past percept `graph` is in the series, as it was said when observed; None where it holds no reading.
pub fn point(store: &Store, graph: &str) -> Result<Option<Point>, Error> {
    Ok(observed(store, graph, PAST_OBSERVATION_GRAPH)?.and_then(|(o, _, _)| o.point()))
}

/// Forget the past percept `graph`, and what was concluded of it.
pub fn forget(store: &Store, graph: &str) -> Result<(), Error> {
    store.forget_graph(graph, Some(PAST_OBSERVATION_GRAPH))
}
