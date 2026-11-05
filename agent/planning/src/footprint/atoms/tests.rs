//! The footprint per filling, held to what `test_footprint.py` holds `_patterns`, `actions_of` and `stored_edges` to.

use orexis::snapshots;

use super::*;

const A_LIST_UNDER_A_FILTER: &str =
    "SELECT ?v WHERE { ?me <urn:m:bidsIn> ?v . FILTER NOT EXISTS { ?c <urn:m:calledBy> ?me ; <urn:m:calledOn> ?v } }";
const A_FILTER_IN_A_FILTER: &str = "SELECT ?v WHERE { ?me <urn:m:bidsIn> ?v . \
     FILTER NOT EXISTS { ?c <urn:m:calledOn> ?v . FILTER NOT EXISTS { ?c <urn:m:answered> true } } }";

fn empty() -> Store {
    Store::new(snapshots::namespaces()).expect("an empty store")
}

fn var(n: &str) -> Node {
    Node::Var(n.to_string())
}

fn m(local: &str) -> Pred {
    Pred::Iri(format!("urn:m:{local}"))
}

#[test]
fn the_patterns_of_a_precondition_are_every_pattern_once_in_rdflibs_order() {
    let store = empty();
    assert_eq!(
        patterns_of(&store, A_LIST_UNDER_A_FILTER).unwrap(),
        vec![
            (var("c"), m("calledBy"), var("me")),
            (var("c"), m("calledOn"), var("v")),
            (var("me"), m("bidsIn"), var("v")),
        ]
    );
    let yes = Node::Lit(Literal::from(true));
    assert_eq!(
        patterns_of(&store, A_FILTER_IN_A_FILTER).unwrap(),
        vec![
            (var("c"), m("calledOn"), var("v")),
            (var("c"), m("answered"), yes),
            (var("me"), m("bidsIn"), var("v")),
        ]
    );
    assert_eq!(
        patterns_of(&store, "SELECT ?x WHERE { ?x ?p ?y }"),
        None,
        "a variable predicate reads anything"
    );
}

#[test]
fn a_block_is_ordered_by_how_many_of_its_terms_are_bound_by_the_block_before() {
    let store = empty();
    let found = patterns_of(
        &store,
        "SELECT * WHERE { ?r <urn:m:of> ?s ; <urn:m:value> ?v . ?a <urn:m:acts> ?s . <urn:m:me> <urn:m:has> ?a }",
    )
    .unwrap();
    assert_eq!(
        found,
        vec![
            (Node::Iri("urn:m:me".into()), m("has"), var("a")),
            (var("a"), m("acts"), var("s")),
            (var("r"), m("of"), var("s")),
            (var("r"), m("value"), var("v")),
        ],
        "the fewest variables first, then what the block before binds, as rdflib orders them"
    );
    let store = empty();
    assert_eq!(
        patterns_of(&store, "SELECT * WHERE { $tank <urn:m:p> ?x BIND($tank AS ?tank) }").unwrap(),
        vec![(var("tank"), m("p"), var("x"))],
        "a token is the variable of its name"
    );
}

#[test]
fn an_effect_writes_what_its_update_takes_out_as_well_as_what_it_puts_in() {
    let store = snapshots::stand_in(&snapshots::tree().join("planning/tests/plans/a_low_tank_is_filled.trig"));
    let actions = store.graphs_of(&[ACTION], &Within::at(snapshots::now())).unwrap()[0].clone();
    store
        .update(&format!(
            r#"PREFIX : <http://example.org/test#> INSERT DATA {{ GRAPH <{actions}> {{
        :drain a orexis:Action ; planning:effect [ a planning:Effect ; sh:rule [ a belief:Transition ;
            belief:update "PREFIX : <http://example.org/test#> DELETE {{ ?t :spilt ?x }} INSERT {{ ?t :level 0 }} WHERE {{ ?t :spilt ?x }}" ] ] .
        :spill a orexis:Action ; planning:effect [ a planning:Effect ; sh:rule [ a sh:SPARQLRule ;
            sh:construct "PREFIX : <http://example.org/test#> CONSTRUCT {{ ?t :spilt 1 }} WHERE {{ ?t :level ?l }}" ] ] }} }}"#
        ))
        .unwrap();
    let found = effects(&store, snapshots::now()).unwrap();
    let t = |l: &str| format!("http://example.org/test#{l}");
    assert_eq!(
        writes(&found[&t("drain")]),
        Some(BTreeSet::from([t("level"), t("spilt")]))
    );
    assert!(writes(&found[&t("fill")]).unwrap().contains(&t("level")));
    assert!(
        !found[&t("spill")].states(),
        "an effect whose rule is no transition says nothing it writes"
    );
    let atoms = atoms_of(&store, snapshots::now()).unwrap();
    assert!(!atoms.contains_key(&t("spill")) && atoms.contains_key(&t("drain")));
}

#[test]
fn stored_edges_read_the_derivations_genesis_wrote() {
    let store = empty();
    store
        .update(
            "INSERT DATA {
  GRAPH <urn:test:derivations> {
    <urn:test:d1> a planning:Derivation ; planning:reads <urn:test:p> ; planning:writes <urn:test:q> .
    <urn:test:d2> a planning:Derivation ; planning:reads planning:Anything }
  GRAPH <urn:test:catalogue> { <urn:test:catalogue> a orexis:CatalogueGraph . <urn:test:derivations> a planning:DerivationGraph } }",
        )
        .unwrap();
    let one = |i: &str| Some(BTreeSet::from([i.to_string()]));
    assert_eq!(
        stored_edges(&store, &["urn:test:derivations"]).unwrap(),
        vec![(one("urn:test:p"), one("urn:test:q")), (None, Some(BTreeSet::new()))]
    );
}

#[test]
fn an_atom_is_spelled_as_python_spells_its_tuple() {
    assert_eq!(spelled(&("urn:p".into(), None)), "('urn:p', None)");
    assert_eq!(spelled(&("urn:p".into(), Some(vec!["a".into()]))), "('urn:p', ('a',))");
    assert_eq!(
        spelled(&("urn:p".into(), Some(vec!["a".into(), "b".into()]))),
        "('urn:p', ('a', 'b'))"
    );
}
