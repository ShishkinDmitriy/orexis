//! TAKING ONE CANDIDATE: the world it reaches, forked from the world it leaves with the action's effect applied,
//! and that world's own row, as `agent/planning/take.py` takes it — and the argument for every clause is that
//! module's docstring, which this follows.
//!
//! - **The child is forked from the ground holding at its landing** (#596): where that ground is not the one its
//!   parent stands in, the child is that ground with every step on the path replayed onto it, then this step's
//!   effect, and what the effect changed is said in `<child>.adds` and `<child>.retracts` before the replayed
//!   ground goes (#919).
//! - **A wait is a move though no effect runs** (#920): it lands where the next ground the search can tell apart
//!   begins, its world that ground with the path replayed.
//! - **An effect is a transition the agent causes, and belief's machine applies it**, `WITH` the fork and reading
//!   every graph of the world with the fork in its place. A step whose effect leaves the world as it found it is
//!   no move.
//! - **The child is named by the candidate's mint number**, read off the candidate's row (#486).
//!
//! **THE ROWS ARE READ OFF THE CATALOGUE'S INDEX**, a candidate's and a world's, and the world's row is written
//! as quads: the Python kernel binds each into a text per candidate, which here would be a parse per candidate.

use std::collections::HashSet;
use std::sync::LazyLock;

use oxigraph::model::vocab::xsd;
use oxigraph::model::{BlankNode, Literal, Quad, Term, Triple};
use oxsdatatypes::DateTime;
use regex::Regex;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::microseconds;
use orexis::hash::{digest_of, py_float_repr, py_round};
use orexis::ontology::{ACTION, BELIEF, DERIVED, END, HASH, SELF_GRAPH, START};
use orexis::store::{Store, Within, instant, iri, value};
use orexis_belief::transition::{Rule, run};

use crate::Memo;
use crate::admit::{local_of, possible};
use crate::memo::{Binding, Carried};
use crate::next_ground::next_ground;
use crate::ontology::{ADDS_GRAPH, BY, FILLS, FROM, GROUND_GRAPH, MINTED, POSSIBLE_GRAPH, RETRACTS_GRAPH, SPENT, WAIT};
use crate::terms::{RDF_TYPE, TEMPORAL};
use crate::world_at::{Asking, catalogue, lexical, named, world_at};

const PERIOD_OF_TIME: &str = "http://purl.org/dc/terms/PeriodOfTime";
const ARRIVED_BY: &str = "http://example.org/orexis#arrivedBy";
const WAS_DERIVED_FROM: &str = "http://www.w3.org/ns/prov#wasDerivedFrom";

/// THE ACTION'S TEXTS, off what the world states.
const RULE_Q: &str = "
SELECT ?rule ?lands ?costs WHERE {
  $rule a orexis:Action .
  OPTIONAL { $rule planning:landsAfter ?lands }
  OPTIONAL { $rule planning:costs ?costs }
  BIND($rule AS ?rule) } LIMIT 1";

/// ITS EFFECT'S RULES, by order — an absent order is 0, as SHACL says — and whether each is a transition.
const EFFECT_Q: &str = "
SELECT ?r ?order ?update ?transition WHERE {
  $rule planning:effect/sh:rule ?r .
  OPTIONAL { ?r sh:order ?o } OPTIONAL { ?r belief:update ?update }
  BIND(EXISTS { ?r a belief:Transition } AS ?transition)
  BIND(COALESCE(?o, 0) AS ?order) }
ORDER BY ?order";

/// WHOM THE SELF ACTS FOR, off the world graph — `$subject` in a rule text.
const ACTS_FOR_Q: &str = "SELECT ?for WHERE { ?me a orexis:Self ; orexis:actsFor ?for } LIMIT 1";

/// THE PATH TO A WORLD: every candidate taken from the ground down to the world itself, in mint order.
const PATH_Q: &str = "
SELECT ?c WHERE { GRAPH $cat { $world (planning:by/planning:from)* ?w . ?w planning:by ?c ; planning:minted ?m } }
ORDER BY ?m";

/// What the Python kernel's binder wraps as an IRI where it is handed a value's text.
static IRI: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^(https?://|urn:|mailto:|file:)\S*$").expect("a valid pattern"));

/// Fork the world `cand` reaches and write its row. False, and nothing made, where the candidate's effect changes
/// nothing in the world it leaves, or where it is a wait and nothing laid after its ground holds anything else.
/// `within` is what a world of this imaginarium is identified by.
pub fn take(
    store: &Store,
    cand: &str,
    within: Option<&std::collections::BTreeSet<String>>,
    memo: &mut Memo,
) -> Result<bool, Error> {
    let binding = binding(store, cand, memo)?;
    let child = format!("{}{}", possible(), binding.minted);
    let cost = figure(store, cand, memo, Text::Costs, "cost")?.unwrap_or(0.0);
    let waits = binding.action == WAIT;
    let (start, end) = if waits {
        match next_ground(store, &binding.from, memo)? {
            None => return Ok(false),
            Some(at) => (at, if binding.end > at { binding.end } else { at }),
        }
    } else {
        let (least, most) = landing(store, cand, memo)?;
        (shifted(binding.start, least)?, shifted(binding.end, most)?)
    };
    let lands_in = ground_at(store, start, memo)?;
    let stands_in = if grounds(store, memo)?.contains(&binding.from) {
        Some(binding.from.clone())
    } else {
        ground_at(store, binding.start, memo)?
    };
    let made = if waits {
        let ground = lands_in
            .clone()
            .ok_or_else(|| Error::Evaluation("a wait lands in no ground".into()))?;
        replayed(store, cand, &child, &ground, Some(&child), memo)?;
        changed(store, &child, &child, memo)?;
        true
    } else if lands_in.is_none() || lands_in == stands_in {
        apply(store, cand, &child, None, None, memo)?
    } else {
        let ground = lands_in.clone().expect("asked above");
        let base = replayed(store, cand, &child, &ground, None, memo)?;
        let graphs: Vec<String> = world_at(store, Some(&ground), &Asking::default(), memo)?
            .into_iter()
            .map(|g| if g == ground { base.clone() } else { g })
            .collect();
        let made = apply(store, cand, &child, Some(&base), Some(graphs), memo)?;
        if made {
            changed(store, &child, &base, memo)?;
        }
        store.clear_graph(&base)?;
        made
    };
    if !made {
        return Ok(false);
    }
    let kinds = closed(store, POSSIBLE_GRAPH, memo)?;
    let cat = named(&catalogue(store, memo)?)?;
    let world = named(&child)?;
    let row = |p: &str, o: Term| -> Result<Quad, Error> { Ok(Quad::new(world.clone(), named(p)?, o, cat.clone())) };
    let mut quads = Vec::new();
    for kind in &kinds {
        quads.push(row(RDF_TYPE, named(kind)?.into())?);
    }
    let spent = py_float_repr(py_round(binding.spent + cost));
    let spent_type = if spent.contains('e') { xsd::DOUBLE } else { xsd::DECIMAL };
    let period = BlankNode::default();
    quads.extend([
        row(ARRIVED_BY, named(DERIVED)?.into())?,
        row(
            HASH,
            Literal::new_simple_literal(digest_of(store, &child, within)?).into(),
        )?,
        row(SPENT, Literal::new_typed_literal(spent, spent_type).into())?,
        row(
            MINTED,
            Literal::new_typed_literal(binding.minted.to_string(), xsd::INTEGER).into(),
        )?,
        row(BY, named(cand)?.into())?,
        row(TEMPORAL, period.clone().into())?,
        Quad::new(period.clone(), named(RDF_TYPE)?, named(PERIOD_OF_TIME)?, cat.clone()),
        Quad::new(period.clone(), named(START)?, isoliteral(start), cat.clone()),
        Quad::new(period, named(END)?, isoliteral(end), cat.clone()),
    ]);
    store.add(quads)?;
    Ok(true)
}

/// Make `into` out of `base` — the world `cand` is taken in, unless the caller hands the ground at its landing
/// with the path replayed — with the action's effect applied, reading `graphs`. False, and no graph left, where
/// the effect says nothing about this world.
fn apply(
    store: &Store,
    cand: &str,
    into: &str,
    base: Option<&str>,
    graphs: Option<Vec<String>>,
    memo: &mut Memo,
) -> Result<bool, Error> {
    let binding = binding(store, cand, memo)?;
    let Some(carried) = carried(store, &binding.action, memo)? else {
        return Ok(false);
    };
    if carried.rules.is_empty() {
        return Ok(false);
    }
    let source = base.unwrap_or(&binding.from).to_string();
    let leaves = match graphs {
        Some(graphs) => graphs,
        None => world_at(store, Some(&binding.from), &Asking::default(), memo)?,
    };
    store.copy_graph(&source, into)?;
    let reading: Vec<String> = leaves
        .into_iter()
        .map(|g| if g == source { into.to_string() } else { g })
        .collect();
    let reading: Vec<&str> = reading.iter().map(String::as_str).collect();
    run(store, &carried.rules, into, &reading, &refs(&tokens(&binding)));
    if same(store, &source, into)? {
        store.clear_graph(into)?;
        return Ok(false);
    }
    Ok(true)
}

/// Whether two graphs hold the same triples.
fn same(store: &Store, one: &str, other: &str) -> Result<bool, Error> {
    let triples = |g: &str| -> Result<HashSet<Triple>, Error> { Ok(store.triples(g)?.into_iter().collect()) };
    Ok(triples(one)? == triples(other)?)
}

/// A copy of `ground` with every step on the path to `cand`'s world applied onto it in order, each with its own
/// filling. Named `<child>.base`, the caller's to clear — or `into`, where the copy is itself the child.
fn replayed(
    store: &Store,
    cand: &str,
    child: &str,
    ground: &str,
    into: Option<&str>,
    memo: &mut Memo,
) -> Result<String, Error> {
    let binding = binding(store, cand, memo)?;
    let base = into.map(String::from).unwrap_or_else(|| format!("{child}.base"));
    store.clear_graph(&base)?;
    store.copy_graph(ground, &base)?;
    let graphs: Vec<String> = world_at(store, Some(ground), &Asking::default(), memo)?
        .into_iter()
        .map(|g| if g == ground { base.clone() } else { g })
        .collect();
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let cat = catalogue(store, memo)?;
    let text = bind(
        PATH_Q,
        &[("world", Value::iri(binding.from.clone())), ("cat", Value::iri(cat))],
    )?;
    let path: Vec<String> = store.rows(&text, &[])?.iter().filter_map(|r| iri(r, "c")).collect();
    for step in &path {
        let taken = self::binding(store, step, memo)?;
        if let Some(carried) = carried(store, &taken.action, memo)? {
            run(store, &carried.rules, &base, &graphs, &refs(&tokens(&taken)));
        }
    }
    log::debug!(
        "{} lands in {ground}: {} step(s) replayed there",
        local_of(child),
        path.len()
    );
    Ok(base)
}

/// Say what the effect changed in `base`, the world `world` was forked from, as two graphs derived from `world`,
/// named even when empty.
fn changed(store: &Store, world: &str, base: &str, memo: &mut Memo) -> Result<(), Error> {
    let (adds, retracts) = (format!("{world}.adds"), format!("{world}.retracts"));
    let here: HashSet<Triple> = store.triples(world)?.into_iter().collect();
    let there: HashSet<Triple> = store.triples(base)?.into_iter().collect();
    let (to_adds, to_retracts) = (named(&adds)?, named(&retracts)?);
    store.add(here.difference(&there).map(|t| t.clone().in_graph(to_adds.clone())))?;
    store.add(there.difference(&here).map(|t| t.clone().in_graph(to_retracts.clone())))?;
    let cat = named(&catalogue(store, memo)?)?;
    let mut rows = Vec::new();
    for (graph, kind) in [(&to_adds, ADDS_GRAPH), (&to_retracts, RETRACTS_GRAPH)] {
        for k in closed(store, kind, memo)? {
            rows.push(Quad::new(graph.clone(), named(RDF_TYPE)?, named(&k)?, cat.clone()));
        }
        rows.push(Quad::new(
            graph.clone(),
            named(ARRIVED_BY)?,
            named(DERIVED)?,
            cat.clone(),
        ));
        rows.push(Quad::new(
            graph.clone(),
            named(WAS_DERIVED_FROM)?,
            named(world)?,
            cat.clone(),
        ));
    }
    store.add(rows)
}

/// The `$tokens` a rule text takes, off a candidate's binding: the world it is taken in, whom the self acts for,
/// the world's start, and one per parameter under its local part — each value's text handed as the Python
/// kernel's binder takes text: an IRI wrapped, anything else spliced as written.
fn tokens(binding: &Binding) -> Vec<(String, Value)> {
    let mut out: Vec<(String, Value)> = vec![
        ("state".into(), Value::raw(format!("<{}>", binding.from))),
        ("subject".into(), as_text(&binding.subject)),
        ("now".into(), instant(binding.start)),
    ];
    for (p, v) in &binding.filled {
        let local = local_of(p);
        out.retain(|(name, _)| *name != local);
        out.push((local, as_text(v)));
    }
    out
}

/// Tokens as the binder takes them.
fn refs(tokens: &[(String, Value)]) -> Vec<(&str, Value)> {
    tokens
        .iter()
        .map(|(name, value)| (name.as_str(), value.clone()))
        .collect()
}

/// A value's text as the Python kernel's `render` takes a string: an IRI wrapped, anything else as written.
fn as_text(text: &str) -> Value {
    if IRI.is_match(text) {
        Value::iri(text)
    } else {
        Value::raw(text)
    }
}

/// Every ground laid in the store, once a pass.
fn grounds(store: &Store, memo: &mut Memo) -> Result<HashSet<String>, Error> {
    if memo.ground_set.is_none() {
        let found = store.graphs_of(&[GROUND_GRAPH], &Within::default())?;
        memo.ground_set = Some(found.into_iter().collect());
    }
    Ok(memo.ground_set.clone().expect("asked above"))
}

/// The ground holding at `at`, or None before the first, once per instant.
fn ground_at(store: &Store, at: DateTime, memo: &mut Memo) -> Result<Option<String>, Error> {
    let key = at.to_string();
    if let Some(known) = memo.ground_at.get(&key) {
        return Ok(known.clone());
    }
    let found = store.graphs_of(&[GROUND_GRAPH], &Within::at(at))?.into_iter().next();
    memo.ground_at.insert(key, found.clone());
    Ok(found)
}

/// `class` and every kind the vocabulary puts it beneath, once a pass.
fn closed(store: &Store, class: &str, memo: &mut Memo) -> Result<Vec<String>, Error> {
    if !memo.closed.contains_key(class) {
        let kinds = store.closed(class)?;
        memo.closed.insert(class.to_string(), kinds);
    }
    Ok(memo.closed[class].clone())
}

/// What a candidate's row says, read once a pass off the catalogue's index.
fn binding(store: &Store, cand: &str, memo: &mut Memo) -> Result<Binding, Error> {
    if let Some(known) = memo.bindings.get(cand) {
        return Ok(known.clone());
    }
    let cat = catalogue(store, memo)?;
    let node = named(cand)?;
    let subject = Term::NamedNode(node.clone());
    let one = |p: &str| -> Result<Option<Term>, Error> { Ok(store.objects(&subject, p, &cat)?.into_iter().next()) };
    let missing = || Error::Evaluation(format!("no candidate {cand} — was it admitted?"));
    let (Some(Term::NamedNode(from)), Some(Term::NamedNode(action)), Some(minted)) =
        (one(FROM)?, one(FILLS)?, one(MINTED)?)
    else {
        return Err(missing());
    };
    let from_node = Term::NamedNode(from.clone());
    let possible = store.holds(from.as_str(), RDF_TYPE, POSSIBLE_GRAPH, &cat)?;
    let mut period = None;
    for p in store.objects(&from_node, TEMPORAL, &cat)? {
        if let Some(start) = store.objects(&p, START, &cat)?.into_iter().next() {
            let end = if possible {
                store.objects(&p, END, &cat)?.into_iter().next()
            } else {
                None
            };
            period = Some((lexical(&start)?, end.as_ref().map(lexical).transpose()?));
            break;
        }
    }
    let (start, end) = period.ok_or_else(missing)?;
    let spent = store
        .objects(&from_node, SPENT, &cat)?
        .into_iter()
        .next()
        .and_then(|s| match s {
            Term::Literal(l) => l.value().parse().ok(),
            _ => None,
        })
        .unwrap_or(0.0);
    let read: HashSet<&str> = [FROM, FILLS, MINTED, RDF_TYPE].into();
    //  THE CANDIDATE'S OWN ROWS, by its subject in the catalogue's index, never the catalogue scanned: it grows
    //  with the cone, and scanned per candidate it was three quarters of a five-disk pass.
    let mut filled = Vec::new();
    let graph = named(&cat)?;
    for quad in store
        .engine()
        .quads_for_pattern(Some(node.as_ref().into()), None, None, Some(graph.as_ref().into()))
    {
        let quad = quad.map_err(|e| Error::Evaluation(e.to_string()))?;
        if !read.contains(quad.predicate.as_str()) {
            filled.push((quad.predicate.as_str().to_string(), term_text(&quad.object)));
        }
    }
    let binding = Binding {
        from: from.into_string(),
        start,
        end: end.unwrap_or(start),
        action: action.into_string(),
        minted: match minted {
            Term::Literal(l) => l.value().parse().map_err(|_| missing())?,
            _ => return Err(missing()),
        },
        spent,
        filled,
        subject: acts_for(store, memo)?.unwrap_or_else(|| "urn:nobody".to_string()),
    };
    memo.bindings.insert(cand.to_string(), binding.clone());
    Ok(binding)
}

/// Whom the self acts for, once a pass.
fn acts_for(store: &Store, memo: &mut Memo) -> Result<Option<String>, Error> {
    if let Some(known) = &memo.acts_for {
        return Ok(known.clone());
    }
    let mut graphs = store.graphs_of(&[BELIEF], &Within::common())?;
    graphs.extend(store.graphs_of(&[SELF_GRAPH], &Within::default())?);
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let found = store.rows(ACTS_FOR_Q, &graphs)?.first().and_then(|r| value(r, "for"));
    memo.acts_for = Some(found.clone());
    Ok(found)
}

/// What an action carries for a search, once a pass: its texts and its effect's transitions in order, a rule
/// that is no transition said in the log and left out; None for no action at all.
fn carried(store: &Store, action: &str, memo: &mut Memo) -> Result<Option<Carried>, Error> {
    if let Some(known) = memo.carried.get(action) {
        return Ok(known.clone());
    }
    let graphs = store.graphs_of(&[ACTION], &Within::default())?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let bound = [("rule", Value::iri(action))];
    let found = store.rows(&bind(RULE_Q, &bound)?, &graphs)?;
    let carried = match found.first() {
        None => None,
        Some(row) => {
            let mut rules = Vec::new();
            for r in store.rows(&bind(EFFECT_Q, &bound)?, &graphs)? {
                if value(&r, "transition").as_deref() != Some("true") {
                    log::error!(
                        "a rule of the effect of {} is no belief:Transition, so it changes nothing",
                        local_of(action)
                    );
                    continue;
                }
                rules.push(Rule {
                    order: value(&r, "order").and_then(|o| o.parse().ok()).unwrap_or(0.0),
                    update: value(&r, "update"),
                    name: Some(format!("the effect of {}", local_of(action))),
                });
            }
            Some(Carried {
                lands: value(row, "lands"),
                costs: value(row, "costs"),
                rules,
            })
        }
    };
    memo.carried.insert(action.to_string(), carried.clone());
    Ok(carried)
}

#[derive(Clone, Copy)]
enum Text {
    Lands,
    Costs,
}

/// How long after the act the change can show, the band the action's `landsAfter` answers in seconds; nought
/// twice where it declares none, declines, or binds only one of the two.
fn landing(store: &Store, cand: &str, memo: &mut Memo) -> Result<(f64, f64), Error> {
    let Some(row) = answer(store, cand, memo, Text::Lands)? else {
        return Ok((0.0, 0.0));
    };
    match (number(&row, "least"), number(&row, "most")) {
        (Some(least), Some(most)) => Ok((least.min(most), least.max(most))),
        _ => {
            log::error!("the landing of this action binds no ?least and ?most, so it lands at once");
            Ok((0.0, 0.0))
        }
    }
}

/// One of a rule's selects that answers a number, asked; None where it declines.
fn figure(store: &Store, cand: &str, memo: &mut Memo, text: Text, column: &str) -> Result<Option<f64>, Error> {
    Ok(answer(store, cand, memo, text)?.and_then(|row| number(&row, column)))
}

fn number(row: &orexis::store::Row, column: &str) -> Option<f64> {
    value(row, column)?.parse().ok()
}

/// The first row of one of the action's selects, asked over the world the candidate is taken in; None where the
/// action states no such text, it yields no row, or it will not run — said in the log.
fn answer(store: &Store, cand: &str, memo: &mut Memo, text: Text) -> Result<Option<orexis::store::Row>, Error> {
    let binding = binding(store, cand, memo)?;
    let Some(carried) = carried(store, &binding.action, memo)? else {
        return Ok(None);
    };
    let (name, Some(select)) = (match text {
        Text::Lands => ("lands", carried.lands),
        Text::Costs => ("costs", carried.costs),
    }) else {
        return Ok(None);
    };
    let graphs = world_at(store, Some(&binding.from), &Asking::default(), memo)?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let asked = bind(&select, &refs(&tokens(&binding))).and_then(|bound| store.rows(&bound, &graphs));
    match asked {
        Ok(rows) => Ok(rows.into_iter().next()),
        Err(e) => {
            log::error!("{name} query for this action would not run: {e}");
            Ok(None)
        }
    }
}

/// An instant moved by a number of seconds, as Python's `timedelta` moves one.
fn shifted(at: DateTime, seconds: f64) -> Result<DateTime, Error> {
    at.checked_add_day_time_duration(microseconds(seconds))
        .ok_or_else(|| Error::Evaluation(format!("{at} moved by {seconds} s is out of range")))
}

/// An instant as the literal the Python kernel writes.
fn isoliteral(at: DateTime) -> Term {
    Literal::new_typed_literal(orexis::clock::isoformat(at), xsd::DATE_TIME).into()
}

/// A term's text as SPARQL-JSON gives it: an IRI's, a literal's value, a blank node's label.
fn term_text(term: &Term) -> String {
    match term {
        Term::NamedNode(n) => n.as_str().to_string(),
        Term::Literal(l) => l.value().to_string(),
        Term::BlankNode(b) => b.as_str().to_string(),
    }
}

#[cfg(test)]
mod tests {
    //! `take`, held to `crates/orexis-planning/tests/take/`'s cases as `test_take.py` holds the Python act: every candidate
    //! that has reached no world taken in mint order, and the diff the worlds they made.

    use std::collections::BTreeSet;
    use std::path::PathBuf;

    use orexis::snapshots;

    use super::*;
    use crate::admit::{Scope, admit};

    const UNTAKEN_Q: &str = "
SELECT ?cand WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?cand a planning:Candidate ; planning:minted ?m .
               FILTER NOT EXISTS { ?w planning:by ?cand } } }
ORDER BY ?m";

    const EDGES_Q: &str = "
SELECT ?cand ?m ?w ?wm WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?cand a planning:Candidate ; planning:minted ?m .
               OPTIONAL { ?w planning:by ?cand ; planning:minted ?wm } } }
ORDER BY ?m";

    const PRESENT_Q: &str =
        "SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph } } LIMIT 1";

    fn cases() -> PathBuf {
        snapshots::tree().join("orexis-planning/tests/take")
    }

    fn untaken(store: &Store) -> Vec<String> {
        store
            .rows(UNTAKEN_Q, &[])
            .unwrap()
            .iter()
            .filter_map(|r| iri(r, "cand"))
            .collect()
    }

    #[test]
    fn take_forks_the_worlds_the_diff_says() {
        for case in snapshots::cases_in(&cases()) {
            let store = snapshots::stand_in(&case);
            let mut memo = Memo::default();
            let candidates = untaken(&store);
            assert!(!candidates.is_empty(), "{} admits no candidate to take", case.display());
            for cand in candidates {
                take(&store, &cand, None, &mut memo).unwrap();
            }
            snapshots::held_to_diff(&case, &store, "take");
        }
    }

    #[test]
    fn every_case_is_read_and_no_diff_is_orphaned() {
        snapshots::all_read(&cases(), 2);
    }

    fn admitted(memo: &mut Memo) -> Store {
        let store =
            snapshots::stand_in(&snapshots::tree().join("orexis-planning/tests/admit/one_lever_two_tanks.trig"));
        let present = iri(&store.rows(PRESENT_Q, &[]).unwrap()[0], "g").unwrap();
        admit(&store, &present, &Scope::default(), memo).unwrap();
        store
    }

    #[test]
    fn siblings_differing_in_one_value_never_share_a_graph() {
        let mut memo = Memo::default();
        let store = admitted(&mut memo);
        for cand in untaken(&store) {
            assert!(take(&store, &cand, None, &mut memo).unwrap());
        }
        let edges = store.rows(EDGES_Q, &[]).unwrap();
        let worlds: Vec<String> = edges.iter().filter_map(|e| iri(e, "w")).collect();
        assert_eq!((edges.len(), worlds.len()), (2, 2));
        let possible: BTreeSet<String> = store
            .graphs_of(&[POSSIBLE_GRAPH], &Within::default())
            .unwrap()
            .into_iter()
            .collect();
        assert_eq!(worlds.iter().cloned().collect::<BTreeSet<_>>(), possible);
        for e in &edges {
            assert_eq!(value(e, "m"), value(e, "wm"), "a world carries its candidate's number");
        }
        let held: Vec<BTreeSet<String>> = worlds
            .iter()
            .map(|w| store.triples(w).unwrap().iter().map(|t| t.to_string()).collect())
            .collect();
        assert!(!held[0].is_empty() && !held[1].is_empty() && held[0] != held[1]);
    }

    #[test]
    fn a_second_pass_over_one_store_mints_above_everything_it_holds() {
        let mut first = Memo::default();
        let store = admitted(&mut first);
        for cand in untaken(&store) {
            take(&store, &cand, None, &mut first).unwrap();
        }
        let before = store.rows(EDGES_Q, &[]).unwrap();
        let names: BTreeSet<String> = before
            .iter()
            .flat_map(|e| [iri(e, "cand"), iri(e, "w")])
            .flatten()
            .collect();
        let mut second = Memo::default();
        admit(&store, &iri(&before[0], "w").unwrap(), &Scope::default(), &mut second).unwrap();
        for cand in untaken(&store) {
            take(&store, &cand, None, &mut second).unwrap();
        }
        let after = store.rows(EDGES_Q, &[]).unwrap();
        let new: Vec<_> = after
            .iter()
            .filter(|e| !names.contains(&iri(e, "cand").unwrap()))
            .collect();
        assert!(!new.is_empty() && new.iter().all(|e| iri(e, "w").is_some()));
        let number = |e: &orexis::store::Row| value(e, "m").unwrap().parse::<u64>().unwrap();
        assert!(new.iter().map(|e| number(e)).min() > before.iter().map(number).max());
        let all: BTreeSet<String> = after
            .iter()
            .flat_map(|e| [iri(e, "cand"), iri(e, "w")])
            .flatten()
            .collect();
        assert_eq!(
            all.len(),
            2 * after.len(),
            "every candidate and every world under a name of its own"
        );
    }
}
