//! `revise`: what the rules the store holds conclude of one graph — its revisions — written beside it, within a
//! budget, as `agent/belief/revise.py` concludes them.
//!
//! **THE RULES ARE SHACL 1.2 INFERENCE RULES', RUN AS THE DRAFT SAYS.** Every graph the catalogue types
//! `sh:RulesGraph` is a rules graph, and what is run is its DEFAULT RULE SET: every active `sh:SPARQLRule` with a
//! `sh:construct`, global, and no `belief:Transition`, which changes a state and is `trigger`'s.
//!
//! **LAYER BY LAYER, TO A FIXPOINT, OVER THE EVALUATION GRAPH.** The evaluation graph is what the caller hands as
//! standing beside the source, the source, and what has been concluded of it so far. Within a layer one iteration
//! runs every `sh:runOnce` rule first, then the iterating rules again while an iteration concludes something new;
//! rules of ONE order are asked over the same state before any conclusion is written. What is inferred is what the
//! base graph does not hold, and a fact already concluded — a blank node by its content — is not written twice.
//! What this engine cannot honour is said in the log and the rest of the rule set runs.
//!
//! **A CEILING ON COMPUTE IS STATED IN THE UNIT THE WORK SPENDS**: one construct run is one rule execution. A group
//! is run whole or not at all; a budget spent before a layer settles leaves what was concluded standing, the
//! revision graph's row saying `belief:settled false`, and the next call continues from what is held.
//!
//! **CONCLUDE, THEN CLASSIFY.** The revision graph's row says the kind the caller hands beside
//! `belief:RevisionGraph`, derived from the source, the source's owner's, over the source's period.

use std::collections::{BTreeMap, BTreeSet};
use std::sync::LazyLock;

use oxigraph::model::{GraphNameRef, NamedNode, Triple};
use regex::Regex;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::instant;
use orexis::hash::{forms, hash_named_graph};
use orexis::ontology::{BELIEF, DERIVED};
use orexis::store::{Store, Within, value};

use crate::ontology::{DERIVED_FROM, REVISION_GRAPH, RULES_GRAPH, SETTLED, revision_graph};

/// Rule executions one call may spend, unless the caller says otherwise.
pub const BUDGET: usize = 64;

const SPARQL_RULE: &str = "http://www.w3.org/ns/shacl#SPARQLRule";

/// THE DEFAULT RULE SET of every rules graph: every active rule of any kind, with where the draft places it, its
/// construct, and whether a shape links it, so that what cannot be run is reported. No transition is of it.
const RULES_Q: &str = "
SELECT ?rule ?type ?construct ?layer ?order ?once ?shape ?condition ?expects WHERE {
  ?rule a ?type . FILTER(?type IN (sh:SPARQLRule, sh:TripleRule, sh:Rule))
  OPTIONAL { ?rule sh:construct ?construct }
  OPTIONAL { ?rule sh:layer ?layer } OPTIONAL { ?rule sh:order ?order }
  OPTIONAL { ?rule sh:runOnce ?once }
  OPTIONAL { ?shape sh:rule ?rule }
  OPTIONAL { ?rule sh:condition ?condition } OPTIONAL { ?rule sh:expectedPredicate ?expects }
  FILTER NOT EXISTS { ?rule sh:deactivated true }
  FILTER NOT EXISTS { ?rule a belief:Transition } }";

/// WHAT A RULE'S `sh:prefixes` DECLARE, as SHACL-SPARQL spells it.
const DECLARED_Q: &str = "
SELECT ?rule ?prefix ?namespace WHERE {
  ?rule sh:prefixes ?ontology . ?ontology sh:declare ?d . ?d sh:prefix ?prefix ; sh:namespace ?namespace }";

/// A CUSTOM RULE PROCESSOR named anywhere in a rules graph: an instruction this engine cannot follow.
const PROCESSOR_Q: &str = "SELECT ?x ?processor WHERE { ?x sh:ruleProcessor ?processor }";

/// WHOSE THE SOURCE IS AND WHEN IT HOLDS, off its row: the revisions are the same.
const SOURCE_Q: &str = "
SELECT ?owner ?start ?end WHERE {
  GRAPH $cat { OPTIONAL { $source orexis:ownedBy ?owner }
               OPTIONAL { $source dcterms:temporal ?p .
                          OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } } } }
LIMIT 1";

/// WHETHER A REVISION GRAPH'S RULES DID NOT SETTLE, off its row.
const UNSETTLED_Q: &str = "ASK { GRAPH $cat { $graph $settled false } }";

/// `PREFIX name: <iri>` at the head of a text, the empty name included.
static PREFIX_LINE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?im)^\s*PREFIX\s+([A-Za-z][\w.\-]*)?\s*:\s*<([^>]*)>").expect("a valid pattern"));

/// One rule of the default rule set, as the draft executes it.
#[derive(Clone, Debug)]
struct Inference {
    construct: String,
    once: bool,
}

/// The rules, layer by layer ascending, each layer's grouped by order ascending.
type Layers = Vec<(f64, Vec<(f64, Vec<Inference>)>)>;

/// Conclude what the rules say follows from `source` beside `read` into its revision graph, classified `kind` beside
/// `belief:RevisionGraph`, layer by layer towards a fixpoint, spending at most `budget` rule executions: what this
/// call spent. A source whose row says its rules did not settle is CONTINUED from what is held; any other has what
/// was concluded of it before forgotten first. Where nothing is concluded there is no graph and no row.
pub fn revise(store: &Store, source: &str, read: &[String], budget: usize, kind: &str) -> Result<usize, Error> {
    let into = revision_graph(source);
    let cat = store.catalogue()?.unwrap_or_default();
    let continuing = unsettled(store, &cat, &into)?;
    let mut held: Vec<Triple> = Vec::new();
    if continuing {
        held = store.triples(&into)?;
    } else {
        store.forget_graph(&into, Some(BELIEF))?;
    }
    let layers = layers(store)?;
    if layers.is_empty() {
        return Ok(0);
    }
    let mut evaluation: Vec<&str> = Vec::new();
    for g in read.iter().map(String::as_str).chain([source, into.as_str()]) {
        if !evaluation.contains(&g) {
            evaluation.push(g);
        }
    }
    let base: Vec<NamedNode> = evaluation
        .iter()
        .filter(|g| **g != into)
        .map(|g| node(g))
        .collect::<Result<_, _>>()?;
    let target = node(&into)?;
    let mut spent = 0;
    let mut settled = true;
    for (layer, orders) in &layers {
        //  ONE ITERATION OVER THE RUN-ONCE RULES FIRST, then the iterating rules while new.
        let pick = |once: bool| -> Vec<Vec<&Inference>> {
            orders
                .iter()
                .map(|(_, rules)| rules.iter().filter(|r| r.once == once).collect())
                .collect()
        };
        let (once, iterating) = (pick(true), pick(false));
        let mut groups = &once;
        loop {
            let mut concluded = 0;
            for due in groups {
                if due.is_empty() {
                    continue;
                }
                if spent >= budget {
                    settled = false;
                    break;
                }
                //  ONE ORDER, ONE STATE: every rule of the order is asked before any conclusion is written.
                let mut added = Vec::new();
                for rule in due {
                    spent += 1;
                    match store.construct(&rule.construct, &evaluation) {
                        Ok(made) => added.extend(made),
                        Err(e) => log::error!("a rule would not run over {source}: {e}"),
                    }
                }
                let fresh = novel(&held, inferred(store, added, &base)?);
                if !fresh.is_empty() {
                    store.add(fresh.iter().map(|t| t.clone().in_graph(target.clone())))?;
                    concluded += fresh.len();
                    held.extend(fresh);
                }
            }
            if !settled {
                break;
            }
            if std::ptr::eq(groups, &once) || concluded > 0 {
                groups = &iterating;
            } else {
                break;
            }
        }
        if !settled {
            log::warn!(
                "the rules over {source} did not settle within {budget} execution(s) at layer {layer}; what they \
                 concluded stands, and the next pass continues"
            );
            break;
        }
    }
    if held.is_empty() {
        return Ok(spent);
    }
    describe(store, &cat, source, &into, settled, continuing, kind)?;
    hash_named_graph(store, &into, None)?;
    log::debug!(
        "{} revision(s) of {source} after {spent} execution(s){}",
        held.len(),
        if settled { "" } else { ", not settled" }
    );
    Ok(spent)
}

/// Whether `graph`'s row says its rules did not settle; no row is settled.
fn unsettled(store: &Store, cat: &str, graph: &str) -> Result<bool, Error> {
    if cat.is_empty() {
        return Ok(false);
    }
    store.ask(
        &bind(
            UNSETTLED_Q,
            &[
                ("cat", Value::iri(cat)),
                ("graph", Value::iri(graph)),
                ("settled", Value::iri(SETTLED)),
            ],
        )?,
        &[],
    )
}

/// The triples of `added` that say something `held` does not — by canonical form, in the universe of both, so a
/// blank node minted again with the content of one already held is the same fact.
fn novel(held: &[Triple], added: Vec<Triple>) -> Vec<Triple> {
    if added.is_empty() {
        return added;
    }
    let all: Vec<Triple> = held.iter().cloned().chain(added.iter().cloned()).collect();
    let shapes = forms(&all);
    let mut seen: BTreeSet<&String> = shapes[..held.len()].iter().collect();
    let mut out = Vec::new();
    for (triple, form) in added.into_iter().zip(&shapes[held.len()..]) {
        if seen.insert(form) {
            out.push(triple);
        }
    }
    out
}

/// The triples of `added` the base graph does not already hold — what the draft calls inferred.
fn inferred(store: &Store, added: Vec<Triple>, base: &[NamedNode]) -> Result<Vec<Triple>, Error> {
    let mut out = Vec::new();
    for t in added {
        let mut stated = false;
        for g in base {
            if store
                .engine()
                .quads_for_pattern(
                    Some(t.subject.as_ref()),
                    Some(t.predicate.as_ref()),
                    Some(t.object.as_ref()),
                    Some(GraphNameRef::NamedNode(g.as_ref())),
                )
                .next()
                .is_some()
            {
                stated = true;
                break;
            }
        }
        if !stated {
            out.push(t);
        }
    }
    Ok(out)
}

/// What one rule's query rows say of it.
#[derive(Default)]
struct About {
    types: BTreeSet<String>,
    shape: Option<String>,
    construct: Option<String>,
    layer: Option<String>,
    order: Option<String>,
    once: Option<String>,
    condition: bool,
    expects: bool,
}

/// The default rule set of every rules graph, as the draft executes it. A rule this engine cannot execute — not a
/// SPARQL rule, or linked to a shape — is the failure the draft says to report, logged and left out.
fn layers(store: &Store) -> Result<Layers, Error> {
    let rules_graphs = store.graphs_of(&[RULES_GRAPH], &Within::default())?;
    let rules: Vec<&str> = rules_graphs.iter().map(String::as_str).collect();
    for r in store.rows(PROCESSOR_Q, &rules)? {
        log::error!(
            "{} names a custom rule processor {}, which this engine cannot follow",
            value(&r, "x").unwrap_or_default(),
            value(&r, "processor").unwrap_or_default()
        );
    }
    let mut seen: BTreeMap<String, About> = BTreeMap::new();
    for r in store.rows(RULES_Q, &rules)? {
        let Some(rule) = value(&r, "rule") else { continue };
        let about = seen.entry(rule).or_default();
        about.types.extend(value(&r, "type"));
        about.shape = about.shape.take().or_else(|| value(&r, "shape"));
        about.construct = about.construct.take().or_else(|| value(&r, "construct"));
        about.layer = about.layer.take().or_else(|| value(&r, "layer"));
        about.order = about.order.take().or_else(|| value(&r, "order"));
        about.once = about.once.take().or_else(|| value(&r, "once"));
        about.condition |= r.contains_key("condition");
        about.expects |= r.contains_key("expects");
    }
    let mut read = rules_graphs.clone();
    for g in store.graphs_of(&[BELIEF], &Within::common())? {
        if !read.contains(&g) {
            read.push(g);
        }
    }
    let read: Vec<&str> = read.iter().map(String::as_str).collect();
    let mut declared: BTreeMap<String, BTreeMap<String, String>> = BTreeMap::new();
    for r in store.rows(DECLARED_Q, &read)? {
        if let (Some(rule), Some(prefix), Some(namespace)) =
            (value(&r, "rule"), value(&r, "prefix"), value(&r, "namespace"))
        {
            declared.entry(rule).or_default().insert(prefix, namespace);
        }
    }
    let mut found: Vec<(f64, f64, String, Inference)> = Vec::new();
    for (rule, about) in seen {
        if let Some(shape) = &about.shape {
            log::error!(
                "rule {rule} is a shape rule of {shape}, which this engine cannot execute: it runs per focus node and \
                 nothing here has one"
            );
            continue;
        }
        let construct = match &about.construct {
            Some(c) if about.types.contains(SPARQL_RULE) => c.clone(),
            _ => {
                let types: Vec<&str> = about.types.iter().map(|t| t.rsplit('#').next().unwrap_or(t)).collect();
                log::error!(
                    "rule {rule} is of a type this engine cannot execute ({})",
                    types.join(", ")
                );
                continue;
            }
        };
        if about.condition {
            log::error!(
                "rule {rule} states a sh:condition, which this engine cannot honour: a condition is a shape rule's, \
                 and this is a global rule"
            );
        }
        if about.expects {
            log::error!(
                "rule {rule} states a sh:expectedPredicate, which this engine cannot honour: derived value nodes are \
                 not computed here"
            );
        }
        let empty = BTreeMap::new();
        let Some(construct) = prefixed(store, &rule, &construct, declared.get(&rule).unwrap_or(&empty)) else {
            continue;
        };
        let figure = |f: &Option<String>| f.as_deref().and_then(|f| f.parse().ok()).unwrap_or(0.0);
        let once = about.once.as_deref().is_some_and(|o| o.eq_ignore_ascii_case("true"));
        found.push((
            figure(&about.layer),
            figure(&about.order),
            rule,
            Inference { construct, once },
        ));
    }
    found.sort_by(|a, b| a.0.total_cmp(&b.0).then(a.1.total_cmp(&b.1)).then(a.2.cmp(&b.2)));
    let mut out: Layers = Vec::new();
    for (layer, order, _, rule) in found {
        if out.last().is_none_or(|(l, _)| *l != layer) {
            out.push((layer, Vec::new()));
        }
        let orders = &mut out.last_mut().expect("a layer").1;
        if orders.last().is_none_or(|(o, _)| *o != order) {
            orders.push((order, Vec::new()));
        }
        orders.last_mut().expect("an order").1.push(rule);
    }
    Ok(out)
}

/// `text` with a `PREFIX` line at its head for each name its `sh:prefixes` declare and the text does not declare
/// itself; None, and the rule refused, where a declared name is one the store's dictionary spells differently.
fn prefixed(store: &Store, rule: &str, text: &str, declared: &BTreeMap<String, String>) -> Option<String> {
    let own: BTreeSet<String> = PREFIX_LINE
        .captures_iter(text)
        .map(|c| c.get(1).map(|m| m.as_str().to_string()).unwrap_or_default())
        .collect();
    let mut lines = Vec::new();
    for (label, namespace) in declared {
        if let Some(known) = store.namespaces().get(label)
            && known != namespace
        {
            log::error!(
                "rule {rule} declares {label}: as <{namespace}>, and the store spells that name <{known}>; refused"
            );
            return None;
        }
        if own.contains(label) {
            continue;
        }
        lines.push(format!("PREFIX {label}: <{namespace}>"));
    }
    if lines.is_empty() {
        return Some(text.to_string());
    }
    lines.push(text.to_string());
    Some(lines.join("\n"))
}

/// The revision graph's row: a revision and of `kind`, derived, from `source`, the source's owner's, for the
/// source's period, and whether its rules settled — the flag replaced where the row stands.
fn describe(
    store: &Store,
    cat: &str,
    source: &str,
    into: &str,
    settled: bool,
    continuing: bool,
    kind: &str,
) -> Result<(), Error> {
    if continuing {
        return say_settled(store, cat, into, settled);
    }
    let rows = store.rows(
        &bind(SOURCE_Q, &[("cat", Value::iri(cat)), ("source", Value::iri(source))])?,
        &[],
    )?;
    let row = rows.first();
    let field = |k: &str| row.and_then(|r| value(r, k));
    let when = |k: &str| field(k).and_then(|t| instant(&t).ok());
    let entry = store.entry(
        into,
        &[REVISION_GRAPH, kind],
        DERIVED,
        field("owner").as_deref(),
        when("start"),
        when("end"),
    )?;
    store.update(&format!(
        "INSERT DATA {{\n  {entry}\n  GRAPH <{cat}> {{ <{into}> <{DERIVED_FROM}> <{source}> ; <{SETTLED}> {settled} . }} }}"
    ))
}

/// Say on `graph`'s row whether its rules — or its arrival — are done, replacing what it said.
pub(crate) fn say_settled(store: &Store, cat: &str, graph: &str, settled: bool) -> Result<(), Error> {
    store.update(&format!(
        "DELETE {{ GRAPH <{cat}> {{ <{graph}> <{SETTLED}> ?was }} }}
INSERT {{ GRAPH <{cat}> {{ <{graph}> <{SETTLED}> {settled} }} }}
WHERE  {{ GRAPH <{cat}> {{ <{graph}> <{SETTLED}> ?was }} }}"
    ))
}

fn node(iri: &str) -> Result<NamedNode, Error> {
    NamedNode::new(iri).map_err(|e| Error::Evaluation(format!("no IRI: {iri}: {e}")))
}

#[cfg(test)]
mod tests {
    //! `revise`, one case per file, held to the diff the Python suite wrote (`agent/belief/tests/test_revise.py`).

    use std::path::PathBuf;

    use orexis::ontology::RECORD;
    use orexis::snapshots;

    use super::*;

    const SENSED: &str = "http://example.org/test#sensed";
    const CONCLUDED_Q: &str = "SELECT ?s ?p ?o WHERE { GRAPH $g { ?s ?p ?o } }";

    fn cases() -> PathBuf {
        snapshots::tree().join("belief/tests/revise")
    }

    fn case(name: &str) -> Store {
        snapshots::stand_in(&cases().join(format!("{name}.trig")))
    }

    fn known(store: &Store) -> Vec<String> {
        store.graphs_of(&[BELIEF, RECORD], &Within::default()).unwrap()
    }

    fn concluded(store: &Store) -> Vec<(String, String, String)> {
        store
            .rows(
                &bind(CONCLUDED_Q, &[("g", Value::iri(revision_graph(SENSED)))]).unwrap(),
                &[],
            )
            .unwrap()
            .iter()
            .map(|r| (value(r, "s").unwrap(), value(r, "p").unwrap(), value(r, "o").unwrap()))
            .collect()
    }

    fn settled(store: &Store) -> Option<String> {
        let found = store
            .rows(
                &format!(
                    "SELECT ?v WHERE {{ GRAPH ?c {{ <{}> <{SETTLED}> ?v }} }}",
                    revision_graph(SENSED)
                ),
                &[],
            )
            .unwrap();
        found.first().and_then(|r| value(r, "v"))
    }

    #[test]
    fn revise_concludes_what_the_patch_says() {
        for case in snapshots::cases_in(&cases()) {
            let store = snapshots::stand_in(&case);
            revise(&store, SENSED, &known(&store), BUDGET, BELIEF).unwrap();
            snapshots::held_to_diff(&case, &store, "revise");
        }
    }

    #[test]
    fn every_case_is_read_and_no_diff_is_orphaned() {
        snapshots::all_read(&cases(), 8);
    }

    #[test]
    fn a_rewritten_source_replaces_its_conclusions() {
        let store = case("a_reading_below_its_range_is_concluded_below");
        let read = known(&store);
        assert!(revise(&store, SENSED, &read, BUDGET, BELIEF).unwrap() > 0);
        assert!(!concluded(&store).is_empty());
        store
            .update(&format!(
                "DELETE {{ GRAPH <{SENSED}> {{ ?o <http://example.org/test#reads> ?v }} }} INSERT {{ GRAPH <{SENSED}> \
                 {{ ?o <http://example.org/test#reads> 0.2 }} }} WHERE {{ GRAPH <{SENSED}> {{ ?o \
                 <http://example.org/test#reads> ?v }} }}"
            ))
            .unwrap();
        assert!(revise(&store, SENSED, &read, BUDGET, BELIEF).unwrap() > 0);
        assert!(concluded(&store).is_empty());
        assert!(
            store
                .graphs_of(&[REVISION_GRAPH], &Within::default())
                .unwrap()
                .is_empty()
        );
    }

    #[test]
    fn a_rule_that_never_settles_spends_the_budget_and_is_said() {
        let store = case("a_reading_below_its_range_is_concluded_below");
        store
            .update(
                r#"INSERT DATA { GRAPH <http://example.org/test#rules> {
  <http://example.org/test#restless> a <http://www.w3.org/ns/shacl#RuleSet> ;
    <http://www.w3.org/ns/shacl#hasRule> [ a <http://www.w3.org/ns/shacl#SPARQLRule> ;
      <http://www.w3.org/ns/shacl#construct> "PREFIX : <http://example.org/test#> CONSTRUCT { ?s :token ?u } WHERE { ?s a :Pot BIND(STRUUID() AS ?u) }" ] } }"#,
            )
            .unwrap();
        assert_eq!(revise(&store, SENSED, &known(&store), 12, BELIEF).unwrap(), 12);
        let tokens = concluded(&store)
            .iter()
            .filter(|(_, p, _)| p.ends_with("token"))
            .count();
        assert!(0 < tokens && tokens <= 12, "{tokens}");
        assert_eq!(settled(&store).as_deref(), Some("false"));
    }

    #[test]
    fn a_cut_is_continued_from_what_is_held() {
        let whole = case("a_chain_settles_in_a_later_round");
        revise(&whole, SENSED, &known(&whole), BUDGET, BELIEF).unwrap();
        let expected: BTreeSet<_> = concluded(&whole).into_iter().collect();
        let store = case("a_chain_settles_in_a_later_round");
        let read = known(&store);
        assert_eq!(revise(&store, SENSED, &read, 2, BELIEF).unwrap(), 2);
        assert_eq!(settled(&store).as_deref(), Some("false"));
        revise(&store, SENSED, &read, 64, BELIEF).unwrap();
        assert_eq!(settled(&store).as_deref(), Some("true"));
        assert_eq!(concluded(&store).into_iter().collect::<BTreeSet<_>>(), expected);
    }

    #[test]
    fn a_rule_this_engine_cannot_execute_is_left_out_and_the_rest_run() {
        let store = case("a_reading_below_its_range_is_concluded_below");
        store
            .update(
                r#"INSERT DATA { GRAPH <http://example.org/test#rules> {
  <http://example.org/test#triple> a <http://www.w3.org/ns/shacl#TripleRule> .
  <http://example.org/test#shape> a <http://www.w3.org/ns/shacl#NodeShape> ;
    <http://www.w3.org/ns/shacl#rule> <http://example.org/test#per_focus> .
  <http://example.org/test#per_focus> a <http://www.w3.org/ns/shacl#SPARQLRule> ;
    <http://www.w3.org/ns/shacl#construct> "CONSTRUCT { <http://example.org/test#zz> a <http://example.org/test#Seen> } WHERE { }" } }"#,
            )
            .unwrap();
        revise(&store, SENSED, &known(&store), BUDGET, BELIEF).unwrap();
        let said = concluded(&store);
        assert!(said.iter().any(|(_, p, _)| p.ends_with("side")));
        assert!(
            !said.iter().any(|(_, _, o)| o.ends_with("Seen")),
            "the shape rule ran nothing"
        );
    }

    #[test]
    fn a_prefix_the_store_spells_differently_refuses_its_rule_and_the_others_conclude() {
        let store = case("a_reading_below_its_range_is_concluded_below");
        store
            .update(
                r#"PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
INSERT DATA { GRAPH <http://example.org/test#rules> {
  <http://example.org/test#rules> sh:ruleProcessor <http://example.org/test#somebody> .
  <http://example.org/test#conditioned> a sh:SPARQLRule ;
    sh:construct "CONSTRUCT { <http://example.org/test#zz> <http://example.org/test#noted> true } WHERE { }" ;
    sh:condition <http://example.org/test#some_shape> ; sh:expectedPredicate <http://example.org/test#reads> .
  <http://example.org/test#misspelt> a sh:SPARQLRule ;
    sh:construct "CONSTRUCT { <http://example.org/test#zz> orexis:wrong true } WHERE { }" ;
    sh:prefixes <http://example.org/test#other> .
  <http://example.org/test#other> sh:declare [ sh:prefix "orexis" ; sh:namespace "http://example.org/elsewhere#"^^xsd:anyURI ] } }"#,
            )
            .unwrap();
        revise(&store, SENSED, &known(&store), BUDGET, BELIEF).unwrap();
        let said: BTreeSet<String> = concluded(&store)
            .into_iter()
            .map(|(_, p, _)| p.rsplit('#').next().unwrap().to_string())
            .collect();
        assert!(
            said.contains("side") && said.contains("noted") && !said.contains("wrong"),
            "{said:?}"
        );
    }
}
