//! WITHDRAWING WHAT THE DERIVATION NO LONGER IMPLIES — the pass-level sweep, and the second of the two things that
//! ever happen to a want, as `agent/planning/withdraw.py` withdraws them. A want is one-shot: a derived want the
//! derivation's answer does not name goes, and so does one reached, however it arrived, with what the search wrote
//! about it. One want in a graph of wants is the whole graph; a record is somebody else's house, and only the want
//! goes.

use std::collections::BTreeSet;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::BELIEF;
use orexis::store::{Store, iri, value};

use crate::ontology::WANT;

/// WHERE A WANT IS: the graph of wants or the record that holds it, and how many wants are in it.
const HOME_Q: &str = "
SELECT ?g ?kind (COUNT(DISTINCT ?w) AS ?wants) WHERE {
  GRAPH ?g { $want a planning:Want . ?w a planning:Want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind .
               VALUES ?kind { planning:WantGraph orexis:RecordGraph } } }
GROUP BY ?g ?kind";

/// TAKE ONE WANT OUT OF A GRAPH THAT HOLDS OTHERS: everything reachable from it by a path of any predicate, and the
/// rows that point at it.
pub const FORGET_ONE_U: &str = "DELETE { GRAPH $graph { ?s ?p ?o } }
WHERE  { GRAPH $graph { $want (<urn:x>|!<urn:x>)* ?s . ?s ?p ?o } } ;
DELETE { GRAPH $graph { ?s ?p $want } }
WHERE  { GRAPH $graph { ?s ?p $want } }";

/// EVERY WANT THE DERIVATION MINTED, across all time.
const DERIVED_Q: &str = "
SELECT ?w WHERE {
  GRAPH ?g { ?w a planning:Want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g a planning:WantGraph ; orexis:arrivedBy orexis:Derived } }";

const WEIGHINGS_U: &str = "
DELETE { GRAPH ?cat { ?x ?p ?o . ?v ?vp ?vo } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                      ?x a planning:Weighing ; planning:for $want ; ?p ?o .
                      OPTIONAL { ?x planning:violation ?v . ?v ?vp ?vo } } }";

const PLAN_Q: &str = "
SELECT ?plan WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?plan a planning:PlanGraph }
  GRAPH ?plan { ?plan planning:for $want } }";

const STEP_GRAPHS_Q: &str = "SELECT ?g WHERE { GRAPH $plan { ?step execution:adds|execution:retracts ?g } }";

/// Drop every derived want `wanted` does not name, and every want in `reached` however it arrived; what went, in
/// name order. `wanted` None judges no derived want. `afresh` are wants whose search alone is withdrawn and which
/// stay: a walking want a belief arriving reopened (#921).
pub fn withdraw(
    store: &Store,
    wanted: Option<&BTreeSet<String>>,
    reached: &BTreeSet<String>,
    afresh: &BTreeSet<String>,
) -> Result<Vec<String>, Error> {
    let standing: BTreeSet<String> = match wanted {
        Some(_) => store.rows(DERIVED_Q, &[])?.iter().filter_map(|r| iri(r, "w")).collect(),
        None => BTreeSet::new(),
    };
    let stale: BTreeSet<String> = standing
        .iter()
        .filter(|w| !wanted.is_some_and(|named| named.contains(*w)))
        .cloned()
        .collect();
    let done: BTreeSet<String> = reached.difference(&stale).cloned().collect();
    let mut gone = Vec::new();
    for uri in stale.union(&done) {
        forget_want(store, uri)?;
        forget_search(store, uri)?;
        log::info!(
            "{} withdrawn: {}",
            uri.rsplit('#').next().unwrap_or(uri),
            if done.contains(uri) {
                "reached"
            } else {
                "its desire no longer reads it unmet"
            }
        );
        gone.push(uri.clone());
    }
    for uri in afresh.iter().filter(|w| !gone.contains(*w)) {
        forget_search(store, uri)?;
        log::info!(
            "{} searched afresh: a belief arriving reopened it",
            uri.rsplit('#').next().unwrap_or(uri)
        );
    }
    Ok(gone)
}

/// Drop what a search wrote about one want: every weighing for it and its plan, with the graphs its steps predict in.
fn forget_search(store: &Store, uri: &str) -> Result<(), Error> {
    store.update(&bind(WEIGHINGS_U, &[("want", Value::iri(uri))])?)?;
    for row in store.rows(&bind(PLAN_Q, &[("want", Value::iri(uri))])?, &[])? {
        let Some(plan) = iri(&row, "plan") else { continue };
        for g in store.rows(&bind(STEP_GRAPHS_Q, &[("plan", Value::iri(plan.as_str()))])?, &[])? {
            if let Some(g) = iri(&g, "g") {
                store.forget_graph(&g, Some(BELIEF))?;
            }
        }
        store.forget_graph(&plan, Some(BELIEF))?;
    }
    Ok(())
}

/// Remove one want, wherever it lives: its graph where a graph of wants holds it alone, the want alone otherwise.
pub fn forget_want(store: &Store, uri: &str) -> Result<(), Error> {
    let mut home: Vec<(String, String, usize)> = store
        .rows(&bind(HOME_Q, &[("want", Value::iri(uri))])?, &[])?
        .iter()
        .filter_map(|r| Some((iri(r, "g")?, iri(r, "kind")?, value(r, "wants")?.parse().ok()?)))
        .collect();
    if home.is_empty() {
        return Ok(());
    }
    home.sort_by_key(|(_, kind, _)| kind != WANT);
    let (graph, kind, wants) = &home[0];
    if kind == WANT && *wants == 1 {
        return store.forget_graph(graph, Some(BELIEF));
    }
    forget_one(store, graph, uri)
}

/// Take `want` out of `graph`, leaving what else it holds.
pub fn forget_one(store: &Store, graph: &str, want: &str) -> Result<(), Error> {
    store.update(&bind(
        FORGET_ONE_U,
        &[("graph", Value::iri(graph)), ("want", Value::iri(want))],
    )?)
}

#[cfg(test)]
mod tests {
    //! Withdrawing what the derivation no longer implies, held to what `test_withdraw.py` holds the Python act to.

    use crate::find_wants::tests::{at, derived, graph_of, owed, store};
    use crate::find_wants::{Finding, find_wants};

    use super::*;

    fn set(uris: &[&str]) -> BTreeSet<String> {
        uris.iter().map(|u| u.to_string()).collect()
    }

    fn found(store: &Store) -> Vec<String> {
        find_wants(store, at(), &Finding::default()).unwrap()
    }

    #[test]
    fn a_want_the_derivation_no_longer_implies_goes_and_the_named_one_stays() {
        let store = store();
        derived(&store, "urn:test:a", at(), None);
        derived(&store, "urn:test:b", at(), None);
        let none = BTreeSet::new();
        assert_eq!(
            withdraw(&store, Some(&set(&["urn:test:a"])), &none, &none).unwrap(),
            ["urn:test:b"]
        );
        assert_eq!(found(&store), ["urn:test:a"]);
    }

    #[test]
    fn a_debt_is_not_the_derivations_to_withdraw_until_it_is_reached() {
        let store = store();
        owed(&store, "urn:test:owed");
        let none = BTreeSet::new();
        assert!(withdraw(&store, Some(&none), &none, &none).unwrap().is_empty());
        assert_eq!(found(&store), ["urn:test:owed"], "the ledger's, and it stands");
        store
        .update("INSERT DATA { GRAPH <http://example.org/orexis/market#obligations/gardener/owed> { <urn:test:history> a <urn:test:Entry> } }")
        .unwrap();
        assert_eq!(
            withdraw(&store, None, &set(&["urn:test:owed"]), &none).unwrap(),
            ["urn:test:owed"],
            "reached, whoever wrote it"
        );
        assert!(found(&store).is_empty());
        assert_eq!(
            store
                .quads("http://example.org/orexis/market#obligations/gardener/owed")
                .unwrap()
                .len(),
            1,
            "and the record keeps what else it holds"
        );
    }

    #[test]
    fn forgetting_a_want_leaves_nothing_behind() {
        let store = store();
        derived(&store, "urn:test:want", at(), None);
        let none = BTreeSet::new();
        assert_eq!(withdraw(&store, Some(&none), &none, &none).unwrap(), ["urn:test:want"]);
        assert!(
            find_wants(
                &store,
                at(),
                &Finding {
                    uri: Some("urn:test:want"),
                    ..Finding::default()
                }
            )
            .unwrap()
            .is_empty()
        );
        let graph = graph_of(at(), None);
        assert!(
            store
                .rows(
                    &format!("SELECT ?p WHERE {{ GRAPH <urn:test:catalogue> {{ <{graph}> ?p ?o }} }}"),
                    &[]
                )
                .unwrap()
                .is_empty(),
            "and the catalogue says nothing of its graph"
        );
    }

    #[test]
    fn one_want_of_two_in_a_graph_goes_alone() {
        let store = store();
        derived(&store, "urn:test:a", at(), None);
        derived(&store, "urn:test:b", at(), None);
        forget_want(&store, "urn:test:a").unwrap();
        assert_eq!(
            found(&store),
            ["urn:test:b"],
            "the graph of the stretch stays for the other"
        );
        let held = store.quads(&graph_of(at(), None)).unwrap();
        assert!(
            held.iter().all(|q| !q.to_string().contains("urn:test:a>")),
            "and nothing of the one is left"
        );
    }
}
