//! PREPARING THE GROUND: what a search over one scope is given — the copy of what crosses from the belief base
//! into the store a pass stands in, as `agent/planning/prepare_ground.py` makes it, and held to its cases. Laying
//! the grounds is `lay_ground`'s, which the Planner calls next: this copies, that builds.
//!
//! **THE ONE FUNCTION OVER TWO STORES**: `beliefs` is read and `into` written, and everything that happens to a
//! possible world afterwards happens to `into` the ordinary way. What crosses: every graph of the kinds a world is
//! made of and a search reads to act ([`CROSSING`]), and the catalogue. **The agent's own beliefs are the scope's**:
//! one whose quads, with its revisions, name members whose scopes meet without this scope stays behind.
//!
//! **A SECOND FILLING IS A REFRESH**: a copy whose source's row states the hash the copy's row was made with is kept,
//! cut as it was, and its row read again; any other copy is taken back with what was cut out of it, and copied
//! again. What the store MADE for itself — its grounds, possible worlds, plans and derived wants — stays.
//!
//! QUADS AND NOT TEXT: a serialise-and-reparse relabels blank nodes, so an observation node would come out the far
//! side unequal to the one a retraction names.

use std::collections::{BTreeSet, HashMap};

use oxigraph::model::{GraphNameRef, NamedOrBlankNode, Quad, Term};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{ACTION, BELIEF, FLOW_GRAPH, RECORD};
use orexis::store::{Store, Within, iri, value};
use orexis_belief::ontology::{REVISION_GRAPH, RULES_GRAPH};

use crate::find_scopes::Scopes;
use crate::ontology::{CONSTRAINT_GRAPH, DERIVATION_GRAPH, DESIRE, SCOPE_GRAPH, SHAPES, WANT};
use crate::world_at::named;

/// THE KINDS THAT CROSS, spelled once for the filling and the refresh: the beliefs a world is made of, and what the
/// search reads to act, each by its own kind, since none of it is a belief (#953).
pub const CROSSING: &[&str] = &[
    DESIRE,
    WANT,
    RECORD,
    BELIEF,
    SCOPE_GRAPH,
    RULES_GRAPH,
    ACTION,
    FLOW_GRAPH,
    DERIVATION_GRAPH,
    SHAPES,
    CONSTRAINT_GRAPH,
];

/// EVERY ROW'S HASH, and every changeable graph with the graph it was cut from.
const HASHES_Q: &str = "SELECT ?g ?h WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g orexis:hash ?h } }";
const PIECES_Q: &str = "SELECT ?piece ?source WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
  ?piece a planning:ChangeableGraph . OPTIONAL { ?piece prov:wasDerivedFrom ?source } } }";
/// A ROW TAKEN BACK, its period with it, and the cut it says it carries left: the graph is the one cut.
const UNDESCRIBE_U: &str = "DELETE { GRAPH $cat { $g ?p ?o . ?o ?pp ?po } }
WHERE { GRAPH $cat { $g ?p ?o . FILTER(?p != planning:cutBy)
                     OPTIONAL { ?o ?pp ?po . FILTER(?p = dcterms:temporal) } } }";

/// WHAT THE STORE MADE FOR ITSELF, which a refresh keeps: planning's kinds, and the wants the derivation minted.
const MADE_Q: &str = "
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    { ?g a ?kind . VALUES ?kind { planning:GroundGraph planning:PossibleGraph planning:PlanGraph } }
    UNION { ?g a planning:WantGraph ; orexis:arrivedBy orexis:Derived } } }";

/// Fill `into` with what a search over `scope` needs from `beliefs`, or refresh what an earlier filling left there.
/// `scopes` is the store's partition as `find_scopes` reads it; handed neither, everything crosses.
pub fn prepare_ground(
    beliefs: &Store,
    into: &Store,
    scope: Option<&str>,
    scopes: Option<&Scopes>,
) -> Result<(), Error> {
    let every = Within::default();
    let made: BTreeSet<String> = into.rows(MADE_Q, &[])?.iter().filter_map(|r| iri(r, "g")).collect();
    let behind = of_another_scope(beliefs, scope, scopes)?;
    let wanted: Vec<String> = beliefs
        .graphs_of(CROSSING, &every)?
        .into_iter()
        .filter(|g| !behind.contains(g))
        .collect();
    let (said, held) = (hashes(beliefs)?, hashes(into)?);
    let kept: BTreeSet<&String> = wanted
        .iter()
        .filter(|g| said.get(*g).is_some_and(|h| held.get(*g) == Some(h)))
        .collect();
    let cut_from: Vec<(String, Option<String>)> = into
        .rows(PIECES_Q, &[])?
        .iter()
        .filter_map(|r| Some((iri(r, "piece")?, iri(r, "source"))))
        .collect();
    for graph in into.graphs_of(CROSSING, &every)? {
        if !made.contains(&graph) && !kept.contains(&graph) {
            into.forget_graph(&graph, None)?;
        }
    }
    for (piece, source) in &cut_from {
        if !source.as_ref().is_some_and(|s| kept.contains(s)) {
            into.forget_graph(piece, None)?;
        }
    }
    if let Some(catalogue) = into.catalogue()? {
        for graph in &kept {
            into.update(&bind(
                UNDESCRIBE_U,
                &[
                    ("cat", Value::Raw(format!("<{catalogue}>"))),
                    ("g", Value::iri(graph.as_str())),
                ],
            )?)?;
        }
    }
    let mut crossing: Vec<String> = wanted.iter().filter(|g| !kept.contains(g)).cloned().collect();
    crossing.extend(beliefs.catalogue()?);
    for graph in crossing {
        let name = named(&graph)?;
        let quads: Vec<Quad> = beliefs
            .engine()
            .quads_for_pattern(None, None, None, Some(GraphNameRef::NamedNode(name.as_ref())))
            .collect::<Result<_, _>>()
            .map_err(|e| Error::Evaluation(e.to_string()))?;
        into.add(quads)?;
    }
    Ok(())
}

/// Every graph `store`'s catalogue says the hash of, and the hash.
fn hashes(store: &Store) -> Result<HashMap<String, String>, Error> {
    Ok(store
        .rows(HASHES_Q, &[])?
        .iter()
        .filter_map(|r| Some((iri(r, "g")?, value(r, "h")?)))
        .collect())
}

/// Every belief of the agent's that is other scopes' alone, with its revisions: a graph whose quads, taken with what
/// was concluded of it, name — as a subject, a predicate or an object — members whose scopes meet without `scope`.
/// Nothing, in a store of one scope or for a caller naming none.
fn of_another_scope(beliefs: &Store, scope: Option<&str>, scopes: Option<&Scopes>) -> Result<BTreeSet<String>, Error> {
    let (Some(scope), Some(scopes)) = (scope, scopes) else {
        return Ok(BTreeSet::new());
    };
    if scopes.all().len() < 2 {
        return Ok(BTreeSet::new());
    }
    let mut behind = BTreeSet::new();
    let every = Within::default();
    let mut skip: BTreeSet<String> = beliefs.graphs_of(&[BELIEF], &Within::common())?.into_iter().collect();
    skip.extend(beliefs.graphs_of(&[REVISION_GRAPH], &every)?);
    for graph in beliefs.graphs_of(&[BELIEF], &every)? {
        if skip.contains(&graph) {
            continue;
        }
        let mut group = vec![graph.clone()];
        group.extend(beliefs.revisions_of(&[&graph], BELIEF)?);
        let mut names: BTreeSet<String> = BTreeSet::new();
        for g in &group {
            for quad in beliefs.quads(g)? {
                names.insert(quad.predicate.into_string());
                if let NamedOrBlankNode::NamedNode(s) = quad.subject {
                    names.insert(s.into_string());
                }
                if let Term::NamedNode(o) = quad.object {
                    names.insert(o.into_string());
                }
            }
        }
        let home = scopes.meet(names.iter().map(String::as_str));
        if !home.is_empty() && !home.contains(scope) {
            behind.extend(group);
        }
    }
    Ok(behind)
}

#[cfg(test)]
mod tests;
