//! The bridges, held to what `test_bridge.py` holds the Python reading to.

use crate::refine::tests::{predicting, store};

use super::*;

#[test]
fn a_rule_with_one_head_triple_is_a_bridge() {
    let found = heads(&store()).unwrap();
    assert_eq!(found.len(), 1);
    assert!(found[0].head.1 == ":on" && found[0].r#where.contains("at"));
}

#[test]
fn a_transition_is_no_bridge() {
    let store = store();
    store
        .update(
            r#"INSERT DATA { GRAPH <http://example.org/test#rules> {
  <http://example.org/test#moved> a sh:SPARQLRule , belief:Transition ;
    sh:construct """PREFIX : <http://example.org/test#>
    CONSTRUCT { ?disk :was ?cell } WHERE { ?disk :at ?cell }""" } }"#,
        )
        .unwrap();
    let found: Vec<String> = heads(&store).unwrap().into_iter().map(|b| b.head.1).collect();
    assert_eq!(found, [":on"]);
}

#[test]
fn a_step_is_kept_below_where_a_bridge_concludes_a_fact_it_adds() {
    let s = store();
    assert!(keeps(&s, &predicting(&s, ":d :on :pegB", "")).unwrap());
    let s = store();
    assert!(
        !keeps(&s, &predicting(&s, ":d :painted :red", "")).unwrap(),
        "no rule concludes a colour"
    );
    let s = store();
    assert!(
        !keeps(&s, &predicting(&s, "", "")).unwrap(),
        "a step that adds nothing is kept by nothing"
    );
}
