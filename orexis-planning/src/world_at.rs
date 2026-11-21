//! WHAT A RULE IS ANSWERED OVER IN ONE WORLD, once the ground is laid, as `agent/planning/world_at.py` answers it:
//! what the world states, the records, the desires and the wants holding at the world's own instant, and the
//! world itself in the state's place — everything the grounds speak for left out. Or, named as none at an
//! instant, the PRESENT the store holds: every belief and its revisions where a ground would stand.
//!
//! The argument for each clause is the Python module's docstring, which this follows line for line.

use std::collections::HashSet;

use oxigraph::model::Term;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::instant;
use orexis::ontology::{BELIEF, DERIVED, END, GRAPH_PREFIX, START};
use orexis::store::{Store, Within, iri};

use crate::Memo;
use crate::ontology::{CHANGEABLE_GRAPH, CONE_GRAPH, GROUND_GRAPH, KNOWN, POSSIBLE_GRAPH};
use crate::terms::{RDF_TYPE, TEMPORAL};

/// Who is asking and when the present is, for a reader that is not standing in a world.
#[derive(Clone, Debug, Default)]
pub struct Asking {
    pub holder: Option<String>,
    pub now: Option<DateTime>,
}

/// The graphs a rule reads in `world`, or in the present where `world` is None, which is then read at `now`.
pub fn world_at(store: &Store, world: Option<&str>, asking: &Asking, memo: &mut Memo) -> Result<Vec<String>, Error> {
    /// EVERY BELIEF THAT BEGINS AFTER `$now`, and the changeable part cut from one: a forecast the present has not
    /// reached (#987).
    const AHEAD_Q: &str = "PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX orexis: <http://example.org/orexis#>
    PREFIX planning: <http://example.org/orexis/planning#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    SELECT ?g WHERE {
      { GRAPH ?m_g { ?g a orexis:BeliefGraph ; dcterms:temporal/orexis:start ?start } }
      UNION { GRAPH ?m_g { ?g a planning:ChangeableGraph ; prov:wasDerivedFrom ?source }
              GRAPH ?m_source { ?source dcterms:temporal/orexis:start ?start } }
      FILTER(?start > $now) }";
    let (at, until) = match world {
        None => {
            let now = asking.now.ok_or_else(|| {
                Error::Evaluation("the present is read at an instant, and a reader meaning now says so".into())
            })?;
            (now, now)
        }
        Some(world) => match when(store, world, memo)? {
            Some((at, until)) => (at, until.unwrap_or(at)),
            None => {
                return Err(Error::Evaluation(format!(
                    "{world} says no period — is it a ground or a possible world?"
                )));
            }
        },
    };
    if memo.spoken_for.is_none() {
        let spoken = store.graphs_of(&[CHANGEABLE_GRAPH, GROUND_GRAPH, POSSIBLE_GRAPH], &Within::default())?;
        memo.spoken_for = Some(spoken.into_iter().collect());
    }
    let key = format!("{at}|{until}|{:?}|{:?}", asking.holder, asking.now);
    if !memo.knowable.contains_key(&key) {
        let within = Within {
            at: Some(at),
            until: Some(until),
            holder: asking.holder.clone(),
            now: asking.now,
            common: false,
        };
        let spoken = memo.spoken_for.as_ref().expect("asked above");
        let known: Vec<String> = store
            .graphs_of(KNOWN, &within)?
            .into_iter()
            .filter(|g| !spoken.contains(g))
            .collect();
        memo.knowable.insert(key.clone(), known);
    }
    let known = memo.knowable[&key].clone();
    match world {
        Some(world) => Ok([known, vec![world.to_string()]].concat()),
        None => {
            let now = asking.now.expect("asked above");
            let text = bind(AHEAD_Q, &[("now", Value::instant(now))])?;
            let ahead: HashSet<String> = store.rows(&text, &[])?.iter().filter_map(|r| iri(r, "g")).collect();
            let beliefs: Vec<String> = store
                .graphs_of(&[BELIEF], &Within::default())?
                .into_iter()
                .filter(|g| !ahead.contains(g))
                .collect();
            let refs: Vec<&str> = beliefs.iter().map(String::as_str).collect();
            let revisions = store.revisions_of(&refs, BELIEF)?;
            let changeable = store
                .graphs_of(&[CHANGEABLE_GRAPH], &Within::default())?
                .into_iter()
                .filter(|g| !ahead.contains(g));
            let mut seen = HashSet::new();
            Ok(known
                .into_iter()
                .chain(beliefs.iter().cloned())
                .chain(revisions)
                .chain(changeable)
                .filter(|g| seen.insert(g.clone()))
                .collect())
        }
    }
}

/// A world's period off its metadata: its start, and its end where it is a possible world. Asked once per world.
pub fn when(store: &Store, world: &str, memo: &mut Memo) -> Result<Option<(DateTime, Option<DateTime>)>, Error> {
    if let Some(known) = memo.when.get(world) {
        return Ok(*known);
    }
    let Some(metadata) = store.metadata_of(world)? else {
        memo.when.insert(world.to_string(), None);
        return Ok(None);
    };
    let subject = Term::NamedNode(named(world)?);
    let possible = store.holds(world, RDF_TYPE, POSSIBLE_GRAPH, &metadata)?;
    let mut found = None;
    for period in store.objects(&subject, TEMPORAL, &metadata)? {
        if let Some(start) = store.objects(&period, START, &metadata)?.first() {
            let until = if possible {
                store
                    .objects(&period, END, &metadata)?
                    .first()
                    .map(lexical)
                    .transpose()?
            } else {
                None
            };
            found = Some((lexical(start)?, until));
            break;
        }
    }
    memo.when.insert(world.to_string(), found);
    Ok(found)
}

/// The period `graph`'s metadata says it holds over, its start and its end where it says one: None where it says
/// no start. Asked of the index, a lookup in the graph's metadata graph.
pub fn period_of(store: &Store, graph: &str) -> Result<Option<(DateTime, Option<DateTime>)>, Error> {
    let Some(metadata) = store.metadata_of(graph)? else {
        return Ok(None);
    };
    for period in store.objects(&Term::NamedNode(named(graph)?), TEMPORAL, &metadata)? {
        if let Some(start) = store.objects(&period, START, &metadata)?.first() {
            let end = store
                .objects(&period, END, &metadata)?
                .first()
                .map(lexical)
                .transpose()?;
            return Ok(Some((lexical(start)?, end)));
        }
    }
    Ok(None)
}

/// THE GRAPH A SEARCH'S OWN ROWS ARE WRITTEN IN, once a pass: the store's cone graph, its candidates, its weighings
/// and the path between its worlds, or the name a writer gives one where the store has none yet. A read asks it
/// and writes nothing; whoever writes a row of the search says it is one first (`cone_made`).
pub fn cone(store: &Store, memo: &mut Memo) -> Result<String, Error> {
    if let Some(name) = &memo.cone {
        return Ok(name.clone());
    }
    let name = store
        .graphs_of(&[CONE_GRAPH], &Within::default())?
        .into_iter()
        .next()
        .unwrap_or_else(|| format!("{GRAPH_PREFIX}cone"));
    memo.cone = Some(name.clone());
    Ok(name)
}

/// The store's cone graph, or the name a writer gives one, asked with no memo.
pub fn cone_of(store: &Store) -> Result<String, Error> {
    cone(store, &mut Memo::default())
}

/// The cone graph, said to be one where nothing says so yet, asked with no memo.
pub fn cone_made_of(store: &Store) -> Result<String, Error> {
    cone_made(store, &mut Memo::default())
}

/// Every row of the search about `graph` taken back: for a world or a ground that goes.
pub fn out_of_the_cone(store: &Store, graph: &str) -> Result<(), Error> {
    let (cone, subject) = (named(&cone_of(store)?)?, named(graph)?);
    let rows: Vec<oxigraph::model::Quad> = store
        .engine()
        .quads_for_pattern(
            Some(subject.as_ref().into()),
            None,
            None,
            Some(oxigraph::model::GraphNameRef::NamedNode(cone.as_ref())),
        )
        .collect::<Result<_, _>>()
        .map_err(|e| Error::Evaluation(e.to_string()))?;
    store.remove_all(&rows)
}

/// The cone graph, said to be one where nothing says so yet: for whoever writes a row of the search.
pub fn cone_made(store: &Store, memo: &mut Memo) -> Result<String, Error> {
    let name = cone(store, memo)?;
    if !memo.cone_made {
        if store.metadata_of(&name)?.is_none() {
            store.classify(&name, CONE_GRAPH, DERIVED, None, None, None)?;
        }
        memo.cone_made = true;
    }
    Ok(name)
}

/// An instant a row holds, as the term it is.
pub fn lexical(term: &Term) -> Result<DateTime, Error> {
    match term {
        Term::Literal(literal) => instant(literal.value()),
        other => Err(Error::Evaluation(format!("no instant: {other}"))),
    }
}

pub(crate) fn named(iri: &str) -> Result<oxigraph::model::NamedNode, Error> {
    oxigraph::model::NamedNode::new(iri).map_err(|e| Error::Evaluation(format!("no IRI: {iri}: {e}")))
}
