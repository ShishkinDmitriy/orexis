//! THE QUESTIONS AN AGENT SAYS TO THE PEERS IT BELIEVES IN RANGE, as `agent/coordination/ask.py` says them: one per peer
//! and constraint. **WHEN**: a peer is in range where it acts for a thing the agent believes now to hold a value on a
//! constraint's key; the agent asks only under a constraint it holds, and only where its walking plans give its own
//! things values on that key. **WHAT**: the constraint, and the asker's holdings under it, in the question's graph,
//! holding over the asker's patience from when it is asked — said again each time the holdings change, and once it has
//! lapsed, never otherwise, and keeping the start of the first asking.

use std::collections::{BTreeSet, HashSet};

use oxigraph::model::NamedNode;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{instant, seconds};
use orexis::document::Document;
use orexis::ontology::SELF_GRAPH;
use orexis::stance::stance;
use orexis::store::{Store, Within, iri, value};

use crate::holdings::{
    Holding, RDF_TYPE, common, constraints_and_self, heard, holdings, key_of, of_kind, present, rows_of, said,
};
use crate::ontology::{COORDINATION, PATIENCE, PATIENCE_S, QUESTION, QUESTION_GRAPH, question_graph};

/// THE CONSTRAINTS THE AGENT HOLDS.
pub(crate) const HELD_Q: &str =
    "SELECT ?c WHERE { ?me a orexis:Self ; planning:holds ?c . ?c a planning:Constraint } ORDER BY ?c";

/// EVERY OTHER AGENT, and each thing it acts for.
const PEERS_Q: &str = "SELECT ?peer ?t WHERE { ?me a orexis:Self . ?peer a orexis:Agent ; orexis:actsFor ?t . FILTER(?peer != ?me) } ORDER BY ?peer ?t";

const HOLDS_Q: &str = "SELECT ?v WHERE { $thing $p ?v } LIMIT 1";

const BEGAN_Q: &str =
    "SELECT ?start WHERE { GRAPH $cat { $graph dcterms:temporal ?p . ?p orexis:start ?start } } LIMIT 1";

/// The constraints the self of `store` holds.
pub(crate) fn held(store: &Store) -> Result<Vec<String>, Error> {
    Ok(rows_of(store, HELD_Q, &[], &constraints_and_self(store)?)?
        .iter()
        .filter_map(|r| iri(r, "c"))
        .collect())
}

/// How long the agent's patience is, its stance or the package's figure.
pub(crate) fn patience(store: &Store) -> Result<f64, Error> {
    Ok(stance(store, PATIENCE_S)?.unwrap_or(PATIENCE))
}

/// Every question the self `me` of `store` has to say at `at`, with the peer it is to.
pub fn ask(store: &Store, me: &str, at: DateTime) -> Result<Vec<(String, Document)>, Error> {
    let holding: BTreeSet<String> = store
        .graphs_of(&[QUESTION_GRAPH], &Within::at(at))?
        .into_iter()
        .collect();
    let patience = patience(store)?;
    let mut out = Vec::new();
    for constraint in held(store)? {
        let mine = holdings(store, &constraint, at)?;
        if mine.is_empty() {
            continue;
        }
        for peer in in_range(store, me, &key_of(store, &constraint)?, at)? {
            let graph = question_graph(me, &peer, &constraint);
            if holding.contains(&graph) {
                let said: HashSet<Holding> = heard(store, &graph)?.into_iter().collect();
                if said == mine.iter().cloned().collect::<HashSet<_>>() {
                    continue;
                }
            }
            let about = vec![
                (RDF_TYPE.to_string(), NamedNode::new_unchecked(QUESTION).into()),
                (format!("{COORDINATION}asks"), NamedNode::new_unchecked(me).into()),
                (
                    format!("{COORDINATION}over"),
                    NamedNode::new_unchecked(&constraint).into(),
                ),
            ];
            let began = began(store, &graph)?.unwrap_or(at);
            let until = at.checked_add_day_time_duration(seconds(patience)).unwrap_or(at);
            out.push((
                peer,
                said(&graph, QUESTION_GRAPH, &graph, &about, &mine, Some((began, until))),
            ));
        }
    }
    Ok(out)
}

/// When the agent first asked a question it has said before: the start of its period, kept each time it is said.
fn began(store: &Store, graph: &str) -> Result<Option<DateTime>, Error> {
    let Some(cat) = store.catalogue()? else { return Ok(None) };
    let text = bind(BEGAN_Q, &[("cat", Value::iri(cat)), ("graph", Value::iri(graph))])?;
    store
        .rows(&text, &[])?
        .first()
        .and_then(|r| value(r, "start"))
        .map(|s| instant(&s))
        .transpose()
}

/// Every peer acting for a thing the agent believes now to hold a value on `key`.
pub(crate) fn in_range(store: &Store, _me: &str, key: &BTreeSet<String>, at: DateTime) -> Result<Vec<String>, Error> {
    let present = present(store, at)?;
    let mut graphs = common(store)?;
    graphs.extend(of_kind(store, &[SELF_GRAPH])?);
    let mut found: Vec<String> = Vec::new();
    for r in rows_of(store, PEERS_Q, &[], &graphs)? {
        let (Some(peer), Some(thing)) = (iri(&r, "peer"), iri(&r, "t")) else {
            continue;
        };
        if found.contains(&peer) {
            continue;
        }
        for p in key {
            let held = rows_of(
                store,
                HOLDS_Q,
                &[("thing", Value::iri(thing.as_str())), ("p", Value::iri(p.as_str()))],
                &present,
            )?;
            if !held.is_empty() {
                found.push(peer.clone());
                break;
            }
        }
    }
    Ok(found)
}
