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
use spargebra::term::GraphNamePattern;
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

/// `update`, one `DELETE`/`INSERT … WHERE` naming no graph, scoped to a world: its templates `into`'s, and its
/// WHERE reading `graphs` merged, each once. Refused, saying why, where the runner will not run it.
pub fn scoped(update: Update, into: &str, graphs: &[&str]) -> Result<Update, Error> {
    let Update { base_iri, operations } = update;
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
            pattern,
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
mod tests;
