//! A STANCE: a figure the agent states of itself, a triple about the self in its self graph, read there alone, as
//! `agent/stance.py` reads it — the patience, the budgets, the horizon, each declared by its reader's package
//! (a-stance-is-the-agents-word-about-itself).

use crate::Error;
use crate::bind::{Value, bind};
use crate::ontology::{SELF_GRAPH, local_of};
use crate::store::{Store, Within, value};

/// The figure `term` the self states of itself in its self graph, or None where it states none, several, or one
/// that is no number — where the reader's package's constant holds.
pub fn stance(store: &Store, term: &str) -> Result<Option<f64>, Error> {
    let selves = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
    let selves: Vec<&str> = selves.iter().map(String::as_str).collect();
    let text = bind(
        "SELECT ?n WHERE { ?me a orexis:Self ; $stance ?n }",
        &[("stance", Value::iri(term))],
    )?;
    let found = store.rows(&text, &selves)?;
    if found.len() != 1 {
        if !found.is_empty() {
            log::warn!(
                "the self states {} figures for {}: the default holds",
                found.len(),
                local_of(term)
            );
        }
        return Ok(None);
    }
    let figure = value(&found[0], "n");
    let parsed = figure.as_deref().and_then(|n| n.parse().ok());
    if parsed.is_none() {
        log::warn!(
            "the self states {figure:?} for {}, which is no number: the default holds",
            local_of(term)
        );
    }
    Ok(parsed)
}
