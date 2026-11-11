//! THE FOOTPRINT of a text — what it reads and what it writes — read off the text itself, as
//! `agent/planning/footprint.py` reads it, here off the parsed algebra rather than rdflib's.
//!
//! Ported so far: what the laying of the grounds asks of it — `changeable`, the patterns a search can change, and
//! `read_by_transitions`, what a transition's WHERE reads — and what `scope_actions` asks, `atoms_of`, each action's
//! fillings as predicates on keys, and `stored_edges`, the derivations' (`atoms`). **ANYTHING UNREADABLE READS AS ANYTHING** (`None`): a
//! text that will not parse, a template whose predicate is a variable nothing bounds. Over-approximation is safe
//! wherever these sets are used and under-approximation is not.
//!
//! **ONE READING DIFFERS, AND NO SHIPPED TEXT MEETS IT.** This engine's parser translates a sequence or an inverse
//! of plain predicates into triples, as SPARQL's algebra says, where rdflib keeps the path: so `?x :p/a :C` reads
//! the class `:C` here and every type, `rdf:type`, there. A path under `*`, `+` or `?` stays a path in both.

use std::collections::{BTreeMap, BTreeSet};
use std::sync::LazyLock;

use oxigraph::model::vocab::{rdf, xsd};
use oxigraph::model::{Literal, Term};
use oxsdatatypes::DateTime;
use regex::Regex;
use spargebra::algebra::{Expression, GraphPattern, PropertyPathExpression};
use spargebra::term::{GroundTerm, GroundTermPattern, NamedNodePattern, TermPattern, TriplePattern, Variable};

use orexis::Error;
use orexis::ontology::{ACTION, SELF};
use orexis::store::{Store, Within, iri, value};
use orexis_belief::transition::{Parts, parts, transitions};

/// A pattern of triple a writer can write: its predicate, and its object where a template fixes one — an IRI or a
/// literal — `None` where anything stands there.
#[derive(Clone, Debug, PartialEq)]
pub struct Pattern {
    pub predicate: String,
    pub object: Option<Term>,
}

impl Pattern {
    /// The object as rdflib's `n3()` spells it, which the digest a cut is remembered by is taken over.
    pub fn spelled(&self) -> Option<String> {
        self.object.as_ref().map(n3)
    }
}

/// The tokens a rule text takes, each replaced with something that PARSES: nothing is run, so the values are
/// never right, only well-formed — in the Python kernel's order, a substring at a time.
const PARSE_TOKENS: &[(&str, &str)] = &[
    ("$given", ""),
    ("$derived", "<urn:parse:derived>"),
    ("$evidence", "<urn:parse:evidence>"),
    ("$wants", "(<urn:parse:want> <urn:parse:about>)"),
    ("$properties", "<urn:parse:property>"),
    ("$litres", "1.0"),
    ("$this", "?this"),
];

static INTO: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\$into\([^)]*\)").expect("a valid pattern"));
static TOKEN: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\$([A-Za-z_][A-Za-z0-9_]*)\b").expect("a valid pattern"));
/// THE SELF IS NO FACT OF THE WORLD: `?me a orexis:Self` is read as absent, `?me` the free variable the agent
/// always was here. Python's pattern ends on a lookahead for `}`, which this engine's regex lacks, so the brace
/// is matched and put back.
static SELF_ANCHOR: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(&format!(
        r"(\?\w+)\s+(?:a|rdf:type)\s+(?:orexis:Self|<{}>)\s*(;|\.|\}})",
        regex::escape(SELF)
    ))
    .expect("a valid pattern")
});

/// The text with every `$token` made parseable and the self's anchor read as absent.
///
/// A TOKEN LEFT IS A VARIABLE OF ITS OWN, `?token__name`, where Python makes it `?name`: SPARQL spells one variable
/// `$tank` and `?tank`, so an effect's `BIND($tank AS ?tank)` binds a variable already in scope, which this
/// engine's parser refuses and rdflib's lets pass. What a text reads and writes does not depend on a variable's
/// name.
pub fn parseable(text: &str) -> String {
    let mut text = INTO.replace_all(text, "<urn:parse:into>").into_owned();
    for (token, stand_in) in PARSE_TOKENS {
        text = text.replace(token, stand_in);
    }
    let text = SELF_ANCHOR.replace_all(&text, |caps: &regex::Captures<'_>| match &caps[2] {
        ";" => caps[1].to_string(),
        "}" => "}".to_string(),
        _ => String::new(),
    });
    as_variables(&text)
}

/// Every `$token` as a variable of its own.
fn as_variables(text: &str) -> String {
    TOKEN.replace_all(text, "?token__${1}").into_owned()
}

/// A transition's or an effect's update as the runner reads it, made parseable — `None` where the runner refuses
/// it, its tokens read as variables, or the parseable text will not parse, which is anything.
pub(crate) fn read(store: &Store, text: &str) -> Option<Parts> {
    parts(store, &as_variables(text)).ok()?;
    parts(store, &parseable(text)).ok()
}

// --- what a transition reads -----------------------------------------------------------------------------------

/// Every predicate — and every class a type pattern names — some transition's WHERE reads: what a ground laid
/// runs them over. `None`, anything, where a transition cannot be read.
pub fn read_by_transitions(store: &Store) -> Result<Option<BTreeSet<String>>, Error> {
    let mut out = BTreeSet::new();
    for order in transitions(store)? {
        for rule in order {
            let Some(text) = &rule.update else { continue };
            let Some(parts) = read(store, text) else {
                return Ok(None);
            };
            match reads_of(&parts.pattern) {
                Some(reads) => out.extend(reads),
                None => return Ok(None),
            }
        }
    }
    Ok(Some(out))
}

/// What a WHERE reads: every triple pattern under it, under its groups and its `EXISTS` filters alike, as its
/// predicate's IRIs — a type pattern whose class is an IRI as the CLASS. `None` where one will not read so.
pub fn reads_of(pattern: &GraphPattern) -> Option<BTreeSet<String>> {
    let mut out = BTreeSet::new();
    walk(pattern, &mut out).then_some(out)
}

fn walk(pattern: &GraphPattern, out: &mut BTreeSet<String>) -> bool {
    match pattern {
        GraphPattern::Bgp { patterns } => patterns.iter().all(|t| triple(t, out)),
        GraphPattern::Path { path, .. } => match path_iris(path) {
            Some(iris) => {
                out.extend(iris);
                true
            }
            None => false,
        },
        GraphPattern::Values { .. } => true,
        GraphPattern::Join { left, right }
        | GraphPattern::Union { left, right }
        | GraphPattern::Minus { left, right } => walk(left, out) && walk(right, out),
        GraphPattern::LeftJoin {
            left,
            right,
            expression,
        } => walk(left, out) && walk(right, out) && expression.as_ref().is_none_or(|e| exists(e, out)),
        GraphPattern::Filter { expr, inner } => exists(expr, out) && walk(inner, out),
        GraphPattern::Extend { inner, expression, .. } => walk(inner, out) && exists(expression, out),
        GraphPattern::Graph { inner, .. }
        | GraphPattern::OrderBy { inner, .. }
        | GraphPattern::Project { inner, .. }
        | GraphPattern::Distinct { inner }
        | GraphPattern::Reduced { inner }
        | GraphPattern::Slice { inner, .. }
        | GraphPattern::Group { inner, .. }
        | GraphPattern::Service { inner, .. } => walk(inner, out),
        #[allow(unreachable_patterns)]
        _ => false,
    }
}

fn triple(t: &TriplePattern, out: &mut BTreeSet<String>) -> bool {
    match (&t.predicate, &t.object) {
        (NamedNodePattern::NamedNode(p), TermPattern::NamedNode(class)) if p.as_ref() == rdf::TYPE => {
            out.insert(class.as_str().to_string());
            true
        }
        (NamedNodePattern::NamedNode(p), _) => {
            out.insert(p.as_str().to_string());
            true
        }
        (NamedNodePattern::Variable(_), _) => false,
    }
}

pub(crate) fn path_iris(path: &PropertyPathExpression) -> Option<BTreeSet<String>> {
    match path {
        PropertyPathExpression::NamedNode(n) => Some(BTreeSet::from([n.as_str().to_string()])),
        PropertyPathExpression::Reverse(p)
        | PropertyPathExpression::ZeroOrMore(p)
        | PropertyPathExpression::OneOrMore(p)
        | PropertyPathExpression::ZeroOrOne(p) => path_iris(p),
        PropertyPathExpression::Sequence(a, b) | PropertyPathExpression::Alternative(a, b) => {
            let mut out = path_iris(a)?;
            out.extend(path_iris(b)?);
            Some(out)
        }
        PropertyPathExpression::NegatedPropertySet(_) => None,
    }
}

/// What every `EXISTS` inside an expression reads.
fn exists(expression: &Expression, out: &mut BTreeSet<String>) -> bool {
    match expression {
        Expression::Exists(pattern) => walk(pattern, out),
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
        | Expression::Divide(a, b) => exists(a, out) && exists(b, out),
        Expression::UnaryPlus(a) | Expression::UnaryMinus(a) | Expression::Not(a) => exists(a, out),
        Expression::If(a, b, c) => exists(a, out) && exists(b, out) && exists(c, out),
        Expression::In(a, list) => exists(a, out) && list.iter().all(|e| exists(e, out)),
        Expression::Coalesce(list) | Expression::FunctionCall(_, list) => list.iter().all(|e| exists(e, out)),
        _ => true,
    }
}

// --- what a search can change ------------------------------------------------------------------------------------

/// ONE ROW PER RULE OF AN ACTION'S EFFECT, with the action's precondition on each.
const ACTIONS_Q: &str = "
SELECT ?action ?precondition ?update WHERE {
  ?action a orexis:Action .
  OPTIONAL { ?action planning:precondition ?precondition }
  OPTIONAL { ?action planning:effect/sh:rule ?r . ?r a belief:Transition ; belief:update ?update }
}";

/// What a search can change, as patterns, sorted as the Python kernel sorts them — one per triple of every template
/// of every writer: each effect of `actions` (every action's where `None`) and each transition. `None`, anything,
/// where a writer's templates cannot be read.
pub fn changeable(
    store: &Store,
    actions: Option<&BTreeSet<String>>,
    at: DateTime,
) -> Result<Option<Vec<Pattern>>, Error> {
    let mut texts: Vec<String> = Vec::new();
    for (action, updates) in effects(store, at)? {
        if actions.is_none_or(|a| a.contains(&action)) {
            texts.extend(updates);
        }
    }
    for order in transitions(store)? {
        for rule in order {
            texts.extend(rule.update);
        }
    }
    let mut out: BTreeMap<(String, Option<String>), Pattern> = BTreeMap::new();
    for text in &texts {
        let Some(parts) = read(store, text) else {
            return Ok(None);
        };
        let Some(found) = template_patterns(&parts) else {
            return Ok(None);
        };
        for pattern in found {
            out.entry((pattern.predicate.clone(), pattern.spelled()))
                .or_insert(pattern);
        }
    }
    Ok(Some(sorted(out.into_values())))
}

/// `patterns` once each, sorted by predicate and then the object's spelling, nothing first.
pub fn sorted(patterns: impl IntoIterator<Item = Pattern>) -> Vec<Pattern> {
    let mut out: BTreeMap<(String, String), Pattern> = BTreeMap::new();
    for pattern in patterns {
        out.entry((pattern.predicate.clone(), pattern.spelled().unwrap_or_default()))
            .or_insert(pattern);
    }
    out.into_values().collect()
}

/// Every action's effect as its update texts, in the order the actions were first met.
fn effects(store: &Store, at: DateTime) -> Result<Vec<(String, Vec<String>)>, Error> {
    let graphs = store.graphs_of(&[ACTION], &Within::at(at))?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let mut out: Vec<(String, Vec<String>)> = Vec::new();
    for row in store.rows(ACTIONS_Q, &graphs)? {
        let Some(action) = iri(&row, "action") else { continue };
        let at = match out.iter().position(|(a, _)| *a == action) {
            Some(at) => at,
            None => {
                out.push((action, Vec::new()));
                out.len() - 1
            }
        };
        out[at].1.extend(value(&row, "update"));
    }
    Ok(out)
}

/// The patterns one update's templates write, its delete templates and its insert templates — `None` where a
/// predicate is a variable that no `VALUES` in its WHERE bounds to IRIs.
fn template_patterns(parts: &Parts) -> Option<Vec<Pattern>> {
    let mut written: Vec<(&NamedNodePattern, Option<Term>)> = Vec::new();
    for q in &parts.delete {
        written.push((&q.predicate, ground_object(&q.object)));
    }
    for q in &parts.insert {
        written.push((&q.predicate, object(&q.object)));
    }
    let mut bounded: Option<BTreeMap<Variable, Option<BTreeSet<String>>>> = None;
    let mut out = Vec::new();
    for (predicate, object) in written {
        match predicate {
            NamedNodePattern::NamedNode(p) => out.push(Pattern {
                predicate: p.as_str().to_string(),
                object,
            }),
            NamedNodePattern::Variable(v) => {
                let values = bounded.get_or_insert_with(|| values_in(&parts.pattern));
                let iris = values.get(v).cloned().flatten().filter(|i| !i.is_empty())?;
                out.extend(iris.into_iter().map(|p| Pattern {
                    predicate: p,
                    object: object.clone(),
                }));
            }
        }
    }
    Some(out)
}

fn object(term: &TermPattern) -> Option<Term> {
    match term {
        TermPattern::NamedNode(n) => Some(n.clone().into()),
        TermPattern::Literal(l) => Some(l.clone().into()),
        _ => None,
    }
}

fn ground_object(term: &GroundTermPattern) -> Option<Term> {
    match term {
        GroundTermPattern::NamedNode(n) => Some(n.clone().into()),
        GroundTermPattern::Literal(l) => Some(l.clone().into()),
        _ => None,
    }
}

/// Every variable a `VALUES` block under `pattern` binds, to the IRIs it binds it to — `None` where a row leaves
/// it `UNDEF` or binds it to something that is no IRI. Two blocks binding one variable are unioned.
pub(crate) fn values_in(pattern: &GraphPattern) -> BTreeMap<Variable, Option<BTreeSet<String>>> {
    let mut found = BTreeMap::new();
    collect_values(pattern, &mut found);
    found
}

fn collect_values(pattern: &GraphPattern, found: &mut BTreeMap<Variable, Option<BTreeSet<String>>>) {
    match pattern {
        GraphPattern::Values { variables, bindings } => {
            for row in bindings {
                for (variable, term) in variables.iter().zip(row) {
                    let held = found.entry(variable.clone()).or_insert_with(|| Some(BTreeSet::new()));
                    match (held.as_mut(), term) {
                        (None, _) => {}
                        (Some(iris), Some(GroundTerm::NamedNode(n))) => {
                            iris.insert(n.as_str().to_string());
                        }
                        (Some(_), _) => *held = None,
                    }
                }
            }
        }
        GraphPattern::Join { left, right }
        | GraphPattern::Union { left, right }
        | GraphPattern::Minus { left, right }
        | GraphPattern::LeftJoin { left, right, .. } => {
            collect_values(left, found);
            collect_values(right, found);
        }
        GraphPattern::Graph { inner, .. }
        | GraphPattern::Filter { inner, .. }
        | GraphPattern::Extend { inner, .. }
        | GraphPattern::OrderBy { inner, .. }
        | GraphPattern::Project { inner, .. }
        | GraphPattern::Distinct { inner }
        | GraphPattern::Reduced { inner }
        | GraphPattern::Slice { inner, .. }
        | GraphPattern::Group { inner, .. }
        | GraphPattern::Service { inner, .. } => collect_values(inner, found),
        _ => {}
    }
}

/// A term as rdflib's `n3()` spells it: an IRI in angle brackets, a literal quoted, with its language or its
/// datatype — a plain string bare.
pub fn n3(term: &Term) -> String {
    match term {
        Term::NamedNode(n) => format!("<{}>", n.as_str()),
        Term::Literal(l) => literal_n3(l),
        other => other.to_string(),
    }
}

pub(crate) fn literal_n3(literal: &Literal) -> String {
    let v = literal.value();
    let encoded = if v.contains('\n') {
        let mut e = v.replace('\\', "\\\\");
        if v.contains("\"\"\"") {
            e = e.replace("\"\"\"", "\\\"\\\"\\\"");
        }
        let chars: Vec<char> = e.chars().collect();
        if chars.len() >= 2 && chars[chars.len() - 1] == '"' && chars[chars.len() - 2] != '\\' {
            e.pop();
            e.push_str("\\\"");
        }
        format!("\"\"\"{}\"\"\"", e.replace('\r', "\\r"))
    } else {
        format!(
            "\"{}\"",
            v.replace('\n', "\\n")
                .replace('\\', "\\\\")
                .replace('"', "\\\"")
                .replace('\r', "\\r")
        )
    };
    if let Some(language) = literal.language() {
        format!("{encoded}@{language}")
    } else if literal.datatype() != xsd::STRING {
        format!("{encoded}^^<{}>", literal.datatype().as_str())
    } else {
        encoded
    }
}

mod atoms;
mod patterns;
mod shapes;

pub use atoms::{Atom, Filling, Side, actions_of, atoms_of, spelled, stored_edges, written};
pub use shapes::{reads_of_select, reads_of_shape, terms_of_shape};

#[cfg(test)]
mod tests {
    //! The footprint's reading of a text, held to what `test_footprint.py` holds the Python reading to — the parts
    //! the laying of the grounds asks.

    use oxigraph::model::{Literal, NamedNode};
    use spargebra::{Query, SparqlParser};

    use orexis::snapshots;

    use super::*;
    use crate::terms::RDF_TYPE;

    fn reads(text: &str) -> Option<BTreeSet<String>> {
        let Query::Select { pattern, .. } = SparqlParser::new().parse_query(text).expect("a query") else {
            panic!("a select")
        };
        reads_of(&pattern)
    }

    fn set(iris: &[&str]) -> Option<BTreeSet<String>> {
        Some(iris.iter().map(|i| i.to_string()).collect())
    }

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
}
