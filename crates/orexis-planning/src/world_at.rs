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
use orexis::bind::bind;
use orexis::clock::instant;
use orexis::ontology::{BELIEF, END, START};
use orexis::store::{Store, Within, iri};

use crate::Memo;
use crate::ontology::{CHANGEABLE_GRAPH, GROUND_GRAPH, KNOWN, POSSIBLE_GRAPH};
use crate::terms::{RDF_TYPE, TEMPORAL};

/// EVERY BELIEF THAT BEGINS AFTER `$now`, and the changeable part cut from one: a forecast the present has not
/// reached (#987).
const AHEAD_Q: &str = "
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               { ?g a orexis:BeliefGraph ; dcterms:temporal/orexis:start ?start }
               UNION { ?g a planning:ChangeableGraph ; prov:wasDerivedFrom/dcterms:temporal/orexis:start ?start }
               FILTER(?start > $now) } }";

/// Who is asking and when the present is, for a reader that is not standing in a world.
#[derive(Clone, Debug, Default)]
pub struct Asking {
    pub holder: Option<String>,
    pub now: Option<DateTime>,
}

/// The graphs a rule reads in `world`, or in the present where `world` is None, which is then read at `now`.
pub fn world_at(store: &Store, world: Option<&str>, asking: &Asking, memo: &mut Memo) -> Result<Vec<String>, Error> {
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
            let text = bind(AHEAD_Q, &[("now", orexis::store::instant(now))])?;
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

/// A world's period off its row: its start, and its end where it is a possible world. Asked once per world.
pub fn when(store: &Store, world: &str, memo: &mut Memo) -> Result<Option<(DateTime, Option<DateTime>)>, Error> {
    if let Some(known) = memo.when.get(world) {
        return Ok(*known);
    }
    let catalogue = catalogue(store, memo)?;
    let subject = Term::NamedNode(named(world)?);
    let possible = store.holds(world, RDF_TYPE, POSSIBLE_GRAPH, &catalogue)?;
    let mut found = None;
    for period in store.objects(&subject, TEMPORAL, &catalogue)? {
        if let Some(start) = store.objects(&period, START, &catalogue)?.first() {
            let until = if possible {
                store
                    .objects(&period, END, &catalogue)?
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

/// The catalogue's name, once a pass.
pub fn catalogue(store: &Store, memo: &mut Memo) -> Result<String, Error> {
    if let Some(name) = &memo.catalogue {
        return Ok(name.clone());
    }
    let name = store
        .catalogue()?
        .ok_or_else(|| Error::Catalogue("no graph describes itself as the catalogue".into()))?;
    memo.catalogue = Some(name.clone());
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
