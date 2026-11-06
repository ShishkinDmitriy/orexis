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
mod tests {
    //! `prepare_ground`, held to `agent/planning/tests/prepare_ground/`'s cases as `test_prepare_ground.py` holds the
    //! Python act — the store it FILLS is the diff — and to its tests beside them.

    use std::collections::BTreeSet;
    use std::path::PathBuf;

    use oxigraph::model::{GraphName, Literal, NamedNode, Quad};

    use orexis::snapshots;

    use super::*;
    use crate::lay_ground::{Laying, lay_ground};
    use crate::ontology::GROUND_GRAPH;

    fn cases() -> PathBuf {
        snapshots::tree().join("planning/tests/prepare_ground")
    }

    fn empty() -> Store {
        Store::new(snapshots::namespaces()).expect("an empty store")
    }

    #[test]
    fn prepare_ground_fills_the_store_as_the_diff_says() {
        for case in snapshots::cases_in(&cases()) {
            let into = empty();
            prepare_ground(&snapshots::stand_in(&case), &into, None, None).unwrap();
            snapshots::held_to_diff(&case, &into, "prepare_ground");
        }
    }

    #[test]
    fn every_case_is_read_and_no_diff_is_orphaned() {
        snapshots::all_read(&cases(), 3);
    }

    #[test]
    fn a_second_filling_refreshes_the_copy_and_keeps_what_the_store_made() {
        let beliefs = snapshots::stand_in(&cases().join("a_forecast_holding_later_crosses_whole.trig"));
        let into = empty();
        prepare_ground(&beliefs, &into, None, None).unwrap();
        lay_ground(&into, snapshots::now(), &Laying::default()).unwrap();
        let grounds = into.graphs_of(&[GROUND_GRAPH], &Within::default()).unwrap();
        assert!(!grounds.is_empty(), "the store made grounds of its own");
        //  A WANT THE DERIVATION MINTED is a kind that crosses too, told apart by how it arrived: no want crosses that
        //  way, since the derivation runs in here and nowhere else.
        let minted = "urn:test:minted";
        let catalogue = into.catalogue().unwrap().unwrap();
        into.update(&format!(
            "INSERT DATA {{ GRAPH <{minted}> {{ <urn:test:w> a planning:Want }}
           GRAPH <{catalogue}> {{ <{minted}> a planning:WantGraph ; orexis:arrivedBy orexis:Derived }} }}"
        ))
        .unwrap();
        let crossing = beliefs.graphs_of(CROSSING, &Within::default()).unwrap();
        let (replaced, swept) = (&crossing[0], &crossing[1]);
        let old = beliefs.quads(replaced).unwrap().remove(0);
        beliefs.remove_all(std::slice::from_ref(&old)).unwrap();
        let new = Quad::new(
            old.subject.clone(),
            old.predicate.clone(),
            Literal::new_simple_literal("moved on"),
            GraphName::NamedNode(NamedNode::new(replaced).unwrap()),
        );
        beliefs.add([new.clone()]).unwrap();
        beliefs.forget_graph(swept, Some(BELIEF)).unwrap();
        prepare_ground(&beliefs, &into, None, None).unwrap();
        let held = into.quads(replaced).unwrap();
        assert!(
            held.contains(&new) && !held.contains(&old),
            "the row replaced, not laid beside the old one"
        );
        assert!(
            !into.graph_names().unwrap().contains(swept),
            "the graph the beliefs swept is gone from the copy"
        );
        assert_eq!(
            into.graphs_of(&[GROUND_GRAPH], &Within::default()).unwrap(),
            grounds,
            "what the store made stays"
        );
        assert!(
            !into.quads(minted).unwrap().is_empty(),
            "and so does the want it minted"
        );
    }

    fn names(store: &Store) -> BTreeSet<String> {
        store.graph_names().unwrap().into_iter().collect()
    }

    fn filled(beliefs: &Store, scope: Option<&str>, scopes: Option<&Scopes>) -> BTreeSet<String> {
        let into = empty();
        prepare_ground(beliefs, &into, scope, scopes).unwrap();
        names(&into)
    }

    fn scopes(members: &[(&str, &[&str])]) -> Scopes {
        Scopes(
            members
                .iter()
                .map(|(m, s)| (m.to_string(), s.iter().map(|s| s.to_string()).collect()))
                .collect(),
        )
    }

    #[test]
    fn a_reading_keyed_by_another_scopes_term_stays_behind_with_its_revisions_and_its_prediction() {
        let beliefs = snapshots::stand_in(&cases().join("a_readings_revisions_cross_with_it.trig"));
        let soils: BTreeSet<String> = ["sensed", "sensed_revisions", "drying_stops", "drying_stops_revisions"]
            .iter()
            .map(|l| format!("http://example.org/test#{l}"))
            .collect();
        let (soil, air) = ("urn:test:soil", "urn:test:air");
        let (moisture, temperature, bed) = (
            "http://example.org/test#SoilMoisture",
            "urn:test:AirTemperature",
            "http://example.org/test#bed",
        );
        let whole = filled(&beliefs, None, None);
        assert!(soils.is_subset(&whole), "with no other scope, every reading crosses");
        let one = scopes(&[(moisture, &[soil])]);
        assert_eq!(
            filled(&beliefs, Some(soil), Some(&one)),
            whole,
            "one scope in the partition is a store of one scope: everything crosses"
        );
        let parted = scopes(&[(moisture, &[soil]), (temperature, &[air])]);
        let less: BTreeSet<String> = whole.difference(&soils).cloned().collect();
        let into = empty();
        prepare_ground(&beliefs, &into, Some(air), Some(&parted)).unwrap();
        assert_eq!(
            names(&into),
            less,
            "the soil's reading, its side and its prediction are another scope's"
        );
        prepare_ground(&beliefs, &into, None, None).unwrap();
        assert_eq!(names(&into), whole, "a refresh for a store of one scope brings them");
        prepare_ground(&beliefs, &into, Some(air), Some(&parted)).unwrap();
        assert_eq!(names(&into), less, "and a refresh for the air's scope takes them back");
        let apart = scopes(&[(moisture, &[soil]), (temperature, &[air]), (bed, &[air])]);
        assert_eq!(
            filled(&beliefs, Some(air), Some(&apart)),
            whole,
            "a reading naming a member of each scope, held together by neither, is each scope's"
        );
        let shared = scopes(&[(moisture, &[soil]), (temperature, &[air]), (bed, &[soil, air])]);
        assert_eq!(
            filled(&beliefs, Some(air), Some(&shared)),
            less,
            "a bed of two scopes and a property of one meet in the one"
        );
        assert_eq!(filled(&beliefs, Some(soil), Some(&shared)), whole);
    }
}
