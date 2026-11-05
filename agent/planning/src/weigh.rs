//! WEIGHING: judging one thing FOR ONE WANT OR DESIRE, and writing what was found, as `agent/planning/weigh.py`
//! weighs it — the argument for every clause is that module's docstring, which this follows.
//!
//! A world's own facts are true of it whoever asks; whether a want is met there, whether its search may still open
//! it and whether it has are true of the world AND the want, so they hang off a node naming both. A CANDIDATE is
//! weighed by what it reached: nothing, so it repeats the world it was taken in; a world a weighing of this want
//! already holds by hash, reached no sooner, so it repeats that one; or a new world, judged as a world is. A WORLD
//! is judged by the met-test compiled once a pass and asked over the world at its own instant; a met-test that
//! cannot be compiled or run writes no verdict. In a world marked impossible, or one landing past the want's
//! lifting, the weighing is bare.

use std::collections::BTreeSet;

use oxigraph::model::vocab::xsd;
use oxigraph::model::{BlankNode, Literal, Quad, Term};
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{instant, isoformat};
use orexis::ontology::RECORD;
use orexis::store::{Row, Store, Within, iri, value};

use crate::Memo;
use crate::admit::local_of;
use crate::ontology::{CONSTRAINT_GRAPH, DESIRE, SHAPES, WANT};
use crate::shapes::Shapes;
use crate::violation::{Compiled, select_of};
use crate::world_at::{Asking, catalogue, named, world_at};

const PLANNING: &str = "http://example.org/orexis/planning#";
const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const SH_SELECT: &str = "http://www.w3.org/ns/shacl#select";
const DERIVED_FROM: &str = "http://www.w3.org/ns/prov#wasDerivedFrom";

const ABOUT_Q: &str = "
SELECT ?from ?child ?seen ?impossible WHERE {
  GRAPH $cat { OPTIONAL { $about planning:from ?from }
    OPTIONAL { ?child planning:by $about ; orexis:hash ?hash .
               OPTIONAL { ?child planning:impossible ?impossible }
               OPTIONAL { ?x a planning:Weighing ; planning:for $for ; planning:weighs ?seen .
                          ?seen orexis:hash ?hash } } } }
ORDER BY ?seen";

const HELD_Q: &str = "
SELECT ?holder ?want WHERE {
  GRAPH ?g { ?holder planning:holds $for . OPTIONAL { $for a planning:Want . BIND(true AS ?want) } }
  OPTIONAL { GRAPH ?s { ?holder a orexis:Self } BIND(true AS ?self) } }
ORDER BY DESC(BOUND(?self)) ?holder LIMIT 1";

const PRESENT_Q: &str = "
SELECT (MIN(?start) AS ?now) WHERE {
  GRAPH $cat { ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start } }";

const PERIOD_Q: &str = "
SELECT ?start ?end ?reopens ?owed WHERE {
  GRAPH $cat { ?d a planning:WantGraph ; dcterms:temporal ?p .
               OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } }
  GRAPH ?d { $for a planning:Want OPTIONAL { $for planning:reopens ?reopens } }
  OPTIONAL { { GRAPH $cat { ?d orexis:arrivedBy orexis:Received } }
             UNION
             { GRAPH ?d { $for prov:wasDerivedFrom ?desire } GRAPH ?dg { ?desire a planning:Desire }
               GRAPH $cat { ?dg orexis:arrivedBy orexis:Received } }
             BIND(true AS ?owed) } } LIMIT 1";

const LANDS_Q: &str = "
SELECT ?start ?end WHERE { GRAPH $cat { $world dcterms:temporal ?p . ?p orexis:start ?start OPTIONAL { ?p orexis:end ?end } } }
LIMIT 1";

/// Weigh `about` — a world, a ground, or a candidate — for `for_`, a want or a desire, and write the weighing.
/// Its node.
pub fn weigh(store: &Store, for_: &str, about: &str, memo: &mut Memo) -> Result<String, Error> {
    let cat = catalogue(store, memo)?;
    let text = bind(
        ABOUT_Q,
        &[
            ("about", Value::iri(about)),
            ("cat", Value::iri(cat.clone())),
            ("for", Value::iri(for_)),
        ],
    )?;
    let answers = store.rows(&text, &[])?;
    let found = answers.first().cloned().unwrap_or_default();
    let held = held(store, for_, memo)?;
    let wants = value(&held, "want").is_some();
    let mut verdict: Vec<(&str, Term)> = Vec::new();
    let mut violations: Vec<Row> = Vec::new();
    let (mut late, mut past) = (None, false);
    let world = if let Some(from) = iri(&found, "from") {
        let mut world = iri(&found, "child");
        if let Some(w) = &world
            && wants
        {
            (late, past) = when(store, for_, w, &cat, memo)?;
        }
        let mut seen: Vec<String> = answers.iter().filter_map(|a| iri(a, "seen")).collect();
        if world.is_some() && wants && !seen.is_empty() {
            let ours = rank(late, past);
            let mut kept = Vec::new();
            for s in seen {
                let (l, p) = when(store, for_, &s, &cat, memo)?;
                if rank(l, p) <= ours {
                    kept.push(s);
                }
            }
            seen = kept;
        }
        let repeats = if world.is_none() {
            Some(from)
        } else {
            seen.into_iter().next()
        };
        if let Some(repeats) = repeats {
            verdict.push(("repeats", named(&repeats)?.into()));
            world = None;
        }
        world
    } else {
        Some(about.to_string())
    };
    let weighed = world.clone().unwrap_or_else(|| about.to_string());
    let node = format!("{weighed}.for.{}", local_of(for_));
    if let Some(world) = &world
        && !found.contains_key("impossible")
        && !past
    {
        let report = report(store, for_, world, &held, memo)?;
        if let Some(rows) = &report {
            verdict.push(("met", boolean(rows.is_empty())));
            violations.clone_from(rows);
        }
        if wants && report.as_ref().is_none_or(|r| !r.is_empty()) {
            verdict.push(("open", boolean(true)));
        }
        if wants {
            if let Some(left) = remaining(store, for_, world, &held, memo)? {
                verdict.push(("remaining", numeric(&left)?));
            }
            if let Some(late) = late {
                verdict.push((
                    "late",
                    Literal::new_typed_literal(isoformat(late), xsd::DATE_TIME).into(),
                ));
            }
        }
    }
    let graph = named(&cat)?;
    let subject = named(&node)?;
    let p = |local: &str| named(&format!("{PLANNING}{local}"));
    let mut quads = vec![
        Quad::new(subject.clone(), named(RDF_TYPE)?, p("Weighing")?, graph.clone()),
        Quad::new(subject.clone(), p("for")?, named(for_)?, graph.clone()),
        Quad::new(subject.clone(), p("weighs")?, named(&weighed)?, graph.clone()),
    ];
    for (local, object) in verdict {
        quads.push(Quad::new(subject.clone(), p(local)?, object, graph.clone()));
    }
    for row in violations {
        let v = BlankNode::default();
        quads.push(Quad::new(subject.clone(), p("violation")?, v.clone(), graph.clone()));
        let mut part = |local: &str, column: &str| -> Result<(), Error> {
            if let Some(term) = row.get(column)
                && !(column == "_offending" && matches!(term, Term::BlankNode(_)))
            {
                quads.push(Quad::new(v.clone(), p(local)?, term.clone(), graph.clone()));
            }
            Ok(())
        };
        part("instance", "this")?;
        part("constraint", "_constraint")?;
        part("about", "_about")?;
        part("offending", "_offending")?;
    }
    store.add(quads)?;
    Ok(node)
}

/// Who holds what is weighed for, the self first, and whether it is a want — once a pass.
fn held(store: &Store, for_: &str, memo: &mut Memo) -> Result<Row, Error> {
    if let Some(known) = memo.held.get(for_) {
        return Ok(known.clone());
    }
    let found = store
        .rows(&bind(HELD_Q, &[("for", Value::iri(for_))])?, &[])?
        .into_iter()
        .next()
        .unwrap_or_default();
    memo.held.insert(for_.to_string(), found.clone());
    Ok(found)
}

/// The instant `world` lands late at for the want `for_`, or None where it is on time, and whether it lands
/// past the instant the want lifts by — must miss for a want of the agent's own, may miss for an obligation.
fn when(store: &Store, for_: &str, world: &str, cat: &str, memo: &mut Memo) -> Result<(Option<DateTime>, bool), Error> {
    if !memo.periods.contains_key(for_) {
        let text = bind(PERIOD_Q, &[("cat", Value::iri(cat)), ("for", Value::iri(for_))])?;
        let found = store.rows(&text, &[])?.into_iter().next().unwrap_or_default();
        memo.periods.insert(for_.to_string(), found);
    }
    let period = memo.periods[for_].clone();
    let (start, end) = (value(&period, "start"), value(&period, "end"));
    if start.is_none() && end.is_none() {
        return Ok((None, false));
    }
    let text = bind(LANDS_Q, &[("world", Value::iri(world)), ("cat", Value::iri(cat))])?;
    let lands = store.rows(&text, &[])?.into_iter().next().unwrap_or_default();
    let Some(earliest) = value(&lands, "start") else {
        return Ok((None, false));
    };
    let earliest = instant(&earliest)?;
    let latest = value(&lands, "end")
        .map(|e| instant(&e))
        .transpose()?
        .unwrap_or(earliest);
    let now = present(store, cat, memo)?;
    let at = match (&start, value(&period, "reopens")) {
        (Some(s), None) => Some(instant(s)?),
        _ => None,
    };
    let lifts = end.map(|e| instant(&e)).transpose()?;
    let judged = if value(&period, "owed").is_some() {
        latest
    } else {
        earliest
    };
    let ahead = matches!((at, now), (Some(at), Some(now)) if at > now);
    let late = match at {
        Some(at) if ahead && judged > at => Some(judged),
        _ => None,
    };
    Ok((late, lifts.is_some_and(|l| earliest > l)))
}

/// Where a world stands in the order a want's achievers are ranked by in time: on time, late by its instant,
/// past the lifting last.
fn rank(late: Option<DateTime>, past: bool) -> (u8, Option<DateTime>) {
    match (past, late) {
        (true, _) => (2, None),
        (false, None) => (0, None),
        (false, Some(at)) => (1, Some(at)),
    }
}

/// Where the timeline begins, the earliest ground — once a pass.
fn present(store: &Store, cat: &str, memo: &mut Memo) -> Result<Option<DateTime>, Error> {
    if let Some(known) = memo.present {
        return Ok(known);
    }
    let text = bind(PRESENT_Q, &[("cat", Value::iri(cat))])?;
    let found = store.rows(&text, &[])?.first().and_then(|r| value(r, "now"));
    let now = found.map(|n| instant(&n)).transpose()?;
    memo.present = Some(now);
    Ok(now)
}

/// The met-test's rows in `world`, each once — or None where there is no met-test to ask or the engine refuses.
fn report(store: &Store, for_: &str, world: &str, held: &Row, memo: &mut Memo) -> Result<Option<Vec<Row>>, Error> {
    let Some(select) = select(store, for_, memo)? else {
        return Ok(None);
    };
    let graphs = graphs(store, world, held, memo)?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    match store.rows(&select, &graphs) {
        Ok(rows) => {
            let mut seen = BTreeSet::new();
            Ok(Some(
                rows.into_iter()
                    .filter(|r| seen.insert(r.iter().map(|(k, v)| format!("{k}={v}")).collect::<Vec<_>>()))
                    .collect(),
            ))
        }
        Err(e) => {
            log::error!(
                "a met-test could not be read in {}: {e}",
                world.rsplit('/').next().unwrap_or(world)
            );
            Ok(None)
        }
    }
}

/// What a text about `world` is answered over: the world at its own instant, the holder's records at the present.
fn graphs(store: &Store, world: &str, held: &Row, memo: &mut Memo) -> Result<Vec<String>, Error> {
    let cat = catalogue(store, memo)?;
    let now = present(store, &cat, memo)?;
    let asking = Asking {
        holder: iri(held, "holder"),
        now,
    };
    world_at(store, Some(world), &asking, memo)
}

/// What the want's estimate reads in `world`, or None where it declares none or the select will not run.
fn remaining(store: &Store, for_: &str, world: &str, held: &Row, memo: &mut Memo) -> Result<Option<String>, Error> {
    if !memo.estimates.contains_key(for_) {
        let shapes = shapes(store, memo)?;
        let want: Term = named(for_)?.into();
        let mut node = shapes.value(&want, &format!("{PLANNING}estimates"));
        if node.is_none()
            && let Some(desire) = shapes.value(&want, DERIVED_FROM)
        {
            node = shapes.value(&desire, &format!("{PLANNING}estimates"));
        }
        let text = node.and_then(|n| shapes.value(&n, SH_SELECT)).map(|t| match t {
            Term::Literal(l) => l.value().to_string(),
            other => other.to_string(),
        });
        memo.estimates.insert(for_.to_string(), text);
    }
    let Some(text) = memo.estimates[for_].clone() else {
        return Ok(None);
    };
    let graphs = graphs(store, world, held, memo)?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    match store.rows(&text, &graphs) {
        Ok(rows) => Ok(rows.first().and_then(|r| value(r, "estimate"))),
        Err(e) => {
            log::error!(
                "the estimate of {} could not be read in {}: {e}",
                local_of(for_),
                world.rsplit('/').next().unwrap_or(world)
            );
            Ok(None)
        }
    }
}

/// `for_`'s met-test compiled, once a pass; None, said in the log, where the compiler refuses it.
fn select(store: &Store, for_: &str, memo: &mut Memo) -> Result<Option<String>, Error> {
    if let Some(known) = memo.selects.get(for_) {
        return Ok(known.clone());
    }
    let shapes = shapes(store, memo)?;
    let compiled = match select_of(&shapes, &named(for_)?.into(), store.namespaces()) {
        Ok(found) => found,
        Err(Compiled::Unsupported(u)) => {
            log::warn!(
                "{}: its met-test cannot be compiled, so it is not judged: {u}",
                local_of(for_)
            );
            None
        }
        Err(Compiled::Error(e)) => return Err(e),
    };
    memo.selects.insert(for_.to_string(), compiled.clone());
    Ok(compiled)
}

/// The shapes, desires, wants, records and constraints as one graph, once a pass.
pub fn shapes(store: &Store, memo: &mut Memo) -> Result<Shapes, Error> {
    if let Some(known) = &memo.shapes {
        return Ok(known.clone());
    }
    let graphs = store.graphs_of(&[DESIRE, WANT, RECORD, SHAPES, CONSTRAINT_GRAPH], &Within::default())?;
    let found = Shapes::of(store, &graphs)?;
    memo.shapes = Some(found.clone());
    Ok(found)
}

fn boolean(b: bool) -> Term {
    Literal::new_typed_literal(if b { "true" } else { "false" }, xsd::BOOLEAN).into()
}

/// A figure's text as SPARQL reads a bare number spliced into an update, as the Python copy splices it.
fn numeric(text: &str) -> Result<Term, Error> {
    let t = text.trim();
    let digits = t.trim_start_matches(['+', '-']);
    let datatype = if digits.contains(['e', 'E']) {
        xsd::DOUBLE
    } else if digits.contains('.') {
        xsd::DECIMAL
    } else if !digits.is_empty() && digits.chars().all(|c| c.is_ascii_digit()) {
        xsd::INTEGER
    } else {
        return Err(Error::Syntax(format!("an estimate that is no number: {text}")));
    };
    Ok(Literal::new_typed_literal(t, datatype).into())
}

#[cfg(test)]
mod tests;
