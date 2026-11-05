//! The footprint's reading of a text, held to what `test_footprint.py` holds the Python reading to — the parts
//! the laying of the grounds asks.

use oxigraph::model::{Literal, NamedNode};
use spargebra::{Query, SparqlParser};

use orexis::snapshots;

use super::*;

fn reads(text: &str) -> Option<BTreeSet<String>> {
    let Query::Select { pattern, .. } = SparqlParser::new().parse_query(text).expect("a query") else {
        panic!("a select")
    };
    reads_of(&pattern)
}

fn set(iris: &[&str]) -> Option<BTreeSet<String>> {
    Some(iris.iter().map(|i| i.to_string()).collect())
}

const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";

#[test]
fn what_a_select_reads_is_the_predicates_of_its_patterns_and_a_type_pattern_its_class() {
    assert_eq!(
        reads("SELECT ?x WHERE { ?x <urn:test:p> ?y . ?y a <urn:test:C> }"),
        set(&["urn:test:p", "urn:test:C"])
    );
    assert_eq!(reads("SELECT ?x WHERE { ?x a ?c }"), set(&[RDF_TYPE]));
    //  A SEQUENCE OR AN INVERSE OF PLAIN PREDICATES IS TRIPLES, as SPARQL's algebra translates it, so a type step
    //  with a class reads the class, where rdflib keeps the path and reads every type. No shipped text spells one.
    assert_eq!(
        reads("SELECT ?x WHERE { ?x <urn:test:p>/a <urn:test:C> }"),
        set(&["urn:test:p", "urn:test:C"])
    );
    assert_eq!(reads("SELECT ?x WHERE { <urn:test:C> ^a ?x }"), set(&["urn:test:C"]));
    assert_eq!(
        reads("SELECT ?x WHERE { ?x (<urn:test:p>/a)+ ?y }"),
        set(&["urn:test:p", RDF_TYPE])
    );
    assert_eq!(
        reads("SELECT ?x WHERE { ?x ?p ?y }"),
        None,
        "a variable predicate reads anything"
    );
    assert_eq!(
        reads("SELECT ?x WHERE { ?x !<urn:test:p> ?y }"),
        None,
        "anything but is anything"
    );
}

#[test]
fn a_pattern_under_not_exists_is_read_too_however_deep() {
    assert_eq!(
        reads("SELECT ?x WHERE { ?x a <urn:test:C> FILTER NOT EXISTS { ?x <urn:test:q> ?z } }"),
        set(&["urn:test:q", "urn:test:C"])
    );
    assert_eq!(
        reads(
            "SELECT ?v WHERE { ?me <urn:m:bidsIn> ?v . FILTER NOT EXISTS { ?c <urn:m:calledBy> ?me ; <urn:m:calledOn> ?v } }"
        ),
        set(&["urn:m:bidsIn", "urn:m:calledBy", "urn:m:calledOn"])
    );
    assert_eq!(
        reads("SELECT ?v WHERE { FILTER NOT EXISTS { ?c a <urn:m:C> ; <urn:m:p> [ <urn:m:q> ?v ] } }"),
        set(&["urn:m:C", "urn:m:p", "urn:m:q"])
    );
    assert_eq!(
        reads("SELECT ?v WHERE { FILTER NOT EXISTS { ?c ?p ?v ; <urn:m:r> ?w } }"),
        None,
        "a variable predicate in the list is still anything"
    );
    assert_eq!(
        reads(
            "SELECT ?v WHERE { ?me <urn:m:a> ?v FILTER NOT EXISTS { ?c <urn:m:b> ?v \
             FILTER NOT EXISTS { ?c <urn:m:c> ?v FILTER NOT EXISTS { ?c <urn:m:d> ?v } } } }"
        ),
        set(&["urn:m:a", "urn:m:b", "urn:m:c", "urn:m:d"])
    );
    assert_eq!(
        reads(
            "SELECT ?v WHERE { ?c <urn:m:p> ?v . FILTER NOT EXISTS { ?c <urn:m:q> ?v . OPTIONAL { ?c <urn:m:o> ?w } \
             MINUS { ?c <urn:m:m> ?z } FILTER EXISTS { ?c <urn:m:e> ?y } } }"
        ),
        set(&["urn:m:p", "urn:m:q", "urn:m:o", "urn:m:m", "urn:m:e"])
    );
    assert_eq!(
        reads("SELECT ?v WHERE { ?c <urn:m:p> ?v BIND(EXISTS { ?c <urn:m:q> ?w ; <urn:m:r> ?x } AS ?b) }"),
        set(&["urn:m:p", "urn:m:q", "urn:m:r"])
    );
}

#[test]
fn a_rule_text_is_made_parseable_and_the_selfs_anchor_read_as_absent() {
    assert!(parseable("SELECT ?x WHERE { $venue <urn:test:p> ?x }").contains("?token__venue"));
    assert!(parseable("SELECT ?x WHERE { $this <urn:test:p> ?x }").contains("?this "));
    assert!(!parseable("INSERT { GRAPH $into(x:G) { ?s ?p ?o } } WHERE { ?s ?p ?o }").contains("$into("));
    let free = "SELECT ?x WHERE { ?me <urn:test:p> ?x . ?x <urn:test:q> ?y }";
    for anchored in [
        "SELECT ?x WHERE { ?me a orexis:Self ; <urn:test:p> ?x . ?x <urn:test:q> ?y }",
        "SELECT ?x WHERE { ?me a orexis:Self . ?me <urn:test:p> ?x . ?x <urn:test:q> ?y }",
        "SELECT ?x WHERE { ?me <urn:test:p> ?x . ?x <urn:test:q> ?y . ?me a <http://example.org/orexis#Self> }",
    ] {
        let text = parseable(anchored);
        assert!(!text.contains("orexis:Self") && !text.contains("#Self"), "{text}");
        assert_eq!(reads(&text), reads(free), "{text}");
    }
}

#[test]
fn a_term_is_spelled_as_rdflib_spells_it() {
    assert_eq!(n3(&NamedNode::new("urn:x").unwrap().into()), "<urn:x>");
    assert_eq!(n3(&Literal::new_simple_literal("a \"b\"\\").into()), r#""a \"b\"\\""#);
    assert_eq!(
        n3(&Literal::new_language_tagged_literal("hi", "en").unwrap().into()),
        "\"hi\"@en"
    );
    assert_eq!(
        n3(&Literal::new_typed_literal("5", xsd::INTEGER).into()),
        "\"5\"^^<http://www.w3.org/2001/XMLSchema#integer>"
    );
}

const ACTIONS: &str = r#"
@prefix : <http://example.org/test#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix planning: <http://example.org/orexis/planning#> .
@prefix belief: <http://example.org/orexis/belief#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
GRAPH :actions {
  :open a orexis:Action ; planning:effect [ sh:rule [ a belief:Transition ;
    belief:update """PREFIX : <http://example.org/test#>
      DELETE { $tank :lid :closed } INSERT { $tank :lid :open ; :volume 1 } WHERE { $tank :lid :closed }""" ] ] .
  :set a orexis:Action ; planning:effect [ sh:rule [ a belief:Transition ;
    belief:update """PREFIX : <http://example.org/test#>
      INSERT { $tank ?p ?v } WHERE { VALUES ?p { :level :temperature } $tank :reading ?v }""" ] ] .
}
GRAPH :rules {
  :dry a belief:Transition ; belief:update """PREFIX : <http://example.org/test#>
    DELETE { ?bed :soil ?was } INSERT { ?bed :soil :dry } WHERE { ?bed :soil ?was ; :moisture ?m . ?m a :Low }""" .
}
GRAPH :catalogue {
  :catalogue a orexis:CatalogueGraph .
  :actions a orexis:ActionGraph .
  :rules a sh:RulesGraph .
}
"#;

fn store_of(trig: &str) -> Store {
    let store = Store::new(snapshots::namespaces()).expect("an empty store");
    store.put_trig(snapshots::WORLD, trig).expect("the actions");
    store
}

fn pattern(predicate: &str, object: Option<Term>) -> Pattern {
    Pattern {
        predicate: format!("http://example.org/test#{predicate}"),
        object,
    }
}

#[test]
fn what_a_search_can_change_is_every_template_of_every_writer_an_object_fixed_where_one_is_stated() {
    let store = store_of(ACTIONS);
    let test = |local: &str| {
        Some(
            NamedNode::new(format!("http://example.org/test#{local}"))
                .unwrap()
                .into(),
        )
    };
    let found = changeable(&store, None, snapshots::now())
        .unwrap()
        .expect("every template reads");
    assert_eq!(
        found,
        vec![
            pattern("level", None),
            pattern("lid", test("closed")),
            pattern("lid", test("open")),
            pattern("soil", None),
            pattern("soil", test("dry")),
            pattern("temperature", None),
            pattern("volume", Some(Literal::new_typed_literal("1", xsd::INTEGER).into())),
        ]
    );
    let only: BTreeSet<String> = ["http://example.org/test#open".to_string()].into();
    let found = changeable(&store, Some(&only), snapshots::now()).unwrap().unwrap();
    assert!(
        !found.iter().any(|p| p.predicate.ends_with("level")),
        "the scope's actions alone"
    );
    assert!(
        found.iter().any(|p| p.predicate.ends_with("soil")),
        "and every transition"
    );
}

#[test]
fn a_predicate_nothing_bounds_or_an_update_refused_is_anything() {
    let unbounded = ACTIONS.replace("VALUES ?p { :level :temperature } ", "");
    assert_eq!(changeable(&store_of(&unbounded), None, snapshots::now()).unwrap(), None);
    let undef = ACTIONS.replace("VALUES ?p { :level :temperature }", "VALUES ?p { :level UNDEF }");
    assert_eq!(changeable(&store_of(&undef), None, snapshots::now()).unwrap(), None);
    let named = ACTIONS.replace("INSERT { ?bed :soil :dry }", "INSERT { GRAPH :g { ?bed :soil :dry } }");
    assert_eq!(changeable(&store_of(&named), None, snapshots::now()).unwrap(), None);
    assert_eq!(read_by_transitions(&store_of(&named)).unwrap(), None);
}

#[test]
fn a_transition_reads_what_its_where_reads() {
    let test = |l: &str| format!("http://example.org/test#{l}");
    assert_eq!(
        read_by_transitions(&store_of(ACTIONS)).unwrap(),
        Some([test("soil"), test("moisture"), test("Low")].into_iter().collect())
    );
}
