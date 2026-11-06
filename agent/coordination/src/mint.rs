//! THE SECRET AN AGENT DRAWS ITS NUMBERS FROM, as `agent/coordination/mint.py` mints it the first time the package
//! starts: random, kept in a belief of the agent's own, and in no document a peer could read — a draw's number is a
//! hash of it and the draw's name, so nothing is kept per draw and a test that states the secret fixes every number.

use orexis::Error;
use orexis::hash::hash_named_graph;
use orexis::ontology::{BELIEF, DERIVED};
use orexis::store::Store;

use crate::holdings::{of_kind, rows_of};
use crate::ontology::{SECRET, secret_graph};

const HELD_Q: &str = "SELECT ?s WHERE { ?me a orexis:Self ; coordination:secret ?s } LIMIT 1";

/// Mint the secret of the self `me` of `store` where it holds none; the graph written, or none.
pub fn mint(store: &Store, me: &str) -> Result<Vec<String>, Error> {
    if !rows_of(store, HELD_Q, &[], &of_kind(store, &[BELIEF])?)?.is_empty() {
        return Ok(Vec::new());
    }
    let mut bytes = [0u8; 32];
    getrandom::fill(&mut bytes).map_err(|e| Error::Evaluation(format!("no secret could be drawn: {e}")))?;
    let token: String = bytes.iter().map(|b| format!("{b:02x}")).collect();
    let graph = secret_graph(me);
    let entry = store.entry(&graph, &[BELIEF], DERIVED, Some(me), None, None)?;
    store.update(&format!(
        "INSERT DATA {{ GRAPH <{graph}> {{ <{me}> <{SECRET}> \"{token}\" }}\n  {entry} }}"
    ))?;
    hash_named_graph(store, &graph, None)?;
    Ok(vec![graph])
}
