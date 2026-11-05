//! The machine a transition is applied by, held as `agent/belief/tests/test_transition.py` holds it: on a bare
//! store, in this test's own words.

use std::collections::BTreeSet;

use oxigraph::model::{NamedNode, Quad};

use orexis::snapshots;

use super::*;

const T: &str = "http://example.org/test#";

fn t(local: &str) -> String {
    format!("{T}{local}")
}

fn p(text: &str) -> String {
    format!("PREFIX : <{T}>\n{text}")
}

/// A lamp lit in one graph and, the same fact, in another; a switch saying off.
fn store() -> Store {
    let store = Store::new(snapshots::namespaces()).unwrap();
    let n = |l: &str| NamedNode::new(t(l)).unwrap();
    for g in ["state", "other"] {
        store.add([Quad::new(n("lamp"), n("is"), n("Lit"), n(g))]).unwrap();
    }
    store
        .add([Quad::new(n("switch"), n("says"), n("off"), n("state"))])
        .unwrap();
    store
}

fn facts(store: &Store, graph: &str) -> BTreeSet<(String, String, String)> {
    let local = |s: String| s.trim_matches(['<', '>']).rsplit('#').next().unwrap().to_string();
    store
        .triples(&t(graph))
        .unwrap()
        .into_iter()
        .map(|x| {
            (
                local(x.subject.to_string()),
                local(x.predicate.to_string()),
                local(x.object.to_string()),
            )
        })
        .collect()
}

fn set(items: &[(&str, &str, &str)]) -> BTreeSet<(String, String, String)> {
    items
        .iter()
        .map(|(a, b, c)| (a.to_string(), b.to_string(), c.to_string()))
        .collect()
}

fn darken() -> Rule {
    Rule::new(
        0.0,
        p("DELETE { ?l :is ?was } INSERT { ?l :is :Dark } WHERE { :switch :says :off . ?l :is ?was }"),
        "darken",
    )
}

fn witness() -> Rule {
    Rule::new(0.0, p("INSERT { ?l :seen ?was } WHERE { ?l :is ?was }"), "witness")
}

#[test]
fn transitions_are_every_active_transition_the_rules_graphs_hold_in_their_orders() {
    let case = snapshots::tree().join("belief/tests/trigger/two_transitions_of_one_order_read_the_same_state.trig");
    let store = snapshots::stand_in(&case);
    let named = |orders: Vec<Vec<Rule>>| -> Vec<Vec<String>> {
        orders
            .into_iter()
            .map(|order| {
                let mut names: Vec<String> = order.iter().map(|r| r.named()[T.len()..].to_string()).collect();
                names.sort();
                names
            })
            .collect()
    };
    assert_eq!(
        named(transitions(&store).unwrap()),
        [vec!["countRule", "sawRule"], vec!["echoRule"]]
    );
    let found = transitions(&store).unwrap()[0]
        .iter()
        .find(|r| r.named() == t("countRule"))
        .cloned()
        .unwrap();
    assert!(
        found.update.is_some() && found.order == 0.0,
        "its text and its order travel with it"
    );
    store
        .update(&format!(
            "PREFIX : <{T}> INSERT DATA {{ GRAPH :rules {{ :sawRule sh:deactivated true . :inference a sh:SPARQLRule ; \
             sh:construct \"CONSTRUCT {{}} WHERE {{}}\" }} }}"
        ))
        .unwrap();
    assert_eq!(
        named(transitions(&store).unwrap()),
        [vec!["countRule"], vec!["echoRule"]]
    );
}

#[test]
fn ordered_groups_the_rules_by_order_ascending() {
    let (a, b, c) = (
        Rule::new(1.0, "a", "a"),
        Rule::new(0.0, "b", "b"),
        Rule::new(1.0, "c", "c"),
    );
    assert_eq!(ordered([a.clone(), b.clone(), c.clone()]), [vec![b], vec![a, c]]);
    assert!(ordered(Vec::new()).is_empty());
}

#[test]
fn run_changes_the_world_it_is_handed_alone_reading_every_graph_beside_it() {
    let store = store();
    assert_eq!(
        run(&store, &[darken()], &t("other"), &[&t("other"), &t("state")], &[]),
        1
    );
    assert_eq!(facts(&store, "other"), set(&[("lamp", "is", "Dark")]));
    assert_eq!(
        facts(&store, "state"),
        set(&[("lamp", "is", "Lit"), ("switch", "says", "off")]),
        "read, and not changed"
    );
}

#[test]
fn run_applies_each_rule_to_what_the_rule_before_left() {
    let store = store();
    run(&store, &[darken(), witness()], &t("state"), &[&t("state")], &[]);
    assert_eq!(
        facts(&store, "state"),
        set(&[
            ("lamp", "is", "Dark"),
            ("lamp", "seen", "Dark"),
            ("switch", "says", "off")
        ])
    );
    let store = self::store();
    let later = Rule::new(1.0, darken().update.unwrap(), "later");
    run(&store, &[later, witness()], &t("state"), &[&t("state")], &[]);
    assert!(
        facts(&store, "state").contains(&("lamp".into(), "seen".into(), "Lit".into())),
        "an earlier order runs first, however listed"
    );
}

#[test]
fn a_delete_where_is_scoped_as_the_delete_it_abbreviates() {
    let store = store();
    run(
        &store,
        &[Rule::new(0.0, p("DELETE WHERE { ?l :is :Lit }"), "short")],
        &t("state"),
        &[&t("state")],
        &[],
    );
    assert_eq!(facts(&store, "state"), set(&[("switch", "says", "off")]));
    assert_eq!(
        facts(&store, "other"),
        set(&[("lamp", "is", "Lit")]),
        "the other graph untouched"
    );
}

/// WHAT THE RUNNER REFUSES, each a package's bug.
const REFUSED: &[(&str, &str)] = &[
    (
        "with",
        "WITH <urn:x> DELETE { ?l :is ?w } INSERT { ?l :is :Dark } WHERE { ?l :is ?w }",
    ),
    (
        "using",
        "DELETE { ?l :is ?w } INSERT { ?l :is :Dark } USING <urn:x> WHERE { ?l :is ?w }",
    ),
    (
        "templated",
        "DELETE { GRAPH <urn:x> { ?l :is ?w } } INSERT { ?l :is :Dark } WHERE { ?l :is ?w }",
    ),
    (
        "graphed",
        "DELETE { ?l :is ?w } INSERT { ?l :is :Dark } WHERE { GRAPH ?g { ?l :is ?w } }",
    ),
    (
        "existing",
        "DELETE { ?l :is ?w } INSERT { ?l :is :Dark } WHERE { ?l :is ?w FILTER EXISTS { GRAPH ?g { ?l :is ?w } } }",
    ),
    (
        "chained",
        "DELETE WHERE { ?l :is :Lit } ; INSERT { ?l :is :Dark } WHERE { ?l :is ?w }",
    ),
    (
        "trailing",
        "DELETE { ?l :is ?w } INSERT { ?l :is :Dark } WHERE { ?l :is ?w } ;",
    ),
    ("data", "INSERT DATA { :lamp :is :Dark }"),
    ("construct", "CONSTRUCT { ?l :is :Dark } WHERE { ?l :is ?w }"),
    (
        "broken",
        "DELETE { ?l :is ?w } INSERT { ?l :is :Dark } WHERE { ?l :is ?w",
    ),
    (
        "unbound",
        "DELETE { ?l :is ?w } INSERT { $nobody :is :Dark } WHERE { ?l :is ?w }",
    ),
];

#[test]
fn an_update_naming_its_graphs_or_chaining_operations_changes_nothing_and_the_order_still_runs() {
    for (name, text) in REFUSED {
        let store = store();
        run(
            &store,
            &[Rule::new(0.0, p(text), *name), witness()],
            &t("state"),
            &[&t("state")],
            &[],
        );
        assert_eq!(
            facts(&store, "state"),
            set(&[
                ("lamp", "is", "Lit"),
                ("switch", "says", "off"),
                ("lamp", "seen", "Lit")
            ]),
            "{name}: the refused rule changes nothing and the witness still runs"
        );
    }
}

#[test]
fn a_refusal_says_why() {
    let store = store();
    let reason = |name: &str| {
        let text = p(REFUSED.iter().find(|(n, _)| *n == name).unwrap().1);
        let refusal = refuse_a_chain(&text)
            .and_then(|()| store.parse_update(&text))
            .and_then(|parsed| scoped(parsed, &t("w"), &[]));
        refusal.err().unwrap().to_string()
    };
    assert!(reason("with").contains("names its own graphs"));
    assert!(reason("graphed").contains("names its own graphs"));
    assert!(reason("chained").contains("chains operations"));
    assert!(reason("trailing").contains("chains operations"));
    assert!(reason("data").contains("InsertData"));
}

#[test]
fn a_token_is_bound_before_the_text_is_parsed() {
    let store = store();
    let rule = Rule::new(
        0.0,
        p("DELETE { $lamp :is ?was } INSERT { $lamp :is :Dark } WHERE { $lamp :is ?was }"),
        "bound",
    );
    run(
        &store,
        &[rule],
        &t("state"),
        &[&t("state")],
        &[("lamp", Value::iri(t("lamp")))],
    );
    assert!(facts(&store, "state").contains(&("lamp".into(), "is".into(), "Dark".into())));
}
