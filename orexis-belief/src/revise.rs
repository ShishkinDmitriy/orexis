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

use oxigraph::model::{NamedNode, Triple};
use regex::Regex;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::instant;
use orexis::hash::{forms, hash_named_graph};
use orexis::ontology::{BELIEF, DERIVED};
use orexis::store::{Store, Within, value};

use crate::held::{holds, push_unique};
use crate::ontology::{DERIVED_FROM, REVISION_GRAPH, RULES_GRAPH, SETTLED, node, revision_graph};

/// Rule executions one call may spend, unless the caller says otherwise.
pub const BUDGET: usize = 64;

const SPARQL_RULE: &str = "http://www.w3.org/ns/shacl#SPARQLRule";

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

/// What one call of `revise` did: the rule executions it spent, and whether the rules settled — false only where the
/// revision graph's row now says `belief:settled false`, which the next call continues.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Concluded {
    pub spent: usize,
    pub settled: bool,
}

/// Conclude what the rules say follows from `source` beside `read` into its revision graph, classified `kind` beside
/// `belief:RevisionGraph`, layer by layer towards a fixpoint, spending at most `budget` rule executions. A source
/// whose row says its rules did not settle is CONTINUED from what is held; any other has what was concluded of it
/// before forgotten first. Where nothing is concluded there is no graph and no row; where something is and there is
/// no catalogue to describe it in, the call is refused.
pub fn revise(store: &Store, source: &str, read: &[String], budget: usize, kind: &str) -> Result<Concluded, Error> {
    let into = revision_graph(source);
    let cat = store.catalogue()?;
    let continuing = match &cat {
        Some(cat) => unsettled(store, cat, &into)?,
        None => false,
    };
    /// WHAT WAS CONCLUDED BEFORE, the revision graph's metadata left out.
    const HELD_Q: &str = "PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX orexis: <http://example.org/orexis#>
    CONSTRUCT { ?s ?p ?o }
    WHERE { GRAPH $into { ?s ?p ?o FILTER NOT EXISTS { ?s a orexis:Graph } FILTER NOT EXISTS { ?s a dcterms:PeriodOfTime } } }";
    let held = if continuing {
        store.construct(&bind(HELD_Q, &[("into", Value::iri(into.clone()))])?, &[])?
    } else {
        store.forget_graph(&into, Some(BELIEF))?;
        Vec::new()
    };
    let layers = layers(store)?;
    if layers.is_empty() {
        return Ok(Concluded {
            spent: 0,
            settled: !continuing,
        });
    }
    let mut graphs: Vec<&str> = Vec::new();
    for g in read.iter().map(String::as_str).chain([source, into.as_str()]) {
        push_unique(&mut graphs, g);
    }
    let mut evaluation = Evaluation {
        store,
        source,
        base: graphs.iter().copied().filter(|g| *g != into).collect(),
        target: node(&into)?,
        graphs,
        held,
        spent: 0,
        budget,
    };
    let mut settled = true;
    for (layer, orders) in &layers {
        //  ONE ITERATION OVER THE RUN-ONCE RULES FIRST, then the iterating rules while an iteration concludes.
        let pick = |once: bool| -> Vec<Vec<&Inference>> {
            orders
                .iter()
                .map(|(_, rules)| rules.iter().filter(|r| r.once == once).collect())
                .collect()
        };
        settled = evaluation.iterate(&pick(true))?.is_some();
        while settled {
            match evaluation.iterate(&pick(false))? {
                Some(0) => break,
                Some(_) => {}
                None => settled = false,
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
    let Evaluation { held, spent, .. } = evaluation;
    if held.is_empty() {
        return Ok(Concluded { spent, settled: true });
    }
    let cat = cat.ok_or_else(|| Error::Catalogue(format!("no catalogue to describe the revisions of {source} in")))?;
    describe(store, &cat, source, &into, settled, continuing, kind)?;
    hash_named_graph(store, &into, None)?;
    log::debug!(
        "{} revision(s) of {source} after {spent} execution(s){}",
        held.len(),
        if settled { "" } else { ", not settled" }
    );
    Ok(Concluded { spent, settled })
}

/// THE EVALUATION GRAPH of one call and what it has spent: the graphs every rule reads, the base graph among them
/// — all but the revision graph — the revision graph written into, and what is concluded in it so far.
struct Evaluation<'a> {
    store: &'a Store,
    source: &'a str,
    graphs: Vec<&'a str>,
    base: Vec<&'a str>,
    target: NamedNode,
    held: Vec<Triple>,
    spent: usize,
    budget: usize,
}

impl Evaluation<'_> {
    /// One iteration over `orders`, each order's rules asked of one state before any conclusion is written: how
    /// many facts it concluded, or None where the budget was spent before an order was begun.
    fn iterate(&mut self, orders: &[Vec<&Inference>]) -> Result<Option<usize>, Error> {
        let mut concluded = 0;
        for due in orders.iter().filter(|due| !due.is_empty()) {
            if self.spent >= self.budget {
                return Ok(None);
            }
            let mut added = Vec::new();
            for rule in due {
                self.spent += 1;
                match self.store.construct(&rule.construct, &self.graphs) {
                    Ok(made) => added.extend(made),
                    Err(e) => log::error!("a rule would not run over {}: {e}", self.source),
                }
            }
            let fresh = novel(&self.held, inferred(self.store, added, &self.base)?);
            if !fresh.is_empty() {
                let target = &self.target;
                self.store
                    .add(fresh.iter().map(|t| t.clone().in_graph(target.clone())))?;
                concluded += fresh.len();
                self.held.extend(fresh);
            }
        }
        Ok(Some(concluded))
    }
}

/// Whether `graph`'s row says its rules did not settle; no row is settled.
fn unsettled(store: &Store, cat: &str, graph: &str) -> Result<bool, Error> {
    /// WHETHER A REVISION GRAPH'S RULES DID NOT SETTLE, off its row.
    const UNSETTLED_Q: &str = "ASK { GRAPH $cat { $graph $settled false } }";
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
fn inferred(store: &Store, added: Vec<Triple>, base: &[&str]) -> Result<Vec<Triple>, Error> {
    let mut out = Vec::new();
    'added: for t in added {
        for g in base {
            if holds(store, &t, g)? {
                continue 'added;
            }
        }
        out.push(t);
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
    /// A CUSTOM RULE PROCESSOR named anywhere in a rules graph: an instruction this engine cannot follow.
    const PROCESSOR_Q: &str =
        "PREFIX sh: <http://www.w3.org/ns/shacl#> SELECT ?x ?processor WHERE { ?x sh:ruleProcessor ?processor }";
    /// WHAT A RULE'S `sh:prefixes` DECLARE, as SHACL-SPARQL spells it.
    const DECLARED_Q: &str = "PREFIX sh: <http://www.w3.org/ns/shacl#>
    SELECT ?rule ?prefix ?namespace WHERE {
      ?rule sh:prefixes ?ontology . ?ontology sh:declare ?d . ?d sh:prefix ?prefix ; sh:namespace ?namespace }";
    /// THE DEFAULT RULE SET of every rules graph: every active rule of any kind, with where the draft places it, its
    /// construct, and whether a shape links it, so that what cannot be run is reported. No transition is of it.
    const RULES_Q: &str = "PREFIX belief: <http://example.org/orexis/belief#>
    PREFIX sh: <http://www.w3.org/ns/shacl#>
    SELECT ?rule ?type ?construct ?layer ?order ?once ?shape ?condition ?expects WHERE {
      ?rule a ?type . FILTER(?type IN (sh:SPARQLRule, sh:TripleRule, sh:Rule))
      OPTIONAL { ?rule sh:construct ?construct }
      OPTIONAL { ?rule sh:layer ?layer } OPTIONAL { ?rule sh:order ?order }
      OPTIONAL { ?rule sh:runOnce ?once }
      OPTIONAL { ?shape sh:rule ?rule }
      OPTIONAL { ?rule sh:condition ?condition } OPTIONAL { ?rule sh:expectedPredicate ?expects }
      FILTER NOT EXISTS { ?rule sh:deactivated true }
      FILTER NOT EXISTS { ?rule a belief:Transition } }";
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
        push_unique(&mut read, g);
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
        let construct = prefixed(&construct, declared.get(&rule).unwrap_or(&empty));
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
/// itself.
fn prefixed(text: &str, declared: &BTreeMap<String, String>) -> String {
    let own: BTreeSet<String> = PREFIX_LINE
        .captures_iter(text)
        .map(|c| c.get(1).map(|m| m.as_str().to_string()).unwrap_or_default())
        .collect();
    let mut lines = Vec::new();
    for (label, namespace) in declared {
        if own.contains(label) {
            continue;
        }
        lines.push(format!("PREFIX {label}: <{namespace}>"));
    }
    lines.push(text.to_string());
    lines.join("\n")
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
    /// THE REVISION GRAPH'S ROW beside its entry: derived from its source, which the graph says of itself too, and
    /// whether its rules settled.
    const DESCRIBED_Q: &str = "GRAPH $cat { $into $derived $source ; $settled $value . }
    GRAPH $into { $into $derived $source . }";
    /// WHOSE THE SOURCE IS AND WHEN IT HOLDS, off its row: the revisions are the same.
    const SOURCE_Q: &str = "PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX orexis: <http://example.org/orexis#>
    SELECT ?owner ?start ?end WHERE {
      GRAPH $source { OPTIONAL { $source orexis:ownedBy ?owner }
                      OPTIONAL { $source dcterms:temporal ?p .
                                 OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } } } }
    LIMIT 1";
    if continuing {
        return say_settled(store, cat, into, settled);
    }
    let rows = store.rows(&bind(SOURCE_Q, &[("source", Value::iri(source))])?, &[])?;
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
    let described = bind(
        DESCRIBED_Q,
        &[
            ("cat", node(cat)?.into()),
            ("into", node(into)?.into()),
            ("source", node(source)?.into()),
            ("derived", Value::iri(DERIVED_FROM)),
            ("settled", Value::iri(SETTLED)),
            ("value", Value::Bool(settled)),
        ],
    )?;
    store.update(&format!(
        "PREFIX sh: <http://www.w3.org/ns/shacl#> INSERT DATA {{\n  {entry}\n  {described} }}"
    ))
}

/// Say on `graph`'s row whether its rules — or its arrival — are done, replacing what it said.
pub(crate) fn say_settled(store: &Store, cat: &str, graph: &str, settled: bool) -> Result<(), Error> {
    /// WHETHER A REVISION GRAPH'S RULES SETTLED, said again on its row.
    const SAY_SETTLED_U: &str = "
    DELETE { GRAPH $cat { $graph $settled ?was } }
    INSERT { GRAPH $cat { $graph $settled $value } }
    WHERE  { GRAPH $cat { $graph $settled ?was } }";
    store.update(&bind(
        SAY_SETTLED_U,
        &[
            ("cat", node(cat)?.into()),
            ("graph", node(graph)?.into()),
            ("settled", Value::iri(SETTLED)),
            ("value", Value::Bool(settled)),
        ],
    )?)
}

#[cfg(test)]
mod tests {
    //! `revise`, one case per file, held to its diff (`agent/belief/tests/test_revise.py`).

    use std::path::PathBuf;

    use orexis::ontology::RECORD;
    use orexis::snapshots;

    use super::*;

    const SENSED: &str = "http://example.org/test#sensed";

    fn cases() -> PathBuf {
        snapshots::tree().join("orexis-belief/tests/revise")
    }

    fn case(name: &str) -> Store {
        snapshots::stand_in(&cases().join(format!("{name}.trig")))
    }

    fn known(store: &Store) -> Vec<String> {
        store.graphs_of(&[BELIEF, RECORD], &Within::default()).unwrap()
    }

    fn concluded(store: &Store) -> Vec<(String, String, String)> {
        const CONCLUDED_Q: &str = "SELECT ?s ?p ?o WHERE { GRAPH $g { ?s ?p ?o } }";
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
                    "PREFIX sh: <http://www.w3.org/ns/shacl#> SELECT ?v WHERE {{ GRAPH ?c {{ <{}> <{SETTLED}> ?v }} }}",
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
        assert!(revise(&store, SENSED, &read, BUDGET, BELIEF).unwrap().spent > 0);
        assert!(!concluded(&store).is_empty());
        store
            .update(&format!(
                "PREFIX : <http://example.org/test#>
                 PREFIX sh: <http://www.w3.org/ns/shacl#>
                 DELETE {{ GRAPH <{SENSED}> {{ ?o :reads ?v }} }} INSERT {{ GRAPH <{SENSED}> \
                 {{ ?o :reads 0.2 }} }} WHERE {{ GRAPH <{SENSED}> {{ ?o \
                 :reads ?v }} }}"
            ))
            .unwrap();
        assert!(revise(&store, SENSED, &read, BUDGET, BELIEF).unwrap().spent > 0);
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
                r#"PREFIX : <http://example.org/test#>
  PREFIX sh: <http://www.w3.org/ns/shacl#>
  INSERT DATA { GRAPH :rules {
  :restless a sh:RuleSet ;
    sh:hasRule [ a sh:SPARQLRule ;
      sh:construct "PREFIX : <http://example.org/test#> CONSTRUCT { ?s :token ?u } WHERE { ?s a :Pot BIND(STRUUID() AS ?u) }" ] } }"#,
            )
            .unwrap();
        assert_eq!(revise(&store, SENSED, &known(&store), 12, BELIEF).unwrap().spent, 12);
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
        assert_eq!(revise(&store, SENSED, &read, 2, BELIEF).unwrap().spent, 2);
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
                r#"PREFIX : <http://example.org/test#>
  PREFIX sh: <http://www.w3.org/ns/shacl#>
  INSERT DATA { GRAPH :rules {
  :triple a sh:TripleRule .
  :shape a sh:NodeShape ;
    sh:rule :per_focus .
  :per_focus a sh:SPARQLRule ;
    sh:construct "CONSTRUCT { <http://example.org/test#zz> a <http://example.org/test#Seen> } WHERE { }" } }"#,
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
    fn a_rule_stating_a_condition_this_engine_cannot_honour_concludes_beside_the_others() {
        let store = case("a_reading_below_its_range_is_concluded_below");
        store
            .update(
                r#"PREFIX : <http://example.org/test#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
INSERT DATA { GRAPH :rules {
  :rules sh:ruleProcessor :somebody .
  :conditioned a sh:SPARQLRule ;
    sh:construct "CONSTRUCT { <http://example.org/test#zz> <http://example.org/test#noted> true } WHERE { }" ;
    sh:condition :some_shape ; sh:expectedPredicate :reads . } }"#,
            )
            .unwrap();
        revise(&store, SENSED, &known(&store), BUDGET, BELIEF).unwrap();
        let said: BTreeSet<String> = concluded(&store)
            .into_iter()
            .map(|(_, p, _)| p.rsplit('#').next().unwrap().to_string())
            .collect();
        assert!(said.contains("side") && said.contains("noted"), "{said:?}");
    }

    #[test]
    fn a_name_that_would_break_out_of_its_text_is_refused_before_anything_is_written() {
        let store = Store::new().unwrap();
        let cat = "urn:test:cat";
        say_settled(&store, cat, "urn:test:g", true).unwrap();
        let smuggled = "urn:test:g> <urn:test:p> <urn:test:o";
        assert!(matches!(
            say_settled(&store, cat, smuggled, true),
            Err(Error::Evaluation(_))
        ));
        assert!(
            store
                .rows("SELECT * WHERE { GRAPH ?g { ?s ?p ?o } }", &[])
                .unwrap()
                .is_empty(),
            "nothing was written"
        );
    }
}
