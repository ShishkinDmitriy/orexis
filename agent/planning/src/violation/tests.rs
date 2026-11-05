//! The met-test compiler, held as `agent/planning/tests/test_violation.py` holds the Python copy.

use oxigraph::model::NamedNode;

use orexis::snapshots;
use orexis::store::{Store, iri, value};

use super::*;

const T: &str = "http://example.org/test#";
const PREFIXES: &str =
    "@prefix sh: <http://www.w3.org/ns/shacl#> .\n@prefix planning: <http://example.org/orexis/planning#> .\n";

fn shape() -> String {
    format!(
        "<{T}full> a sh:NodeShape ; sh:targetClass <{T}Tank> ;
    sh:property [ sh:path <{T}level> ; sh:minInclusive 10 ; planning:about <{T}level> ] .
<{T}wanted> planning:metWhen <{T}full> .\n"
    )
}

fn avoided() -> String {
    format!(
        "<{T}low_tank> planning:about sh:this ;
    sh:select \"SELECT $this ?value WHERE {{ $this a <{T}Tank> ; <{T}level> ?value . FILTER(?value < 10) }}\" .
<{T}averse> planning:unmetWhen <{T}low_tank> .\n"
    )
}

/// A store of two tanks, the shapes in a graph of their own.
fn store(shapes: &str) -> Store {
    let store = Store::new(snapshots::namespaces()).unwrap();
    store
        .put_trig(
            &format!("{T}default"),
            &format!(
            "{PREFIXES}<{T}world> {{ <{T}low> a <{T}Tank> ; <{T}level> 5 . <{T}high> a <{T}Tank> ; <{T}level> 12 . }}
<{T}shapes> {{ {shapes} }}"
        ),
        )
        .unwrap();
    store
}

fn compiled(store: &Store, subject: &str) -> Result<Option<String>> {
    let shapes = Shapes::of(store, &[format!("{T}shapes")]).unwrap();
    select_of(
        &shapes,
        &NamedNode::new(format!("{T}{subject}")).unwrap().into(),
        &snapshots::namespaces(),
    )
}

fn rows(store: &Store, select: &str) -> Vec<orexis::store::Row> {
    store.rows(select, &[&format!("{T}world")]).unwrap()
}

fn refusal(found: Result<Option<String>>) -> String {
    match found {
        Err(Compiled::Unsupported(u)) => u.0,
        other => panic!("refused nothing: {other:?}"),
    }
}

#[test]
fn the_report_answers_the_focus_nodes_that_violate_and_what_each_is_about() {
    let store = store(&shape());
    let found = rows(&store, &compiled(&store, "wanted").unwrap().unwrap());
    assert_eq!(found.len(), 1);
    assert_eq!(iri(&found[0], "this"), Some(format!("{T}low")));
    assert_eq!(iri(&found[0], "_about"), Some(format!("{T}level")));
    assert_eq!(value(&found[0], "_constraint").as_deref(), Some("0"));
    assert_eq!(value(&found[0], "_offending").as_deref(), Some("5"));
}

#[test]
fn the_entered_select_answers_one_row_per_instance_in_the_avoided_state_with_its_offending_value() {
    let store = store(&avoided());
    let found = rows(&store, &compiled(&store, "averse").unwrap().unwrap());
    assert_eq!(found.len(), 1);
    let row = &found[0];
    assert_eq!(
        (
            iri(row, "this"),
            value(row, "_constraint"),
            value(row, "_offending"),
            iri(row, "_about")
        ),
        (
            Some(format!("{T}low")),
            Some("0".into()),
            Some("5".into()),
            Some(format!("{T}low"))
        )
    );
}

#[test]
fn an_avoided_state_narrowed_by_a_target_node_answers_for_that_instance_alone() {
    let high = store(&format!("{} <{T}low_tank> sh:targetNode <{T}high> .", avoided()));
    assert!(rows(&high, &compiled(&high, "averse").unwrap().unwrap()).is_empty());
    let low = store(&format!("{} <{T}low_tank> sh:targetNode <{T}low> .", avoided()));
    assert_eq!(rows(&low, &compiled(&low, "averse").unwrap().unwrap()).len(), 1);
}

#[test]
fn select_of_reads_either_polarity_and_refuses_both() {
    let store = store(&format!("{}{}", shape(), avoided()));
    assert!(compiled(&store, "bare").unwrap().is_none());
    let both = self::store(&format!(
        "{}{} <{T}wanted> planning:unmetWhen <{T}low_tank> .",
        shape(),
        avoided()
    ));
    assert!(refusal(compiled(&both, "wanted")).contains("both"));
}

#[test]
fn an_avoided_state_that_is_not_one_select_refuses() {
    let two = store(&format!(
        "{} <{T}low_tank> sh:select \"SELECT $this WHERE {{ $this a <urn:x> }}\" .",
        avoided()
    ));
    assert!(refusal(compiled(&two, "averse")).contains("one sh:select"));
    let none = store(&format!(
        "<{T}low_tank> planning:about sh:this . <{T}averse> planning:unmetWhen <{T}low_tank> ."
    ));
    assert!(refusal(compiled(&none, "averse")).contains("one sh:select"));
    let a_shape = store(&format!("{} <{T}averse> planning:unmetWhen <{T}full> .", shape()));
    assert!(refusal(compiled(&a_shape, "averse")).contains("not a shape"));
}

#[test]
fn a_constraint_this_does_not_compile_refuses_and_names_itself() {
    let store = store(&format!(
        "<{T}full> a sh:NodeShape ; sh:targetClass <{T}Tank> ; sh:property [ sh:path <{T}level> ; sh:pattern \"x\" ] .
<{T}wanted> planning:metWhen <{T}full> ."
    ));
    assert!(refusal(compiled(&store, "wanted")).contains("is not a constraint this compiles"));
}

#[test]
fn constraints_are_numbered_in_the_order_the_shapes_graph_hands_them() {
    let store = store(&format!(
        "<{T}full> a sh:NodeShape ; sh:targetClass <{T}Tank> ;
    sh:property [ sh:path <{T}level> ; sh:minInclusive 10 ; planning:about <{T}level> ] ;
    sh:property [ sh:path <{T}level> ; sh:maxInclusive 8 ; planning:about <{T}top> ] .
<{T}wanted> planning:metWhen <{T}full> ."
    ));
    let found = rows(&store, &compiled(&store, "wanted").unwrap().unwrap());
    let numbered: std::collections::BTreeSet<(String, String, String)> = found
        .iter()
        .map(|r| {
            (
                iri(r, "this").unwrap(),
                value(r, "_constraint").unwrap(),
                iri(r, "_about").unwrap(),
            )
        })
        .collect();
    assert_eq!(
        numbered,
        [
            (format!("{T}low"), "0".into(), format!("{T}level")),
            (format!("{T}high"), "1".into(), format!("{T}top")),
        ]
        .into()
    );
}
