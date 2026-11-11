//! WHAT AN AGENT SAYS OF ITS OWN FUTURE UNDER ONE CONSTRAINT, as `agent/coordination/holdings.py` reads it: the values
//! its walking plans give the things it acts for on the constraint's key, each over the period it holds.
//!
//! **THE KEY IS READ OFF THE CONSTRAINT**: the predicates its select joins two subjects on, read by parsing the text,
//! never by naming a domain's word. **A HOLDING IS READ OFF THE INTENTIONS**: for each thing the agent acts for, the
//! values it holds now, then each step of a walking intention whose predicted change gives the thing new values on the
//! key — the old values holding until the step's latest landing, the new from its earliest. Nothing is said where no
//! step changes the key. And the one shape holdings take in what is said — written by `ask` and `answer`, read by both
//! and by `lay` — and whether two holdings want one resource, by the constraint's own word.

use std::collections::{BTreeMap, BTreeSet};
use std::sync::Arc;

use oxigraph::model::{
    BlankNode, GraphName, GraphNameRef, Literal, NamedNode, NamedNodeRef, NamedOrBlankNode, Quad, Term,
};
use oxsdatatypes::DateTime;
use spargebra::algebra::GraphPattern;
use spargebra::term::{NamedNodePattern, TermPattern, TriplePattern};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{instant, isoformat};
use orexis::document::Document;
use orexis::ontology::{BELIEF, FORECAST, SELF_GRAPH};
use orexis::store::{Row, Store, Within, iri, value};

use crate::ontology::{COMMITTED_STEP_GRAPH, CONSTRAINT_GRAPH, COORDINATION};

pub(crate) const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const XSD_DATETIME: &str = "http://www.w3.org/2001/XMLSchema#dateTime";
const XSD_BOOLEAN: &str = "http://www.w3.org/2001/XMLSchema#boolean";
const TEMPORAL: &str = "http://purl.org/dc/terms/temporal";
const START: &str = "http://example.org/orexis#start";
const END: &str = "http://example.org/orexis#end";
const SCRATCH: &str = "urn:orexis:coordination:scratch";

/// One thing's values on a constraint's key, over a period: `start` None where the thing holds them now, `end` None
/// where nothing ends them; `taken` where a step already taken — in flight, which nothing cancels — gives them.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct Holding {
    pub thing: String,
    pub values: Vec<(String, Term)>,
    pub start: Option<DateTime>,
    pub end: Option<DateTime>,
    pub taken: bool,
}

impl Holding {
    /// Whether two holdings hold the same values of the key over periods that overlap.
    pub fn overlaps(&self, other: &Holding) -> bool {
        self.values == other.values
            && (other.end.is_none() || self.start.is_none() || self.start < other.end)
            && (self.end.is_none() || other.start.is_none() || other.start < self.end)
    }
}

/// Values sorted as the Python sorts them: by predicate, then by the term's N-Triples form.
pub(crate) fn sorted(mut values: Vec<(String, Term)>) -> Vec<(String, Term)> {
    values.sort_by(|a, b| (a.0.as_str(), a.1.to_string()).cmp(&(b.0.as_str(), b.1.to_string())));
    values.dedup();
    values
}

pub(crate) fn strs(names: &[String]) -> Vec<&str> {
    names.iter().map(String::as_str).collect()
}

pub(crate) fn rows_of(
    store: &Store,
    text: &str,
    values: &[(&str, Value)],
    graphs: &[String],
) -> Result<Vec<Row>, Error> {
    store.rows(&bind(text, values)?, &strs(graphs))
}

pub(crate) fn common(store: &Store) -> Result<Vec<String>, Error> {
    store.graphs_of(&[BELIEF], &Within::common())
}

pub(crate) fn of_kind(store: &Store, kinds: &[&str]) -> Result<Vec<String>, Error> {
    store.graphs_of(kinds, &Within::default())
}

/// The constraint graphs and the self graphs together, where a held constraint is read.
pub(crate) fn constraints_and_self(store: &Store) -> Result<Vec<String>, Error> {
    let mut out = of_kind(store, &[CONSTRAINT_GRAPH])?;
    out.extend(of_kind(store, &[SELF_GRAPH])?);
    Ok(out)
}

pub(crate) fn at_of(text: Option<String>) -> Result<Option<DateTime>, Error> {
    text.map(|t| instant(&t)).transpose()
}

/// WHAT A CONSTRAINT SAYS IS UNMET OR MET: the select under either polarity.
pub(crate) const TEXTS_Q: &str = "
SELECT ?text WHERE {
  { $constraint planning:unmetWhen ?s . ?s sh:select ?text }
  UNION { $constraint planning:metWhen ?shape . ?shape sh:sparql ?c . ?c sh:select ?text } }";

/// THE THINGS THE AGENT ACTS FOR.
const THINGS_Q: &str = "SELECT ?t WHERE { ?me a orexis:Self ; orexis:actsFor ?t } ORDER BY ?t";
const VALUES_Q: &str = "SELECT ?p ?v WHERE { $thing ?p ?v }";

/// EVERY STANDING INTENTION, the plan it adopts, the step it stands at and the want it pursues; and whether it ends
/// after it.
const STANDING_Q: &str = "
SELECT ?plan ?step ?ending ?act ?want WHERE { GRAPH ?g { ?i a execution:Intention ; execution:by ?step ; execution:adopts ?plan .
  FILTER NOT EXISTS { ?i execution:resolvedAt ?done } OPTIONAL { ?i execution:endsAfter ?ending } OPTIONAL { ?i execution:pursues ?want }
  OPTIONAL { ?act execution:of ?step ; execution:taken true } } }";

/// A PLAN'S STEPS: each, the one after it, the graph naming what it adds, and the two ends of its landing.
const STEPS_Q: &str = "
SELECT ?step ?next ?adds ?lands ?latest WHERE { GRAPH $plan { ?step a execution:Step .
  OPTIONAL { ?step execution:then ?next } OPTIONAL { ?step execution:adds ?adds }
  OPTIONAL { ?step execution:landsAt ?lands } OPTIONAL { ?step execution:notAfter ?latest } } }";

/// The things the self of `store` acts for.
pub(crate) fn things(store: &Store) -> Result<Vec<String>, Error> {
    let mut graphs = common(store)?;
    graphs.extend(of_kind(store, &[SELF_GRAPH])?);
    Ok(rows_of(store, THINGS_Q, &[], &graphs)?
        .iter()
        .filter_map(|r| iri(r, "t"))
        .collect())
}

/// Every holding of the things the self of `store` acts for under `constraint`, standing at `at`.
pub fn holdings(store: &Store, constraint: &str, at: DateTime) -> Result<Vec<Holding>, Error> {
    let key = key_of(store, constraint)?;
    if key.is_empty() {
        return Ok(Vec::new());
    }
    let things = things(store)?;
    let present = present(store, at)?;
    let changes = changes(store, &things, &key)?;
    let mut out = Vec::new();
    for thing in &things {
        let mut now: BTreeMap<String, Term> = BTreeMap::new();
        for r in rows_of(store, VALUES_Q, &[("thing", Value::iri(thing.as_str()))], &present)? {
            if let Some(p) = iri(&r, "p")
                && key.contains(&p)
            {
                now.insert(p.clone(), term(store, thing, &p, &present)?);
            }
        }
        let steps = changes.get(thing).cloned().unwrap_or_default();
        if now.keys().cloned().collect::<BTreeSet<_>>() != key || steps.is_empty() {
            continue;
        }
        let (mut values, mut start, mut taken) = (now, None, false);
        for change in steps {
            out.push(Holding {
                thing: thing.clone(),
                values: sorted(values.clone().into_iter().collect()),
                start,
                end: change.latest.or(change.lands),
                taken,
            });
            values.extend(change.values);
            start = change.lands;
            taken = change.in_flight;
        }
        out.push(Holding {
            thing: thing.clone(),
            values: sorted(values.into_iter().collect()),
            start,
            end: None,
            taken,
        });
    }
    Ok(out)
}

/// The wants of the standing intentions whose plans change a value on `constraint`'s key of a thing the self acts for.
pub fn walking_over(store: &Store, constraint: &str) -> Result<BTreeSet<String>, Error> {
    let key = key_of(store, constraint)?;
    if key.is_empty() {
        return Ok(BTreeSet::new());
    }
    let things = things(store)?;
    Ok(changes(store, &things, &key)?
        .into_values()
        .flatten()
        .filter_map(|c| c.want)
        .collect())
}

/// The predicates `constraint` joins two subjects on. Empty where its text will not parse or joins nothing.
pub fn key_of(store: &Store, constraint: &str) -> Result<BTreeSet<String>, Error> {
    let mut graphs = of_kind(store, &[CONSTRAINT_GRAPH])?;
    graphs.extend(common(store)?);
    let mut out = BTreeSet::new();
    for r in rows_of(store, TEXTS_Q, &[("constraint", Value::iri(constraint))], &graphs)? {
        if let Some(text) = value(&r, "text") {
            out.extend(key(store, &text));
        }
    }
    Ok(out)
}

fn key(store: &Store, text: &str) -> BTreeSet<String> {
    let Ok(query) = store.parse_query(text) else {
        return BTreeSet::new();
    };
    let pattern = match &query {
        spargebra::Query::Select { pattern, .. }
        | spargebra::Query::Construct { pattern, .. }
        | spargebra::Query::Describe { pattern, .. }
        | spargebra::Query::Ask { pattern, .. } => pattern,
    };
    let mut triples = Vec::new();
    walk(pattern, &mut triples);
    let mut subjects: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for t in &triples {
        if let (NamedNodePattern::NamedNode(p), TermPattern::Variable(o)) = (&t.predicate, &t.object)
            && p.as_str() != RDF_TYPE
        {
            subjects
                .entry(o.as_str().to_string())
                .or_default()
                .insert(t.subject.to_string());
        }
    }
    triples
        .iter()
        .filter_map(|t| match (&t.predicate, &t.object) {
            (NamedNodePattern::NamedNode(p), TermPattern::Variable(o))
                if p.as_str() != RDF_TYPE && subjects.get(o.as_str()).is_some_and(|s| s.len() > 1) =>
            {
                Some(p.as_str().to_string())
            }
            _ => None,
        })
        .collect()
}

/// Every triple pattern of every basic graph pattern under `pattern`.
fn walk(pattern: &GraphPattern, out: &mut Vec<TriplePattern>) {
    use GraphPattern as G;
    match pattern {
        G::Bgp { patterns } => out.extend(patterns.iter().cloned()),
        G::Join { left, right } | G::Union { left, right } | G::Minus { left, right } => {
            walk(left, out);
            walk(right, out);
        }
        G::LeftJoin { left, right, .. } => {
            walk(left, out);
            walk(right, out);
        }
        G::Filter { inner, .. }
        | G::Graph { inner, .. }
        | G::Extend { inner, .. }
        | G::OrderBy { inner, .. }
        | G::Project { inner, .. }
        | G::Distinct { inner }
        | G::Reduced { inner }
        | G::Slice { inner, .. }
        | G::Group { inner, .. }
        | G::Service { inner, .. } => walk(inner, out),
        _ => {}
    }
}

/// What the agent believes holds at `at`: every belief holding then, save its self graph, a forecast and a committed
/// step.
pub(crate) fn present(store: &Store, at: DateTime) -> Result<Vec<String>, Error> {
    let aside: BTreeSet<String> = of_kind(store, &[SELF_GRAPH, FORECAST, COMMITTED_STEP_GRAPH])?
        .into_iter()
        .collect();
    Ok(store
        .graphs_of(&[BELIEF], &Within::at(at))?
        .into_iter()
        .filter(|g| !aside.contains(g))
        .collect())
}

/// The value `thing` holds on `predicate` now, as the term it is, read in the first of `graphs` that holds one.
fn term(store: &Store, thing: &str, predicate: &str, graphs: &[String]) -> Result<Term, Error> {
    for graph in graphs {
        let found = store
            .engine()
            .quads_for_pattern(
                Some(NamedNodeRef::new_unchecked(thing).into()),
                Some(NamedNodeRef::new_unchecked(predicate)),
                None,
                Some(GraphNameRef::NamedNode(NamedNodeRef::new_unchecked(graph))),
            )
            .next();
        if let Some(q) = found {
            return Ok(q.map_err(|e| Error::Evaluation(e.to_string()))?.object);
        }
    }
    Err(Error::Evaluation(format!("{thing} holds nothing on {predicate}")))
}

/// One change a walking plan's step makes to a thing's values on the key.
#[derive(Clone, Debug)]
pub(crate) struct Change {
    lands: Option<DateTime>,
    latest: Option<DateTime>,
    values: BTreeMap<String, Term>,
    in_flight: bool,
    want: Option<String>,
}

/// Per thing, every change a walking plan's steps make to its values on the key, in the order they are walked.
fn changes(store: &Store, things: &[String], key: &BTreeSet<String>) -> Result<BTreeMap<String, Vec<Change>>, Error> {
    let mut out: BTreeMap<String, Vec<Change>> = BTreeMap::new();
    for r in store.rows(STANDING_Q, &[])? {
        let (Some(plan), Some(first)) = (iri(&r, "plan"), iri(&r, "step")) else {
            continue;
        };
        let mut chain: BTreeMap<String, Row> = BTreeMap::new();
        for s in store.rows(&bind(STEPS_Q, &[("plan", Value::iri(plan.as_str()))])?, &[])? {
            if let Some(step) = iri(&s, "step") {
                chain.insert(step, s);
            }
        }
        let mut step = Some(first.clone());
        while let Some(at) = step.take() {
            let Some(s) = chain.get(&at) else { break };
            if let Some(adds) = iri(s, "adds") {
                for thing in things {
                    let mut values = BTreeMap::new();
                    for q in store.engine().quads_for_pattern(
                        Some(NamedNodeRef::new_unchecked(thing).into()),
                        None,
                        None,
                        Some(GraphNameRef::NamedNode(NamedNodeRef::new_unchecked(&adds))),
                    ) {
                        let q = q.map_err(|e| Error::Evaluation(e.to_string()))?;
                        if key.contains(q.predicate.as_str()) {
                            values.insert(q.predicate.as_str().to_string(), q.object);
                        }
                    }
                    if !values.is_empty() {
                        out.entry(thing.clone()).or_default().push(Change {
                            lands: at_of(value(s, "lands"))?,
                            latest: at_of(value(s, "latest"))?,
                            values,
                            in_flight: at == first && r.contains_key("act"),
                            want: iri(&r, "want"),
                        });
                    }
                }
            }
            step = if r.contains_key("ending") { None } else { iri(s, "next") };
        }
    }
    for changes in out.values_mut() {
        changes.sort_by(|a, b| a.lands.partial_cmp(&b.lands).unwrap_or(std::cmp::Ordering::Equal));
    }
    Ok(out)
}

// --- holdings in what is said: one shape, written by `ask` and `answer`, read by both and by `lay` -----------------

const HOLDINGS_Q: &str = "
SELECT ?h ?t ?p ?v ?from ?until ?taken WHERE { GRAPH $graph { ?n coordination:holding ?h . ?h coordination:of ?t ; ?p ?v .
  OPTIONAL { ?h coordination:from ?from } OPTIONAL { ?h coordination:until ?until } OPTIONAL { ?h coordination:taken ?taken } } }";

fn named(iri: &str) -> NamedNode {
    NamedNode::new_unchecked(iri)
}

fn at_literal(at: DateTime) -> Literal {
    Literal::new_typed_literal(isoformat(at), named(XSD_DATETIME))
}

/// A document of one graph, `graph`, of `kind`: the node `node` with what `about` says of it, and each holding of
/// `held` hanging off it — the thing, the values on the key with the key's own predicates, and the period; and the
/// graph's own period, where `period` gives one.
pub(crate) fn said(
    graph: &str,
    kind: &str,
    node: &str,
    about: &[(String, Term)],
    held: &[Holding],
    period: Option<(DateTime, DateTime)>,
) -> Document {
    let (g, mut quads) = (named(graph), Vec::new());
    let into = GraphName::NamedNode(g.clone());
    quads.push(Quad::new(
        g.clone(),
        named(RDF_TYPE),
        named(kind),
        GraphName::DefaultGraph,
    ));
    if let Some((start, end)) = period {
        let p = BlankNode::default();
        quads.push(Quad::new(
            g.clone(),
            named(TEMPORAL),
            p.clone(),
            GraphName::DefaultGraph,
        ));
        quads.push(Quad::new(
            p.clone(),
            named(START),
            at_literal(start),
            GraphName::DefaultGraph,
        ));
        quads.push(Quad::new(p, named(END), at_literal(end), GraphName::DefaultGraph));
    }
    let n = named(node);
    for (predicate, value) in about {
        quads.push(Quad::new(n.clone(), named(predicate), value.clone(), into.clone()));
    }
    let word = |w: &str| named(&format!("{COORDINATION}{w}"));
    for (i, h) in held.iter().enumerate() {
        let hn = named(&format!("{node}/holding/{i}"));
        quads.push(Quad::new(n.clone(), word("holding"), hn.clone(), into.clone()));
        quads.push(Quad::new(hn.clone(), named(RDF_TYPE), word("Holding"), into.clone()));
        quads.push(Quad::new(hn.clone(), word("of"), named(&h.thing), into.clone()));
        for (predicate, value) in &h.values {
            quads.push(Quad::new(hn.clone(), named(predicate), value.clone(), into.clone()));
        }
        if let Some(start) = h.start {
            quads.push(Quad::new(hn.clone(), word("from"), at_literal(start), into.clone()));
        }
        if let Some(end) = h.end {
            quads.push(Quad::new(hn.clone(), word("until"), at_literal(end), into.clone()));
        }
        if h.taken {
            let yes = Literal::new_typed_literal("true", named(XSD_BOOLEAN));
            quads.push(Quad::new(hn, word("taken"), yes, into.clone()));
        }
    }
    Document::of_quads(quads)
}

/// The holdings a question or an answer in `graph` carries, as the terms they were said in.
pub(crate) fn heard(store: &Store, graph: &str) -> Result<Vec<Holding>, Error> {
    struct Found {
        thing: String,
        from: Option<String>,
        until: Option<String>,
        taken: bool,
        predicates: BTreeSet<String>,
    }
    let excluded = [
        RDF_TYPE.to_string(),
        format!("{COORDINATION}of"),
        format!("{COORDINATION}from"),
        format!("{COORDINATION}until"),
        format!("{COORDINATION}taken"),
    ];
    let mut found: BTreeMap<String, Found> = BTreeMap::new();
    for r in store.rows(&bind(HOLDINGS_Q, &[("graph", Value::iri(graph))])?, &[])? {
        let (Some(h), Some(t)) = (iri(&r, "h"), iri(&r, "t")) else {
            continue;
        };
        let entry = found.entry(h).or_insert_with(|| Found {
            thing: t,
            from: value(&r, "from"),
            until: value(&r, "until"),
            taken: value(&r, "taken").as_deref() == Some("true"),
            predicates: BTreeSet::new(),
        });
        if let Some(p) = iri(&r, "p")
            && !excluded.contains(&p)
        {
            entry.predicates.insert(p);
        }
    }
    let mut out = Vec::new();
    for (node, h) in found {
        let mut values = Vec::new();
        for p in &h.predicates {
            let q = store
                .engine()
                .quads_for_pattern(
                    Some(NamedNodeRef::new_unchecked(&node).into()),
                    Some(NamedNodeRef::new_unchecked(p)),
                    None,
                    Some(GraphNameRef::NamedNode(NamedNodeRef::new_unchecked(graph))),
                )
                .next();
            if let Some(q) = q {
                values.push((p.clone(), q.map_err(|e| Error::Evaluation(e.to_string()))?.object));
            }
        }
        out.push(Holding {
            thing: h.thing,
            values: sorted(values),
            start: at_of(h.from)?,
            end: at_of(h.until)?,
            taken: h.taken,
        });
    }
    Ok(out)
}

/// A scratch store beside `store`, speaking its namespaces, holding `quads` in the one graph a text is asked over.
pub(crate) fn scratch(
    store: &Store,
    quads: impl IntoIterator<Item = (NamedOrBlankNode, NamedNode, Term)>,
) -> Result<Store, Error> {
    let out = Store::new(Arc::new(store.namespaces().clone()))?;
    let g = named(SCRATCH);
    out.add(quads.into_iter().map(|(s, p, o)| Quad::new(s, p, o, g.clone())))?;
    Ok(out)
}

/// `text` asked over a scratch store's one graph.
pub(crate) fn asked(scratch: &Store, text: &str) -> Result<Vec<Row>, Error> {
    scratch.rows(text, &[SCRATCH])
}

const KINDS_Q: &str = "SELECT ?k WHERE { $thing a ?k }";

/// Whether `constraint` reads a violation where `mine` and `theirs` hold at once: its own select, asked of the two
/// things with the kinds the agent believes them of and the values the holdings give them, and nothing else.
pub(crate) fn violates(store: &Store, constraint: &str, mine: &Holding, theirs: &Holding) -> Result<bool, Error> {
    if !mine.overlaps(theirs) {
        return Ok(false);
    }
    let common = common(store)?;
    let mut quads = Vec::new();
    for h in [mine, theirs] {
        let node: NamedOrBlankNode = named(&h.thing).into();
        for r in rows_of(store, KINDS_Q, &[("thing", Value::iri(h.thing.as_str()))], &common)? {
            if let Some(k) = iri(&r, "k") {
                quads.push((node.clone(), named(RDF_TYPE), named(&k).into()));
            }
        }
        for (predicate, value) in &h.values {
            quads.push((node.clone(), named(predicate), value.clone()));
        }
    }
    let scratch = scratch(store, quads)?;
    let mut graphs = of_kind(store, &[CONSTRAINT_GRAPH])?;
    graphs.extend(common);
    for r in rows_of(store, TEXTS_Q, &[("constraint", Value::iri(constraint))], &graphs)? {
        let Some(text) = value(&r, "text") else { continue };
        match asked(&scratch, &text) {
            Ok(found) if !found.is_empty() => return Ok(true),
            Ok(_) => {}
            Err(_) => return Ok(true),
        }
    }
    Ok(false)
}

#[cfg(test)]
mod tests {
    use orexis::snapshots::namespaces;

    use super::*;

    #[test]
    fn the_key_is_what_the_select_joins_two_subjects_on() {
        let store = Store::new(namespaces()).unwrap();
        let text = "PREFIX courier: <http://example.org/orexis/courier#>
        SELECT $this ?value WHERE { $this a courier:Van ; courier:x ?x ; courier:y ?y .
            ?value a courier:Van ; courier:x ?x ; courier:y ?y . FILTER(?value != $this) }";
        let found: Vec<String> = key(&store, text).into_iter().collect();
        assert_eq!(
            found,
            [
                "http://example.org/orexis/courier#x",
                "http://example.org/orexis/courier#y"
            ]
        );
        assert!(
            key(&store, "SELECT nonsense").is_empty(),
            "a text that will not parse joins nothing"
        );
    }
}
