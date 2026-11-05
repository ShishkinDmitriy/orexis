//! THE FOOTPRINT PER FILLING: predicates on keys, as `footprint.atoms_of` reads them — what `scope_actions`
//! partitions. A precondition's patterns are asked over the common beliefs as a chain of OPTIONALs, so the ORDER
//! they are asked in is part of the answer: it is rdflib's, each BGP reordered as `reorderTriples` orders it and
//! the algebra walked as rdflib's `traverse` walks it, a filter's expression before its pattern.

use std::cmp::Ordering;
use std::collections::{BTreeMap, BTreeSet};

use oxigraph::model::vocab::rdf;
use oxigraph::model::{Literal, Term};
use oxsdatatypes::DateTime;
use spargebra::Query;
use spargebra::algebra::{Expression, GraphPattern, PropertyPathExpression};
use spargebra::term::{GroundTermPattern, NamedNodePattern, TermPattern, TriplePattern};

use orexis::Error;
use orexis::hash::py_str;
use orexis::ontology::{ACTION, BELIEF};
use orexis::store::{Row, Store, Within, iri, value};
use orexis_belief::transition::Parts;

use super::{literal_n3, parseable, path_iris, read, values_in};
use crate::admit::local_of;
use crate::ontology::ANYTHING;

/// What an atom is keyed by: the values the filling binds its subject by, sorted — `None` where it binds none,
/// which is every atom of the predicate.
pub type Key = Option<Vec<String>>;

/// A predicate on a key.
pub type Atom = (String, Key);

/// One filling an action takes as the world alone decides it: the atoms it reads of what some action writes and
/// the atoms it writes, and the world's IRIs it binds.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Filling {
    pub atoms: BTreeSet<Atom>,
    pub terms: BTreeSet<String>,
}

/// An atom as Python's `str` of its tuple spells it — what the partition is sorted by.
pub fn spelled(atom: &Atom) -> String {
    let key = match &atom.1 {
        None => "None".to_string(),
        Some(values) if values.len() == 1 => format!("({},)", py_str(&values[0])),
        Some(values) => format!("({})", values.iter().map(|v| py_str(v)).collect::<Vec<_>>().join(", ")),
    };
    format!("({}, {key})", py_str(&atom.0))
}

// --- a precondition's patterns, in rdflib's order --------------------------------------------------------------

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

fn variable(name: &str) -> String {
    name.strip_prefix("token__").unwrap_or(name).to_string()
}

fn node(term: &TermPattern) -> Node {
    match term {
        TermPattern::Variable(v) => Node::Var(variable(v.as_str())),
        TermPattern::BlankNode(b) => Node::Blank(b.as_str().to_string()),
        TermPattern::NamedNode(n) => Node::Iri(n.as_str().to_string()),
        TermPattern::Literal(l) => Node::Lit(l.clone()),
        #[allow(unreachable_patterns)]
        _ => Node::Blank(String::new()),
    }
}

fn pred(p: &NamedNodePattern) -> Pred {
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
fn spell(n: &Node) -> String {
    match n {
        Node::Var(v) => format!("?{v}"),
        Node::Blank(b) => format!("?_b{b}"),
        Node::Iri(i) => format!("<{i}>"),
        Node::Lit(l) => literal_n3(l),
    }
}

fn spell_pred(p: &Pred) -> String {
    match p {
        Pred::Iri(i) => format!("<{i}>"),
        Pred::Var(v) => format!("?{v}"),
        Pred::Path(path) => format!("({path})"),
    }
}

// --- the footprint of each action ------------------------------------------------------------------------------

const ACTIONS_Q: &str = "
SELECT ?action ?precondition ?update WHERE {
  ?action a orexis:Action .
  OPTIONAL { ?action planning:precondition ?precondition }
  OPTIONAL { ?action planning:effect/sh:rule ?r . ?r a belief:Transition ; belief:update ?update }
}";

const TAKES_Q: &str = "SELECT ?action ?takes WHERE { ?action a orexis:Action ; orexis:takes ?takes }";

/// An action's precondition and its effect's updates, each read as the machine reads it — `None` for one the
/// machine refuses, which writes anything.
struct Effect {
    precondition: Option<String>,
    updates: Vec<Option<Parts>>,
}

impl Effect {
    /// An effect states one only where an update inserts, or will not be read.
    fn states(&self) -> bool {
        self.updates
            .iter()
            .any(|u| u.as_ref().is_none_or(|p| !p.insert.is_empty()))
    }
}

fn effects(store: &Store, at: DateTime) -> Result<BTreeMap<String, Effect>, Error> {
    let graphs = store.graphs_of(&[ACTION], &Within::at(at))?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let mut out: BTreeMap<String, Effect> = BTreeMap::new();
    for row in store.rows(ACTIONS_Q, &graphs)? {
        let Some(action) = iri(&row, "action") else { continue };
        let held = out.entry(action).or_insert_with(|| Effect {
            precondition: value(&row, "precondition"),
            updates: Vec::new(),
        });
        if let Some(text) = value(&row, "update") {
            held.updates.push(read(store, &text));
        }
    }
    Ok(out)
}

/// What an effect writes, the predicates of its templates — `None` where an insert's cannot be read; a delete's
/// that cannot is left out, since it takes the node an insert replaces.
fn writes(effect: &Effect) -> Option<BTreeSet<String>> {
    let mut out = BTreeSet::new();
    for update in &effect.updates {
        let parts = update.as_ref()?;
        if parts.insert.is_empty() {
            continue;
        }
        let predicates: Vec<(&NamedNodePattern, Option<String>)> = parts
            .insert
            .iter()
            .map(|q| {
                (
                    &q.predicate,
                    match &q.object {
                        TermPattern::NamedNode(n) => Some(n.as_str().to_string()),
                        _ => None,
                    },
                )
            })
            .collect();
        out.extend(template(&predicates, &parts.pattern)?);
    }
    for parts in effect.updates.iter().flatten() {
        let predicates: Vec<(&NamedNodePattern, Option<String>)> = parts
            .delete
            .iter()
            .map(|q| {
                (
                    &q.predicate,
                    match &q.object {
                        GroundTermPattern::NamedNode(n) => Some(n.as_str().to_string()),
                        _ => None,
                    },
                )
            })
            .collect();
        if !predicates.is_empty()
            && let Some(found) = template(&predicates, &parts.pattern)
        {
            out.extend(found);
        }
    }
    Some(out)
}

fn template(predicates: &[(&NamedNodePattern, Option<String>)], pattern: &GraphPattern) -> Option<BTreeSet<String>> {
    let mut out = BTreeSet::new();
    let mut bounded = None;
    for (p, o) in predicates {
        match p {
            NamedNodePattern::NamedNode(n) if n.as_ref() == rdf::TYPE && o.is_some() => {
                out.insert(o.clone().expect("a class"));
            }
            NamedNodePattern::NamedNode(n) => {
                out.insert(n.as_str().to_string());
            }
            NamedNodePattern::Variable(v) => {
                let values = bounded.get_or_insert_with(|| values_in(pattern));
                out.extend(values.get(v).cloned().flatten().filter(|i| !i.is_empty())?);
            }
        }
    }
    Some(out)
}

/// What an effect writes as subject variable → predicates — `None` where a template's subject is not a variable or
/// its predicate is.
fn written_subjects(effect: &Effect) -> Option<BTreeMap<String, BTreeSet<String>>> {
    let mut out: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for update in &effect.updates {
        let parts = update.as_ref()?;
        let mut triples: Vec<(Node, Pred, Node)> = Vec::new();
        for q in &parts.insert {
            triples.push((node(&q.subject), pred(&q.predicate), node(&q.object)));
        }
        for q in &parts.delete {
            let ground = |t: &GroundTermPattern| match t {
                GroundTermPattern::Variable(v) => Node::Var(variable(v.as_str())),
                GroundTermPattern::NamedNode(n) => Node::Iri(n.as_str().to_string()),
                GroundTermPattern::Literal(l) => Node::Lit(l.clone()),
                #[allow(unreachable_patterns)]
                _ => Node::Blank(String::new()),
            };
            triples.push((ground(&q.subject), pred(&q.predicate), ground(&q.object)));
        }
        for (s, p, o) in triples {
            let Node::Var(s) = s else { return None };
            match (p, o) {
                (Pred::Iri(p), Node::Iri(class)) if p == rdf::TYPE.as_str() => {
                    out.entry(s).or_default().insert(class);
                }
                (Pred::Iri(p), _) => {
                    out.entry(s).or_default().insert(p);
                }
                _ => return None,
            }
        }
    }
    Some(out)
}

/// What one action reads and writes: `None` on a side that cannot be read, anything.
pub type Footprint = (Option<BTreeSet<String>>, Option<BTreeSet<String>>);

/// Every action the store holds that states an effect, as what its precondition reads and what its effect writes.
pub fn actions_of(store: &Store, at: DateTime) -> Result<BTreeMap<String, Footprint>, Error> {
    let mut out = BTreeMap::new();
    for (action, effect) in effects(store, at)? {
        if !effect.states() {
            continue;
        }
        let reads = match &effect.precondition {
            Some(text) => super::reads_of_select(store, text),
            None => Some(BTreeSet::new()),
        };
        out.insert(action, (reads, writes(&effect)));
    }
    Ok(out)
}

/// Every predicate some action's effect can write — nothing where one writes anything, and then nothing is left out.
pub fn written(store: &Store, at: DateTime) -> Result<BTreeSet<String>, Error> {
    let mut out = BTreeSet::new();
    for (_, writes) in actions_of(store, at)?.into_values() {
        match writes {
            Some(w) => out.extend(w),
            None => return Ok(BTreeSet::new()),
        }
    }
    Ok(out)
}

/// Every action the store holds as its fillings — `None` where its texts cannot be read so. An action stating no
/// effect has no entry, and one every row of which leaves unbound a parameter the world alone decides has none.
pub fn atoms_of(store: &Store, at: DateTime) -> Result<BTreeMap<String, Option<Vec<Filling>>>, Error> {
    let mut out = BTreeMap::new();
    let effects = effects(store, at)?;
    if effects.is_empty() {
        return Ok(out);
    }
    let stated = store.graphs_of(
        &[BELIEF],
        &Within {
            common: true,
            ..Within::at(at)
        },
    )?;
    let stated: Vec<&str> = stated.iter().map(String::as_str).collect();
    let changeable: BTreeSet<String> = effects
        .values()
        .filter(|e| e.states())
        .filter_map(writes)
        .flatten()
        .collect();
    let actions = store.graphs_of(&[ACTION], &Within::at(at))?;
    let actions: Vec<&str> = actions.iter().map(String::as_str).collect();
    let mut takes: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for row in store.rows(TAKES_Q, &actions)? {
        if let (Some(action), Some(param)) = (iri(&row, "action"), iri(&row, "takes")) {
            takes.entry(action).or_default().insert(local_of(&param));
        }
    }
    let written: BTreeMap<&String, Option<BTreeMap<String, BTreeSet<String>>>> = effects
        .iter()
        .filter(|(_, e)| e.states())
        .map(|(a, e)| (a, written_subjects(e)))
        .collect();
    let mut touched = changeable.clone();
    for subjects in written.values().flatten() {
        touched.extend(subjects.values().flatten().cloned());
    }
    for (action, effect) in &effects {
        if !effect.states() {
            continue;
        }
        let parsed = match &effect.precondition {
            Some(text) => patterns_of(store, text),
            None => Some(Vec::new()),
        };
        let (Some(parsed), Some(subjects)) = (parsed, written[action].as_ref()) else {
            out.insert(action.clone(), None);
            continue;
        };
        let decided = decided_by_the_world(&parsed, subjects, &touched, takes.get(action));
        let found = fillings(store, &stated, &parsed, subjects, &changeable, &decided);
        if !decided.is_empty() && found.is_empty() {
            log::info!(
                "{action} takes {}, of which this world states none: it has no filling here, and is in no scope",
                decided.iter().cloned().collect::<Vec<_>>().join(", ")
            );
        }
        out.insert(action.clone(), Some(found));
    }
    Ok(out)
}

/// The parameters an action takes that the WORLD ALONE decides: each stands in some pattern, is no subject the
/// effect writes, and stands in no pattern reading a predicate any effect writes or deletes.
fn decided_by_the_world(
    patterns: &[Pat],
    written: &BTreeMap<String, BTreeSet<String>>,
    touched: &BTreeSet<String>,
    takes: Option<&BTreeSet<String>>,
) -> BTreeSet<String> {
    let mut out = BTreeSet::new();
    for param in takes.into_iter().flatten() {
        let var = Node::Var(param.clone());
        let stands: Vec<&Pat> = patterns.iter().filter(|t| t.0 == var || t.2 == var).collect();
        if stands.is_empty() || written.contains_key(param) {
            continue;
        }
        let reads: BTreeSet<String> = stands.iter().filter_map(|t| read_of(t)).flatten().collect();
        if reads.is_disjoint(touched) {
            out.insert(param.clone());
        }
    }
    out
}

/// A key value as text; an IRI among them is a term a scope may hold as a member.
fn key_value(term: &Term, iris: &mut BTreeSet<String>) -> String {
    match term {
        Term::NamedNode(n) => {
            iris.insert(n.as_str().to_string());
            n.as_str().to_string()
        }
        Term::Literal(l) => l.value().to_string(),
        other => other.to_string(),
    }
}

/// Each filling the world alone decides: the common beliefs asked the precondition's patterns, every one OPTIONAL
/// and no filter, and the atoms each row reads of what some action writes, and writes.
fn fillings(
    store: &Store,
    stated: &[&str],
    patterns: &[Pat],
    written: &BTreeMap<String, BTreeSet<String>>,
    changeable: &BTreeSet<String>,
    decided: &BTreeSet<String>,
) -> Vec<Filling> {
    let mut rows: Vec<Row> = vec![Row::new()];
    if !patterns.is_empty() {
        let text = format!(
            "SELECT DISTINCT * WHERE {{ {} }}",
            patterns
                .iter()
                .map(|(s, p, o)| format!("OPTIONAL {{ {} {} {} . }}", spell(s), spell_pred(p), spell(o)))
                .collect::<Vec<_>>()
                .join(" ")
        );
        match store.rows(&text, stated) {
            Ok(found) => {
                rows = if found.is_empty() { vec![Row::new()] } else { found };
                rows.retain(|bound| decided.iter().all(|d| bound.contains_key(d)));
                if rows.is_empty() {
                    return Vec::new();
                }
            }
            Err(e) => log::debug!("a precondition's patterns would not run over the common beliefs: {e}"),
        }
    }
    let mut links: BTreeMap<String, Vec<Node>> = BTreeMap::new();
    for (s, _, o) in patterns {
        for (a, b) in [(s, o), (o, s)] {
            if let Node::Var(a) = a
                && !matches!(b, Node::Blank(_))
            {
                let held = links.entry(a.clone()).or_default();
                if !held.contains(b) {
                    held.push(b.clone());
                }
            }
        }
    }
    let mut out = Vec::new();
    for bound in &rows {
        let mut iris = BTreeSet::new();
        let key = |var: &str, iris: &mut BTreeSet<String>| -> Key {
            if let Some(term) = bound.get(var) {
                return Some(vec![key_value(term, iris)]);
            }
            let mut linked = BTreeSet::new();
            for other in links.get(var).into_iter().flatten() {
                match other {
                    Node::Var(v) => {
                        if let Some(term) = bound.get(v) {
                            linked.insert(key_value(term, iris));
                        }
                    }
                    Node::Iri(i) => {
                        iris.insert(i.clone());
                        linked.insert(i.clone());
                    }
                    Node::Lit(l) => {
                        linked.insert(l.value().to_string());
                    }
                    Node::Blank(_) => {}
                }
            }
            (!linked.is_empty()).then(|| linked.into_iter().collect())
        };
        let mut atoms = BTreeSet::new();
        for t in patterns {
            let Node::Var(s) = &t.0 else { continue };
            for predicate in read_of(t).into_iter().flatten() {
                if changeable.contains(&predicate) {
                    atoms.insert((predicate, key(s, &mut iris)));
                }
            }
        }
        for (subject, predicates) in written {
            for predicate in predicates {
                atoms.insert((predicate.clone(), key(subject, &mut iris)));
            }
        }
        for term in bound.values() {
            key_value(term, &mut iris);
        }
        out.push(Filling { atoms, terms: iris });
    }
    out
}

// --- the derivations' edges --------------------------------------------------------------------------------------

const EDGES_Q: &str = "
SELECT ?d ?reads ?writes WHERE {
  ?d a planning:Derivation .
  OPTIONAL { ?d planning:reads ?reads }
  OPTIONAL { ?d planning:writes ?writes } }";

/// One side of an edge: the predicates, or `None` for anything.
pub type Side = Option<BTreeSet<String>>;

/// The derivations' `(reads, writes)` edges read back from `graphs`, by the derivation's name.
pub fn stored_edges(store: &Store, graphs: &[&str]) -> Result<Vec<(Side, Side)>, Error> {
    let mut sides: BTreeMap<String, (BTreeSet<String>, BTreeSet<String>)> = BTreeMap::new();
    for row in store.rows(EDGES_Q, graphs)? {
        let Some(d) = row.get("d").map(|t| t.to_string()) else {
            continue;
        };
        let (reads, writes) = sides.entry(d).or_default();
        reads.extend(iri(&row, "reads"));
        writes.extend(iri(&row, "writes"));
    }
    let side = |s: BTreeSet<String>| (!s.contains(ANYTHING)).then_some(s);
    Ok(sides.into_values().map(|(r, w)| (side(r), side(w))).collect())
}

#[cfg(test)]
mod tests;
