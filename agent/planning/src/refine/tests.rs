//! `refine`, held to what `test_refine.py` holds the Python act to: the tower's shape at its smallest.

use orexis::snapshots;

use super::*;

const ME: &str = "http://example.org/test#mover";
const STEP: &str = "http://example.org/test#step";
const T: &str = "http://example.org/test#";

const CASE: &str = r#"
@prefix : <http://example.org/test#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

GRAPH :catalogue {
  :catalogue a orexis:CatalogueGraph , orexis:Graph .
  :rules a sh:RulesGraph , orexis:Graph .
  :state a orexis:BeliefGraph , orexis:Graph .
}
GRAPH :rules {
  :stands a sh:SPARQLRule ; sh:construct """PREFIX : <http://example.org/test#>
    CONSTRUCT { ?disk :on ?peg } WHERE { ?disk :at ?cell . ?peg a :Peg ; :at ?cell }""" .
  :twice a sh:SPARQLRule ; sh:construct """PREFIX : <http://example.org/test#>
    CONSTRUCT { ?disk :near ?peg . ?peg :near ?disk } WHERE { ?disk :at ?cell . ?peg :at ?cell }""" .
}
GRAPH :state {
  :pegA a :Peg ; :at :c1 .  :pegB a :Peg ; :at :c2 .
  :d :at :c1 ; :on :pegA .  :e :at :c1 ; :on :pegA .
}
"#;

pub(crate) fn store() -> Store {
    let store = Store::new(snapshots::namespaces()).expect("an empty store");
    store.put_trig(&format!("{T}state"), CASE).unwrap();
    store.close_catalogue().unwrap();
    store
}

/// The step as a plan's extraction writes one: its two graphs, named off it, holding what it adds and retracts.
pub(crate) fn predicting(store: &Store, adds: &str, retracts: &str) -> String {
    store
        .update(&format!(
            "PREFIX : <{T}>
INSERT DATA {{
  GRAPH <{T}plan> {{ <{STEP}> a execution:Step ; execution:adds <{STEP}.adds> ; execution:retracts <{STEP}.retracts> }}
  GRAPH <{STEP}.adds> {{ {adds} }}
  GRAPH <{STEP}.retracts> {{ {retracts} }} }}"
        ))
        .unwrap();
    STEP.to_string()
}

fn now() -> DateTime {
    snapshots::now()
}

fn wants(store: &Store) -> Vec<String> {
    store.graphs_of(&[WANT], &Within::default()).unwrap()
}

/// The minted met-test, run as the search runs it: a violation row is the want unmet.
fn met(store: &Store, state: &str) -> bool {
    let graphs = wants(store);
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let found = store.rows("SELECT ?q WHERE { ?s sh:select ?q }", &graphs).unwrap();
    let text = orexis::store::value(&found[0], "q")
        .unwrap()
        .replace("SELECT $this", "SELECT *");
    store.rows(&text, &[state]).unwrap().is_empty()
}

#[test]
fn a_step_whose_fact_a_rule_concludes_is_a_want_below() {
    let store = store();
    let step = predicting(&store, ":d :on :pegB", ":d :on :pegA");
    let want = refine(&store, ME, &step, now()).unwrap();
    assert_eq!(want, Some(format!("{STEP}.below")));
    let graphs = wants(&store);
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let found = store
        .rows("SELECT ?step WHERE { ?step execution:keptBy ?w }", &graphs)
        .unwrap();
    assert_eq!(orexis::store::iri(&found[0], "step").as_deref(), Some(STEP));
    assert!(!met(&store, &format!("{T}state")), "the disk still stands on A's cell");
}

#[test]
fn the_want_below_is_the_world_the_step_lands_in_not_its_diff() {
    let store = store();
    let step = predicting(&store, ":d :on :pegB", ":d :on :pegA");
    refine(&store, ME, &step, now()).unwrap();
    let put = |name: &str, body: &str| {
        store
            .put_trig(
                &format!("{T}{name}"),
                &format!("@prefix : <http://example.org/test#> . {body}"),
            )
            .unwrap();
    };
    put(
        "moved",
        ":pegA a :Peg ; :at :c1 . :pegB a :Peg ; :at :c2 . :d :at :c2 . :e :at :c1 .",
    );
    assert!(met(&store, &format!("{T}moved")));
    put(
        "both",
        ":pegA a :Peg ; :at :c1 . :pegB a :Peg ; :at :c2 . :d :at :c2 . :e :at :c2 .",
    );
    assert!(!met(&store, &format!("{T}both")), "carrying e away breaks the frame");
}

#[test]
fn a_step_no_rule_concludes_is_taken_as_it_would_be() {
    let store = store();
    let step = predicting(&store, ":d :painted :red", "");
    assert_eq!(refine(&store, ME, &step, now()).unwrap(), None);
    assert!(wants(&store).is_empty(), "nothing minted");
}

#[test]
fn a_rule_of_two_head_triples_is_not_run_backwards() {
    let store = store();
    let step = predicting(&store, ":d :near :pegB", "");
    assert_eq!(refine(&store, ME, &step, now()).unwrap(), None);
}
