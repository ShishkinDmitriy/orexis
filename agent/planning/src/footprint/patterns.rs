//! A PRECONDITION'S PATTERNS, IN RDFLIB'S ORDER: a footprint asks a precondition's patterns over the common beliefs
//! as a chain of OPTIONALs, so the order they are asked in is part of the answer — each BGP reordered as
//! `reorderTriples` orders it, and the algebra walked as rdflib's `traverse` walks it, a filter's expression before
//! its pattern.

use std::cmp::Ordering;
use std::collections::{BTreeMap, BTreeSet};

use oxigraph::model::Literal;
use oxigraph::model::vocab::rdf;
use spargebra::Query;
use spargebra::algebra::{Expression, GraphPattern, PropertyPathExpression};
use spargebra::term::{NamedNodePattern, TermPattern, TriplePattern};

use orexis::store::Store;

use super::{literal_n3, parseable, path_iris};

/// One term of a pattern, as rdflib holds it: a token's variable is the variable of its name, as `$tank` and `?tank`
/// are one variable to SPARQL.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub(crate) enum Node {
    Var(String),
    Blank(String),
    Iri(String),
    Lit(Literal),
}

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub(crate) enum Pred {
    Iri(String),
    Var(String),
    Path(PropertyPathExpression),
}

pub(crate) type Pat = (Node, Pred, Node);

pub(super) fn variable(name: &str) -> String {
    name.strip_prefix("token__").unwrap_or(name).to_string()
}

pub(super) fn node(term: &TermPattern) -> Node {
    match term {
        TermPattern::Variable(v) => Node::Var(variable(v.as_str())),
        TermPattern::BlankNode(b) => Node::Blank(b.as_str().to_string()),
        TermPattern::NamedNode(n) => Node::Iri(n.as_str().to_string()),
        TermPattern::Literal(l) => Node::Lit(l.clone()),
        #[allow(unreachable_patterns)]
        _ => Node::Blank(String::new()),
    }
}

pub(super) fn pred(p: &NamedNodePattern) -> Pred {
    match p {
        NamedNodePattern::NamedNode(n) => Pred::Iri(n.as_str().to_string()),
        NamedNodePattern::Variable(v) => Pred::Var(variable(v.as_str())),
    }
}

/// What one pattern reads: its predicate's IRIs, or a type pattern's class; `None` for a variable predicate.
pub(crate) fn read_of(pattern: &Pat) -> Option<BTreeSet<String>> {
    match (&pattern.1, &pattern.2) {
        (Pred::Iri(p), Node::Iri(class)) if p == rdf::TYPE.as_str() => Some(BTreeSet::from([class.clone()])),
        (Pred::Iri(p), _) => Some(BTreeSet::from([p.clone()])),
        (Pred::Path(path), _) => path_iris(path),
        (Pred::Var(_), _) => None,
    }
}

/// rdflib's order of node kinds, then each kind's own.
fn rank(n: &Node) -> u8 {
    match n {
        Node::Blank(_) => 10,
        Node::Var(_) => 20,
        Node::Iri(_) => 30,
        Node::Lit(_) => 40,
    }
}

fn text_of(n: &Node) -> &str {
    match n {
        Node::Var(s) | Node::Blank(s) | Node::Iri(s) => s,
        Node::Lit(l) => l.value(),
    }
}

fn compare_nodes(a: &Node, b: &Node) -> Ordering {
    rank(a).cmp(&rank(b)).then_with(|| text_of(a).cmp(text_of(b)))
}

fn pred_node(p: &Pred) -> Node {
    match p {
        Pred::Iri(s) => Node::Iri(s.clone()),
        Pred::Var(s) => Node::Var(s.clone()),
        Pred::Path(path) => Node::Iri(path.to_string()),
    }
}

fn compare(a: &Pat, b: &Pat) -> Ordering {
    compare_nodes(&a.0, &b.0)
        .then_with(|| compare_nodes(&pred_node(&a.1), &pred_node(&b.1)))
        .then_with(|| compare_nodes(&a.2, &b.2))
}

fn is_var(n: &Node) -> bool {
    matches!(n, Node::Var(_) | Node::Blank(_))
}

/// rdflib's `reorderTriples`: the patterns with most terms bound first, by the variables the block before binds.
pub(crate) fn reorder(patterns: Vec<Pat>) -> Vec<Pat> {
    let terms = |t: &Pat| [t.0.clone(), pred_node(&t.1), t.2.clone()];
    let mut count: BTreeMap<String, i64> = BTreeMap::new();
    let id = |n: &Node| format!("{}{}", rank(n), text_of(n));
    for t in &patterns {
        for c in terms(t) {
            if is_var(&c) {
                *count.entry(id(&c)).or_default() += 1;
            }
        }
    }
    let mut known: BTreeSet<String> = BTreeSet::new();
    let key = |t: &Pat, known: &BTreeSet<String>| {
        let ts = terms(t);
        let unbound = ts.iter().filter(|c| is_var(c) && !known.contains(&id(c))).count() as i64;
        let sum: i64 = ts.iter().map(|c| count.get(&id(c)).copied().unwrap_or(0)).sum();
        (unbound, -sum, !matches!(t.2, Node::Lit(_)))
    };
    let mut l: Vec<((i64, i64, bool), Pat)> = patterns.into_iter().map(|t| ((0, 0, false), t)).collect();
    let mut i = 0;
    while i < l.len() {
        let mut rest: Vec<((i64, i64, bool), Pat)> = l.drain(i..).map(|(_, t)| (key(&t, &known), t)).collect();
        rest.sort_by(|a, b| a.0.cmp(&b.0).then_with(|| compare(&a.1, &b.1)));
        l.extend(rest);
        let top = l[i].0.0;
        let mut j = 0;
        while i + j < l.len() && l[i + j].0.0 == top {
            for c in terms(&l[i + j].1) {
                if is_var(&c) {
                    known.insert(id(&c));
                }
            }
            j += 1;
        }
        i += 1;
    }
    l.into_iter().map(|(_, t)| t).collect()
}

/// Every triple pattern under a SELECT's WHERE, in rdflib's order and each once — `None` where one reads anything.
pub(crate) fn patterns_of(store: &Store, text: &str) -> Option<Vec<Pat>> {
    let Ok(Query::Select { pattern, .. }) = store.parse_query(&parseable(text)) else {
        return None;
    };
    let mut found = Vec::new();
    walk(&pattern, &mut found);
    let mut out: Vec<Pat> = Vec::new();
    for t in found {
        if !out.contains(&t) {
            out.push(t);
        }
    }
    out.iter().all(|t| read_of(t).is_some()).then_some(out)
}

fn bgp(patterns: &[TriplePattern]) -> Vec<Pat> {
    patterns
        .iter()
        .map(|t| (node(&t.subject), pred(&t.predicate), node(&t.object)))
        .collect()
}

/// As rdflib's `traverse` walks the algebra, children before the node, each node's children in the order its
/// fields were made: a filter's expression before its pattern, a left join's right before its expression.
fn walk(pattern: &GraphPattern, out: &mut Vec<Pat>) {
    match pattern {
        GraphPattern::Bgp { patterns } => out.extend(reorder(bgp(patterns))),
        GraphPattern::Path { subject, path, object } => {
            out.push((node(subject), Pred::Path(path.clone()), node(object)));
        }
        GraphPattern::Join { left, right }
        | GraphPattern::Union { left, right }
        | GraphPattern::Minus { left, right } => {
            walk(left, out);
            walk(right, out);
        }
        GraphPattern::LeftJoin {
            left,
            right,
            expression,
        } => {
            walk(left, out);
            walk(right, out);
            if let Some(e) = expression {
                expression_walk(e, out);
            }
        }
        GraphPattern::Filter { expr, inner } => {
            expression_walk(expr, out);
            walk(inner, out);
        }
        GraphPattern::Extend { inner, expression, .. } => {
            walk(inner, out);
            expression_walk(expression, out);
        }
        GraphPattern::Graph { inner, .. }
        | GraphPattern::OrderBy { inner, .. }
        | GraphPattern::Project { inner, .. }
        | GraphPattern::Distinct { inner }
        | GraphPattern::Reduced { inner }
        | GraphPattern::Slice { inner, .. }
        | GraphPattern::Group { inner, .. }
        | GraphPattern::Service { inner, .. } => walk(inner, out),
        _ => {}
    }
}

/// An `EXISTS` is read twice, as rdflib holds it twice: its group as parsed, triples in the order written and its
/// nested filters popped out, then its translated algebra, walked as any group.
fn expression_walk(expression: &Expression, out: &mut Vec<Pat>) {
    match expression {
        Expression::Exists(pattern) => {
            as_written(pattern, out);
            walk(pattern, out);
        }
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
        | Expression::Divide(a, b) => {
            expression_walk(a, out);
            expression_walk(b, out);
        }
        Expression::UnaryPlus(a) | Expression::UnaryMinus(a) | Expression::Not(a) => expression_walk(a, out),
        Expression::If(a, b, c) => {
            expression_walk(a, out);
            expression_walk(b, out);
            expression_walk(c, out);
        }
        Expression::In(a, list) => {
            expression_walk(a, out);
            list.iter().for_each(|e| expression_walk(e, out));
        }
        Expression::Coalesce(list) | Expression::FunctionCall(_, list) => {
            list.iter().for_each(|e| expression_walk(e, out))
        }
        _ => {}
    }
}

/// A group's triples in the order written, its filters left out.
fn as_written(pattern: &GraphPattern, out: &mut Vec<Pat>) {
    match pattern {
        GraphPattern::Bgp { patterns } => out.extend(bgp(patterns)),
        GraphPattern::Path { subject, path, object } => {
            out.push((node(subject), Pred::Path(path.clone()), node(object)));
        }
        GraphPattern::Join { left, right }
        | GraphPattern::Union { left, right }
        | GraphPattern::Minus { left, right }
        | GraphPattern::LeftJoin { left, right, .. } => {
            as_written(left, out);
            as_written(right, out);
        }
        GraphPattern::Filter { inner, .. }
        | GraphPattern::Extend { inner, .. }
        | GraphPattern::Graph { inner, .. }
        | GraphPattern::Project { inner, .. }
        | GraphPattern::Distinct { inner } => as_written(inner, out),
        _ => {}
    }
}

/// A pattern's term as the SPARQL text it is; a blank node as a variable of its own, since a pattern's is one.
pub(super) fn spell(n: &Node) -> String {
    match n {
        Node::Var(v) => format!("?{v}"),
        Node::Blank(b) => format!("?_b{b}"),
        Node::Iri(i) => format!("<{i}>"),
        Node::Lit(l) => literal_n3(l),
    }
}

pub(super) fn spell_pred(p: &Pred) -> String {
    match p {
        Pred::Iri(i) => format!("<{i}>"),
        Pred::Var(v) => format!("?{v}"),
        Pred::Path(path) => format!("({path})"),
    }
}
