//! A TRANSITION: rules that change a state rather than conclude of it, and the one machine that applies them, as
//! `agent/belief/transition.py` applies them (a-transition-changes-the-state-and-an-inference-only-concludes).
//!
//! **ONE TEXT, AND THE RUNNER SAYS WHERE.** A rule is a `belief:Transition` whose `belief:update` is one SPARQL
//! update, either template alone over its WHERE, or `DELETE WHERE`. No rule names a graph: `run` hands the engine
//! the text scoped to a world — what it deletes and inserts that world's alone, what its WHERE reads every graph it
//! is handed — rule after rule, by `sh:order`, each reading what the one before left.
//!
//! **THE SCOPE IS SAID ON THE ALGEBRA.** The Python kernel finds the text's prologue, templates and WHERE with
//! rdflib's grammar and writes `WITH <world>` and a `USING` per graph around them; here the parsed update is told
//! the same, its templates' default graph made the world and its dataset the graphs read, so nothing is reprinted
//! and the text is parsed once. **A RULE THAT WILL NOT RUN CHANGES NOTHING, LOUDLY**: one naming its own graphs,
//! chaining a second operation, no `DELETE`/`INSERT … WHERE`, refusing to bind or refused by the engine is said in
//! the log, naming the rule, and the whole of it changes nothing.

use oxigraph::model::NamedNode;
use spargebra::algebra::{Expression, GraphPattern, QueryDataset};
use spargebra::term::{GraphNamePattern, GroundQuadPattern, QuadPattern};
use spargebra::{GraphUpdateOperation, Update};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::store::{Store, Within, iri, value};

use crate::ontology::RULES_GRAPH;

/// EVERY TRANSITION, over the rules graphs: each active one, with its order and its update.
const TRANSITIONS_Q: &str = "
SELECT DISTINCT ?rule ?order ?update WHERE {
  ?rule a belief:Transition .
  FILTER NOT EXISTS { ?rule sh:deactivated true }
  OPTIONAL { ?rule sh:order ?o } OPTIONAL { ?rule belief:update ?update }
  BIND(COALESCE(?o, 0) AS ?order) }
ORDER BY ?order ?rule";

/// One rule of a transition: its order, its update text, and its name for the log.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Rule {
    pub order: f64,
    pub update: Option<String>,
    pub name: Option<String>,
}

impl Rule {
    pub fn new(order: f64, update: impl Into<String>, name: impl Into<String>) -> Self {
        Rule {
            order,
            update: Some(update.into()),
            name: Some(name.into()),
        }
    }

    fn named(&self) -> &str {
        self.name.as_deref().unwrap_or("a rule")
    }
}

/// Every active `belief:Transition` of the rules graphs, in the orders they are applied in.
pub fn transitions(store: &Store) -> Result<Vec<Vec<Rule>>, Error> {
    let graphs = store.graphs_of(&[RULES_GRAPH], &Within::default())?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let found = store.rows(TRANSITIONS_Q, &graphs)?;
    let rules = found.iter().map(|r| Rule {
        order: value(r, "order").and_then(|o| o.parse().ok()).unwrap_or(0.0),
        update: value(r, "update"),
        name: iri(r, "rule"),
    });
    Ok(ordered(rules))
}

/// `rules` grouped by order, ascending, each order as the rules were listed.
pub fn ordered(rules: impl IntoIterator<Item = Rule>) -> Vec<Vec<Rule>> {
    let mut groups: Vec<(f64, Vec<Rule>)> = Vec::new();
    for rule in rules {
        match groups.iter_mut().find(|(order, _)| *order == rule.order) {
            Some((_, group)) => group.push(rule),
            None => groups.push((rule.order, vec![rule])),
        }
    }
    groups.sort_by(|a, b| a.0.total_cmp(&b.0));
    groups.into_iter().map(|(_, group)| group).collect()
}

/// `rules` applied to `into`, one after another in their order, each reading `graphs` as the rule before left
/// them. Answers the rule executions spent, one a rule. `tokens` are the `$tokens` a text takes — an effect's
/// parameters; none for an arrival's transition.
pub fn run(store: &Store, rules: &[Rule], into: &str, graphs: &[&str], tokens: &[(&str, Value)]) -> usize {
    let flat: Vec<Rule> = ordered(rules.iter().cloned()).into_iter().flatten().collect();
    for rule in &flat {
        let Some(text) = &rule.update else {
            log::error!(
                "{}: a transition states no belief:update, so it changes nothing",
                rule.named()
            );
            continue;
        };
        let applied = bind(text, tokens).and_then(|bound| {
            refuse_a_chain(&bound)?;
            let parsed = store.parse_update(&bound)?;
            store.run_update(scoped(parsed, into, graphs)?)
        });
        match applied {
            Ok(()) => {}
            Err(Error::Document(reason)) => log::error!("{}: {reason}, so it changes nothing", rule.named()),
            Err(other) => log::error!(
                "{}: its update would not run, so it changes nothing: {other}",
                rule.named()
            ),
        }
    }
    flat.len()
}

/// A transition's update as its runner reads it: the delete templates, the insert templates and the one WHERE —
/// a `DELETE WHERE` its pattern as both — as `agent/belief/transition.py`'s `templates` finds them. Refused,
/// saying why, where the runner will not run it.
#[derive(Clone, Debug)]
pub struct Parts {
    pub delete: Vec<GroundQuadPattern>,
    pub insert: Vec<QuadPattern>,
    pub pattern: GraphPattern,
}

/// `text`, a transition's update, as its parts: refused where it chains operations, is no `DELETE`/`INSERT …
/// WHERE`, or names a graph anywhere.
pub fn parts(store: &Store, text: &str) -> Result<Parts, Error> {
    refuse_a_chain(text)?;
    parts_of(store.parse_update(text)?.operations)
}

fn parts_of(operations: Vec<GraphUpdateOperation>) -> Result<Parts, Error> {
    let [operation] = <[GraphUpdateOperation; 1]>::try_from(operations)
        .map_err(|_| refused("its update chains operations with `;`, and a transition is one"))?;
    let GraphUpdateOperation::DeleteInsert {
        delete,
        insert,
        using,
        pattern,
    } = operation
    else {
        return Err(refused(&format!(
            "its update is {}, no DELETE/INSERT … WHERE",
            kind(&operation)
        )));
    };
    let names_a_graph = using.is_some()
        || delete.iter().any(|q| q.graph_name != GraphNamePattern::DefaultGraph)
        || insert.iter().any(|q| q.graph_name != GraphNamePattern::DefaultGraph)
        || graphed(&pattern);
    if names_a_graph {
        return Err(refused("its update names its own graphs, and the runner says them"));
    }
    Ok(Parts {
        delete,
        insert,
        pattern: *pattern,
    })
}

/// `update`, one `DELETE`/`INSERT … WHERE` naming no graph, scoped to a world: its templates `into`'s, and its
/// WHERE reading `graphs` merged, each once. Refused, saying why, where the runner will not run it.
pub fn scoped(update: Update, into: &str, graphs: &[&str]) -> Result<Update, Error> {
    let Update { base_iri, operations } = update;
    let Parts {
        delete,
        insert,
        pattern,
    } = parts_of(operations)?;
    let world = node(into)?;
    let mut default: Vec<oxigraph::model::NamedNode> = Vec::new();
    for g in graphs {
        let g = node(g)?;
        if !default.contains(&g) {
            default.push(g);
        }
    }
    let delete = delete
        .into_iter()
        .map(|mut q| {
            q.graph_name = world.clone().into();
            q
        })
        .collect();
    let insert = insert
        .into_iter()
        .map(|mut q| {
            q.graph_name = world.clone().into();
            q
        })
        .collect();
    Ok(Update {
        base_iri,
        operations: vec![GraphUpdateOperation::DeleteInsert {
            delete,
            insert,
            using: Some(QueryDataset {
                default,
                named: Some(Vec::new()),
            }),
            pattern: Box::new(pattern),
        }],
    })
}

/// A text ending in `;` chains an empty operation after its one: the Python kernel's grammar counts two, and so
/// refuses it, where this engine's parser counts one.
fn refuse_a_chain(text: &str) -> Result<(), Error> {
    if text.trim_end().ends_with(';') {
        return Err(refused(
            "its update chains operations with `;`, and a transition is one",
        ));
    }
    Ok(())
}

/// Whether a WHERE names a graph anywhere, an `EXISTS` included.
fn graphed(pattern: &GraphPattern) -> bool {
    match pattern {
        GraphPattern::Graph { .. } => true,
        GraphPattern::Bgp { .. } | GraphPattern::Path { .. } | GraphPattern::Values { .. } => false,
        GraphPattern::Join { left, right }
        | GraphPattern::Union { left, right }
        | GraphPattern::Minus { left, right } => graphed(left) || graphed(right),
        GraphPattern::LeftJoin {
            left,
            right,
            expression,
        } => graphed(left) || graphed(right) || expression.as_ref().is_some_and(exists_graphed),
        GraphPattern::Filter { expr, inner } => exists_graphed(expr) || graphed(inner),
        GraphPattern::Extend { inner, expression, .. } => graphed(inner) || exists_graphed(expression),
        GraphPattern::OrderBy { inner, .. }
        | GraphPattern::Project { inner, .. }
        | GraphPattern::Distinct { inner }
        | GraphPattern::Reduced { inner }
        | GraphPattern::Slice { inner, .. }
        | GraphPattern::Group { inner, .. }
        | GraphPattern::Service { inner, .. } => graphed(inner),
        #[allow(unreachable_patterns)]
        _ => false,
    }
}

fn exists_graphed(expression: &Expression) -> bool {
    match expression {
        Expression::Exists(pattern) => graphed(pattern),
        Expression::Or(a, b)
        | Expression::And(a, b)
        | Expression::Equal(a, b)
        | Expression::SameTerm(a, b)
        | Expression::Greater(a, b)
        | Expression::GreaterOrEqual(a, b)
        | Expression::Less(a, b)
        | Expression::LessOrEqual(a, b)
        | Expression::Add(a, b)
        | Expression::Subtract(a, b)
        | Expression::Multiply(a, b)
        | Expression::Divide(a, b) => exists_graphed(a) || exists_graphed(b),
        Expression::UnaryPlus(a) | Expression::UnaryMinus(a) | Expression::Not(a) => exists_graphed(a),
        Expression::If(a, b, c) => exists_graphed(a) || exists_graphed(b) || exists_graphed(c),
        Expression::In(a, list) => exists_graphed(a) || list.iter().any(exists_graphed),
        Expression::Coalesce(list) | Expression::FunctionCall(_, list) => list.iter().any(exists_graphed),
        _ => false,
    }
}

/// The name an operation has in the Python kernel's grammar, for the refusal.
fn kind(operation: &GraphUpdateOperation) -> &'static str {
    match operation {
        GraphUpdateOperation::InsertData { .. } => "InsertData",
        GraphUpdateOperation::DeleteData { .. } => "DeleteData",
        GraphUpdateOperation::DeleteInsert { .. } => "Modify",
        GraphUpdateOperation::Load { .. } => "Load",
        GraphUpdateOperation::Clear { .. } => "Clear",
        GraphUpdateOperation::Create { .. } => "Create",
        GraphUpdateOperation::Drop { .. } => "Drop",
    }
}

fn refused(reason: &str) -> Error {
    Error::Document(reason.to_string())
}

fn node(iri: &str) -> Result<NamedNode, Error> {
    NamedNode::new(iri).map_err(|e| Error::Evaluation(format!("no IRI: {iri}: {e}")))
}

#[cfg(test)]
mod tests {
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
}
