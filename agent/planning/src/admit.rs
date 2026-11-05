//! WHAT ONE WORLD ADMITS — a candidate per action per legal filling — written as the edges that leave it, as
//! `agent/planning/admit.py` writes them: an action's precondition is a SELECT projecting the parameters it
//! takes, so its ROWS are the candidates. Every action of the scope is asked (`only`), a filling naming another
//! scope's member is that scope's (`elsewhere`), and a wait is admitted where a ground whose identity differs is
//! laid after the world's. Idempotent by FILLING, not by name; the candidates are numbered by the store's mint
//! counter in a fixed order, by action and then by filling, so two traces of one search compare.

use std::collections::{BTreeSet, HashSet};

use oxigraph::model::{Literal, NamedNode, Quad, Term};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{ACTION, GRAPH_PREFIX};
use orexis::store::{Store, Within, iri, value};

use crate::Memo;
use crate::memo::{Declared, Filling};
use crate::next_ground::next_ground;
use crate::ontology::{CANDIDATE, FILLS, FROM, MINTED, WAIT};
use crate::world_at::{Asking, catalogue, named, world_at};

/// Where a possible world's readings sit, under the same root as every other graph.
pub fn possible() -> String {
    format!("{GRAPH_PREFIX}possible/")
}

const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";

/// WHETHER THE STORE HOLDS THE WAIT, among the actions.
const WAIT_Q: &str = "SELECT ?w WHERE { $wait a orexis:Action BIND($wait AS ?w) } LIMIT 1";

/// Each action with its precondition and the parameters it declares. `STR(?takes)` because `GROUP_CONCAT` over
/// an IRI binds nothing in this engine.
const ACTIONS_Q: &str =
    "SELECT ?action ?precondition (GROUP_CONCAT(DISTINCT STR(?takes); separator=\" \") AS ?takes_) WHERE {
  ?action a orexis:Action ; planning:precondition ?precondition .
  OPTIONAL { ?action orexis:takes ?takes }
} GROUP BY ?action ?precondition";

/// WHAT THE WORLD ALREADY ADMITS: each candidate leaving it, the action it fills and every parameter.
const ADMITTED_Q: &str = "
SELECT ?c ?action ?p ?v WHERE {
  GRAPH $cat { ?c a planning:Candidate ; planning:from $world ; planning:fills ?action .
               OPTIONAL { ?c ?p ?v . FILTER(?p NOT IN (planning:from, planning:fills, planning:minted, rdf:type)) } } }";

/// THE HIGHEST MINT NUMBER IN THE STORE, candidate or world.
const MINTED_Q: &str = "SELECT (MAX(?m) AS ?n) WHERE { GRAPH $cat { ?w planning:minted ?m } }";

/// Which actions a scope asks, and which values are another scope's.
#[derive(Clone, Debug, Default)]
pub struct Scope<'a> {
    pub only: Option<&'a HashSet<String>>,
    pub elsewhere: Option<&'a HashSet<String>>,
}

/// Write every candidate `world` admits for the self.
pub fn admit(store: &Store, world: &str, scope: &Scope<'_>, memo: &mut Memo) -> Result<(), Error> {
    let graphs = world_at(store, Some(world), &Asking::default(), memo)?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let cat = catalogue(store, memo)?;
    let mut admitted: std::collections::BTreeMap<(String, String), BTreeSet<(String, String)>> = Default::default();
    let text = bind(
        ADMITTED_Q,
        &[("cat", Value::iri(cat.clone())), ("world", Value::iri(world))],
    )?;
    for r in store.rows(&text, &[])? {
        let (Some(c), Some(action)) = (iri(&r, "c"), iri(&r, "action")) else {
            continue;
        };
        let held = admitted.entry((c, action)).or_default();
        if let (Some(p), Some(v)) = (value(&r, "p"), value(&r, "v")) {
            held.insert((p, v));
        }
    }
    let already: HashSet<(String, BTreeSet<(String, String)>)> = admitted
        .into_iter()
        .map(|((_, action), filling)| (action, filling))
        .collect();
    let in_scope = |action: &str| scope.only.is_none_or(|only| only.contains(action));
    let mut fillings: Vec<(String, Filling)> = Vec::new();
    for declared in actions(store, memo)? {
        if !in_scope(&declared.action) {
            continue;
        }
        let params: Vec<(String, &String)> = {
            let mut by_local: Vec<(String, &String)> = Vec::new();
            for p in &declared.takes {
                let local = local_of(p);
                by_local.retain(|(l, _)| *l != local);
                by_local.push((local, p));
            }
            by_local
        };
        for row in store.rows(&bind(&declared.precondition, &[])?, &graphs)? {
            let mut filling: Filling = params
                .iter()
                .filter_map(|(local, iri)| {
                    let term = row.get(local)?;
                    Some(((*iri).clone(), value(&row, local)?, written(term)))
                })
                .collect();
            filling.sort_by(|a, b| (&a.0, &a.1, a.2.to_string()).cmp(&(&b.0, &b.1, b.2.to_string())));
            let said: BTreeSet<(String, String)> = filling.iter().map(|(p, v, _)| (p.clone(), v.clone())).collect();
            if already.contains(&(declared.action.clone(), said))
                || filling
                    .iter()
                    .any(|(_, v, _)| scope.elsewhere.is_some_and(|e| e.contains(v)))
            {
                continue;
            }
            let candidate = (declared.action.clone(), filling);
            if !fillings.contains(&candidate) {
                fillings.push(candidate);
            }
        }
    }
    if in_scope(WAIT)
        && !already.contains(&(WAIT.to_string(), BTreeSet::new()))
        && waits(store, memo)?
        && next_ground(store, world, memo)?.is_some()
    {
        fillings.push((WAIT.to_string(), Vec::new()));
    }
    if fillings.is_empty() {
        return Ok(());
    }
    let mut minted = match memo.minted {
        Some(n) => n,
        None => {
            let text = bind(MINTED_Q, &[("cat", Value::iri(cat.clone()))])?;
            store
                .rows(&text, &[])?
                .first()
                .and_then(|r| value(r, "n"))
                .and_then(|n| n.parse().ok())
                .unwrap_or(0)
        }
    };
    fillings.sort_by_key(key);
    let (graph, from, world) = (named(&cat)?, named(FROM)?, named(world)?);
    let mut edges = Vec::new();
    for (action, filling) in fillings {
        minted += 1;
        let candidate = named(&format!("{}{minted}.by", possible()))?;
        let quad = |p: NamedNode, o: Term| Quad::new(candidate.clone(), p, o, graph.clone());
        edges.push(quad(named(RDF_TYPE)?, named(CANDIDATE)?.into()));
        edges.push(quad(from.clone(), world.clone().into()));
        edges.push(quad(named(FILLS)?, named(&action)?.into()));
        edges.push(quad(
            named(MINTED)?,
            Literal::new_typed_literal(minted.to_string(), oxigraph::model::vocab::xsd::INTEGER).into(),
        ));
        for (p, _, term) in filling {
            edges.push(quad(named(&p)?, term));
        }
    }
    memo.minted = Some(minted);
    store.add(edges)
}

/// The order fillings are numbered in: by action, then by what they are filled with, as Python sorts the tuples.
fn key((action, filling): &(String, Filling)) -> (String, Vec<(String, String, String)>) {
    (
        action.clone(),
        filling
            .iter()
            .map(|(p, v, t)| (p.clone(), v.clone(), t.to_string()))
            .collect(),
    )
}

/// The actions the store declares, sorted by action, once a pass.
fn actions(store: &Store, memo: &mut Memo) -> Result<Vec<Declared>, Error> {
    if let Some(known) = &memo.actions {
        return Ok(known.clone());
    }
    let graphs = store.graphs_of(&[ACTION], &Within::default())?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let mut out: Vec<Declared> = store
        .rows(ACTIONS_Q, &graphs)?
        .iter()
        .filter_map(|r| {
            Some(Declared {
                action: iri(r, "action")?,
                precondition: value(r, "precondition")?,
                takes: value(r, "takes_")
                    .unwrap_or_default()
                    .split_whitespace()
                    .map(String::from)
                    .collect(),
            })
        })
        .collect();
    out.sort_by(|a, b| a.action.cmp(&b.action));
    memo.actions = Some(out.clone());
    Ok(out)
}

/// Whether the store holds the wait among its actions, once a pass.
fn waits(store: &Store, memo: &mut Memo) -> Result<bool, Error> {
    if let Some(known) = memo.waits {
        return Ok(known);
    }
    let graphs = store.graphs_of(&[ACTION], &Within::default())?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    let text = bind(WAIT_Q, &[("wait", Value::iri(WAIT))])?;
    let found = !store.rows(&text, &graphs)?.is_empty();
    memo.waits = Some(found);
    Ok(found)
}

/// A parameter's term as the edge writes it: the term the precondition bound, a typed literal kept typed. A
/// blank node is written as a plain literal of its label, as the Python kernel's SPARQL-JSON crossing writes it.
fn written(term: &Term) -> Term {
    match term {
        Term::BlankNode(b) => Literal::new_simple_literal(b.as_str()).into(),
        other => other.clone(),
    }
}

/// An IRI's local part, the name a parameter answers to as a variable and a token.
pub fn local_of(iri: &str) -> String {
    let tail = iri.rsplit('#').next().unwrap_or(iri);
    tail.rsplit('/').next().unwrap_or(tail).to_string()
}

#[cfg(test)]
mod tests;
