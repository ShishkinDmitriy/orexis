//! What a graph HOLDS, asked of the engine one triple at a time, and a list that keeps each item once in the order it
//! came: what the revision, the transitions and the deliberator each asked by hand.

use oxigraph::model::Triple;

use orexis::Error;
use orexis::store::Store;

use crate::ontology::node;

/// Whether `graph` holds `triple`; an engine that cannot answer is an error, never an answer either way.
pub(crate) fn holds(store: &Store, triple: &Triple, graph: &str) -> Result<bool, Error> {
    store
        .engine()
        .contains(&triple.clone().in_graph(node(graph)?))
        .map_err(|e| Error::Evaluation(e.to_string()))
}

/// `item` added to `list` where it is not there yet, keeping the order items came in.
pub(crate) fn push_unique<T: PartialEq>(list: &mut Vec<T>, item: T) {
    if !list.contains(&item) {
        list.push(item);
    }
}
