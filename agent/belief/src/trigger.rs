//! `trigger`: an arrival of testimony triggers every transition once, applied to the agent's own state, order by
//! order, within a budget, as `agent/belief/trigger.py` applies them
//! (a-transition-changes-the-state-and-an-inference-only-concludes).
//!
//! **WHAT TRIGGERS**: a graph whose catalogue row says it arrived `orexis:Received`. Nothing that arrived another way
//! triggers one, so a transition's output can never trigger it again. **WHAT IT READS**: the arrival with its
//! revisions, the common beliefs, and the agent's own derived state graphs, whatever their period — never another
//! testimony. **WHERE IT WRITES**: what an order inserts goes into a state graph of the arrival's own, over the
//! arrival's period; what it deletes is taken out of whichever derived state graph holds it, and one left empty is
//! forgotten. **ONCE, IN ORDER, WITHIN A BUDGET**: an order is applied whole, begun while any budget is left, and
//! where the budget is spent before the last the answer says how many orders are done.

use oxigraph::model::NamedNode;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::instant;
use orexis::hash::hash_named_graph;
use orexis::ontology::{BELIEF, DERIVED};
use orexis::store::{Store, Within, iri, value};

use crate::ontology::{REVISION_GRAPH, state_graph};
use crate::transition::{Change, applied, asked, transitions};

/// WHETHER THE ARRIVAL IS TESTIMONY, WHOSE IT IS AND WHEN IT HOLDS, off its row.
const ARRIVAL_Q: &str = "
SELECT ?owner ?start ?end WHERE {
  GRAPH $cat { $arrival orexis:arrivedBy orexis:Received .
               OPTIONAL { $arrival orexis:ownedBy ?owner }
               OPTIONAL { $arrival dcterms:temporal ?p .
                          OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } } } }
LIMIT 1";

/// EVERY BELIEF THE AGENT DERIVED, of any period, that is no revision: its own state.
const DERIVED_Q: &str = "
SELECT ?g WHERE { GRAPH $cat { ?g a orexis:BeliefGraph ; orexis:arrivedBy orexis:Derived .
                               FILTER NOT EXISTS { ?g a belief:RevisionGraph }
                               ?g orexis:ownedBy ?owner . } } ORDER BY ?g";

/// WHETHER A GRAPH STILL HAS A ROW: one an order emptied was forgotten, row and all.
const ROW_Q: &str = "SELECT ?k WHERE { GRAPH $cat { $graph a ?k } } LIMIT 1";

/// A ROW, AND ITS PERIOD, TAKEN BACK — for an arrival's state graph said again of a later arrival.
const UNDESCRIBE_U: &str = "
DELETE { GRAPH $cat { $graph ?p ?o . ?period ?pp ?po } }
WHERE  { GRAPH $cat { $graph ?p ?o . OPTIONAL { $graph dcterms:temporal ?period . ?period ?pp ?po } } }";

/// What applying the transitions an arrival triggers did: the rule executions it spent, how many of its orders are
/// applied — those before this call included — whether that is all of them, and the agent's own state graphs this
/// call changed.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Triggered {
    pub spent: usize,
    pub done: usize,
    pub finished: bool,
    pub changed: Vec<String>,
}

impl Triggered {
    fn finished(done: usize) -> Self {
        Triggered {
            spent: 0,
            done,
            finished: true,
            changed: Vec::new(),
        }
    }
}

/// Apply the transitions `arrival` triggers to the agent's own state, from its `done`th order on, spending at most
/// `budget` rule executions. An arrival that is no testimony triggers nothing, spends nothing, and is done.
pub fn trigger(store: &Store, arrival: &str, budget: usize, done: usize) -> Result<Triggered, Error> {
    let Some(cat) = store.catalogue()? else {
        return Ok(Triggered::finished(done));
    };
    let found = store.rows(
        &bind(
            ARRIVAL_Q,
            &[("cat", Value::iri(&cat)), ("arrival", Value::iri(arrival))],
        )?,
        &[],
    )?;
    let Some(row) = found.into_iter().next() else {
        return Ok(Triggered::finished(done));
    };
    let orders = transitions(store)?;
    if done >= orders.len() {
        return Ok(Triggered::finished(done));
    }
    let into = state_graph(arrival);
    let common = store.graphs_of(&[BELIEF], &Within::common())?;
    let mut spent = 0;
    let mut changed: Vec<String> = Vec::new();
    for (n, order) in orders.iter().enumerate().skip(done) {
        if spent >= budget {
            log::debug!(
                "the transitions {arrival} triggers are cut short after {n} of {} order(s)",
                orders.len()
            );
            return Ok(Triggered {
                spent,
                done: n,
                finished: false,
                changed: stamped(store, &cat, changed)?,
            });
        }
        let state = derived(store, &cat)?;
        let mut reads: Vec<String> = Vec::new();
        let revisions = store.revisions_of(&[arrival], REVISION_GRAPH)?;
        for g in std::iter::once(arrival.to_string())
            .chain(revisions)
            .chain(common.iter().cloned())
            .chain(state.iter().cloned())
        {
            if !reads.contains(&g) {
                reads.push(g);
            }
        }
        let reads: Vec<&str> = reads.iter().map(String::as_str).collect();
        let change = asked(store, order, &reads, &[]);
        spent += change.executions;
        let state: Vec<&str> = state.iter().map(String::as_str).collect();
        for g in deleted_from(store, &change, &state)? {
            if !changed.contains(&g) {
                changed.push(g);
            }
        }
        let emptied = applied(store, &change, &into, &state)?;
        for graph in emptied {
            if graph != into || change.added.is_empty() {
                store.forget_graph(&graph, Some(BELIEF))?;
            }
        }
        if !change.added.is_empty() {
            describe(store, &cat, &into, &row)?;
            if !changed.contains(&into) {
                changed.push(into.clone());
            }
        }
        if !change.added.is_empty() || !change.deleted.is_empty() {
            log::debug!(
                "{arrival} triggered order {n}: {} deleted, {} added",
                change.deleted.len(),
                change.added.len()
            );
        }
    }
    Ok(Triggered {
        spent,
        done: orders.len(),
        finished: true,
        changed: stamped(store, &cat, changed)?,
    })
}

/// `changed`, each graph still standing stamped with the hash of what it now holds.
fn stamped(store: &Store, cat: &str, changed: Vec<String>) -> Result<Vec<String>, Error> {
    for graph in &changed {
        let row = store.rows(
            &bind(ROW_Q, &[("cat", Value::iri(cat)), ("graph", Value::iri(graph))])?,
            &[],
        )?;
        if !row.is_empty() {
            hash_named_graph(store, graph, None)?;
        }
    }
    Ok(changed)
}

/// The graphs of `targets` holding something `change` deletes.
fn deleted_from(store: &Store, change: &Change, targets: &[&str]) -> Result<Vec<String>, Error> {
    let mut out = Vec::new();
    for g in targets {
        let name = NamedNode::new(*g).map_err(|e| Error::Evaluation(e.to_string()))?;
        for t in &change.deleted {
            let quad = t.clone().in_graph(name.clone());
            if store
                .engine()
                .contains(&quad)
                .map_err(|e| Error::Evaluation(e.to_string()))?
            {
                out.push(g.to_string());
                break;
            }
        }
    }
    Ok(out)
}

/// Every state graph the agent derived, whatever its period.
fn derived(store: &Store, cat: &str) -> Result<Vec<String>, Error> {
    Ok(store
        .rows(&bind(DERIVED_Q, &[("cat", Value::iri(cat))])?, &[])?
        .iter()
        .filter_map(|r| iri(r, "g"))
        .collect())
}

/// The arrival's state graph's row, said of the arrival it now holds the state of, any row of an earlier arrival
/// taken back first.
fn describe(store: &Store, cat: &str, into: &str, row: &orexis::store::Row) -> Result<(), Error> {
    store.update(&bind(
        UNDESCRIBE_U,
        &[("cat", Value::iri(cat)), ("graph", Value::iri(into))],
    )?)?;
    let when = |k: &str| value(row, k).and_then(|t| instant(&t).ok());
    let entry = store.entry(
        into,
        &[BELIEF],
        DERIVED,
        iri(row, "owner").as_deref(),
        when("start"),
        when("end"),
    )?;
    store.update(&format!("INSERT DATA {{ {entry} }}"))
}

#[cfg(test)]
mod tests {
    //! `trigger`, one case per file, held to the diff the Python suite wrote (`agent/belief/tests/test_trigger.py`).

    use std::collections::BTreeMap;
    use std::path::PathBuf;

    use orexis::ontology::RECORD;
    use orexis::snapshots;

    use super::*;
    use crate::revise::{BUDGET, revise};

    const T: &str = "http://example.org/test#";
    const TICK: &str = "http://example.org/test#tick2";
    const HELD_Q: &str = "SELECT ?p ?o WHERE { <http://example.org/test#counter> ?p ?o FILTER(?p != rdf:type) }";
    const OWN_STATE_Q: &str = "SELECT ?g WHERE { GRAPH ?c { ?c a orexis:CatalogueGraph .
    ?g a orexis:BeliefGraph ; orexis:arrivedBy orexis:Derived .
    FILTER NOT EXISTS { ?g a belief:RevisionGraph } ?g orexis:ownedBy ?owner . } } ORDER BY ?g";

    fn cases() -> PathBuf {
        snapshots::tree().join("belief/tests/trigger")
    }

    fn case(name: &str) -> Store {
        snapshots::stand_in(&cases().join(format!("{name}.trig")))
    }

    fn t(local: &str) -> String {
        format!("{T}{local}")
    }

    fn held(store: &Store) -> BTreeMap<String, String> {
        let own: Vec<String> = store
            .rows(OWN_STATE_Q, &[])
            .unwrap()
            .iter()
            .filter_map(|r| iri(r, "g"))
            .collect();
        let own: Vec<&str> = own.iter().map(String::as_str).collect();
        store
            .rows(HELD_Q, &own)
            .unwrap()
            .iter()
            .map(|r| {
                (
                    value(r, "p").unwrap().rsplit('#').next().unwrap().to_string(),
                    value(r, "o").unwrap(),
                )
            })
            .collect()
    }

    fn map(items: &[(&str, &str)]) -> BTreeMap<String, String> {
        items.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect()
    }

    fn triggered(spent: usize, done: usize, finished: bool, changed: &[&str]) -> Triggered {
        Triggered {
            spent,
            done,
            finished,
            changed: changed.iter().map(|c| t(c)).collect(),
        }
    }

    #[test]
    fn trigger_changes_what_the_patch_says() {
        for case in snapshots::cases_in(&cases()) {
            let store = snapshots::stand_in(&case);
            assert!(trigger(&store, TICK, BUDGET, 0).unwrap().finished);
            snapshots::held_to_diff(&case, &store, "trigger");
        }
    }

    #[test]
    fn every_case_is_read_and_no_diff_is_orphaned() {
        snapshots::all_read(&cases(), 1);
    }

    #[test]
    fn a_graph_that_is_no_testimony_triggers_nothing() {
        let store = case("a_state_is_replaced_where_it_stood");
        assert_eq!(
            trigger(&store, &t("world"), BUDGET, 0).unwrap(),
            triggered(0, 0, true, &[])
        );
        assert_eq!(
            trigger(&store, &t("tick1/believed"), BUDGET, 0).unwrap(),
            triggered(0, 0, true, &[])
        );
        assert_eq!(held(&store), map(&[("count", "1")]));
        assert_eq!(
            trigger(&store, TICK, BUDGET, 0).unwrap(),
            triggered(1, 1, true, &["tick1/believed", "tick2/believed"]),
            "the state graphs it changed: the count taken out where it stood, and put in the tick's own (#944)"
        );
        assert_eq!(held(&store), map(&[("count", "2")]));
    }

    #[test]
    fn an_order_is_applied_whole_and_a_cut_is_continued_to_the_same_state() {
        let whole = case("two_transitions_of_one_order_read_the_same_state");
        let changed = ["tick1/believed", "tick2/believed"];
        assert_eq!(
            trigger(&whole, TICK, BUDGET, 0).unwrap(),
            triggered(3, 2, true, &changed)
        );
        let store = case("two_transitions_of_one_order_read_the_same_state");
        let first = trigger(&store, TICK, 1, 0).unwrap();
        assert_eq!(first, triggered(2, 1, false, &changed));
        assert_eq!(
            held(&store),
            map(&[("count", "2"), ("saw", "1")]),
            "the first order whole, and nothing of the second"
        );
        assert_eq!(
            trigger(&store, TICK, BUDGET, first.done).unwrap(),
            triggered(1, 2, true, &["tick2/believed"])
        );
        assert_eq!(held(&store), held(&whole));
        assert_eq!(held(&store), map(&[("count", "2"), ("saw", "1"), ("echo", "2")]));
    }

    #[test]
    fn a_transition_is_no_inference() {
        let store = case("a_state_is_replaced_where_it_stood");
        store
            .update(
                r#"INSERT DATA { GRAPH <http://example.org/test#rules> { <http://example.org/test#countRule>
        a sh:SPARQLRule , sh:Rule ;
        sh:construct "CONSTRUCT { ?c <http://example.org/test#count> 9 } WHERE { ?c a <http://example.org/test#Counter> }" } }"#,
            )
            .unwrap();
        let known = store.graphs_of(&[BELIEF, RECORD], &Within::default()).unwrap();
        assert_eq!(revise(&store, TICK, &known, BUDGET, BELIEF).unwrap(), 0);
        assert_eq!(held(&store), map(&[("count", "1")]));
        assert!(
            store
                .rows("SELECT ?g WHERE { GRAPH ?c { ?g a belief:RevisionGraph } }", &[])
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn an_arrivals_state_graph_said_again_takes_the_later_arrivals_period() {
        let store = case("a_state_is_replaced_where_it_stood");
        trigger(&store, TICK, BUDGET, 0).unwrap();
        store
            .update(&format!(
                r#"DELETE {{ GRAPH ?c {{ ?p orexis:start ?s . ?p orexis:end ?e }} }}
INSERT {{ GRAPH ?c {{ ?p orexis:start "2026-01-01T12:20:00+00:00"^^xsd:dateTime .
                     ?p orexis:end "2026-01-01T12:40:00+00:00"^^xsd:dateTime }} }}
WHERE {{ GRAPH ?c {{ <{TICK}> dcterms:temporal ?p . ?p orexis:start ?s ; orexis:end ?e }} }}"#
            ))
            .unwrap();
        trigger(&store, TICK, BUDGET, 0).unwrap();
        let periods = store
            .rows(
                &format!(
                    "SELECT ?s ?e WHERE {{ GRAPH ?c {{ <{TICK}/believed> dcterms:temporal ?p . ?p orexis:start ?s ; \
                     orexis:end ?e }} }}"
                ),
                &[],
            )
            .unwrap();
        let said: Vec<(String, String)> = periods
            .iter()
            .map(|p| {
                (
                    value(p, "s").unwrap()[..19].to_string(),
                    value(p, "e").unwrap()[..19].to_string(),
                )
            })
            .collect();
        assert_eq!(
            said,
            [("2026-01-01T12:20:00".to_string(), "2026-01-01T12:40:00".to_string())]
        );
        assert_eq!(held(&store), map(&[("count", "3")]));
    }
}
