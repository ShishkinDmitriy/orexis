//! LAYING THE GROUND WORLDS: what the agent's own knowledge comes to over each period, one graph per period, in
//! the store a pass stands in — as `agent/planning/lay_ground.py` lays them, and held to its cases.
//!
//! **A FORECAST IS AN ACTION NOBODY TAKES**: a boundary forks the ground standing before it, takes out of the fork
//! every triple under a key what begins there adds to, and adds it (#988). **A BELIEF THAT BEGINS LATER** is laid
//! where it begins and in no ground before it (#987), and a forecast's end takes back what it added of a thing
//! nothing else is believed of. **THE PERIODS COLLAPSE**: a boundary whose ground holds what the one before held is
//! no period. **A GROUND IS WHAT THE SEARCH CAN CHANGE**: before the present is laid, every graph read beside the
//! worlds is cut in two, what a writer can write into a `planning:ChangeableGraph` derived from it (#953). **WHAT
//! IS BUILT IS CLASSIFIED, NOT RETURNED**: each ground is a `planning:GroundGraph` with the stretch it holds over.
//!
//! NOT YET PORTED: the predictor's foresight, the integration of the flows advanced from each ground and the
//! transitions a predicted observation triggers where it arrives (#1000). It is the prediction package's to make,
//! and lands with that package; until then the grounds are laid as Python lays them handed no foresight.

use std::collections::{BTreeMap, BTreeSet, HashSet};

use oxigraph::model::vocab::rdf;
use oxigraph::model::{GraphNameRef, NamedNode, NamedOrBlankNode, Quad, Term, Triple};
use oxsdatatypes::DateTime;
use sha2::{Digest, Sha256};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{instant, isoformat};
use orexis::hash::{digest_of, hash_named_graph};
use orexis::ontology::{BELIEF, DERIVED, FORECAST, ONTOLOGY, RECORD};
use orexis::store::{Store, Within, iri};

use crate::footprint::{self, Pattern, read_by_transitions};
use crate::ontology::{CHANGEABLE_GRAPH, GROUND_GRAPH, POSSIBLE_GRAPH};
use crate::world_at::named;

const PROV_DERIVED: &str = "http://www.w3.org/ns/prov#wasDerivedFrom";

/// What a step in flight changes where it lands — the Planner's to say, off the plan it published: what it
/// retracts and what it adds, at its landing.
#[derive(Clone, Debug)]
pub struct Landed {
    pub at: DateTime,
    pub retracts: Vec<Triple>,
    pub adds: Vec<Triple>,
}

/// What the grounds are laid with, each the Planner's to say: what a world is identified by (`within`, `None`
/// hashing whole and laying every belief ahead), the instants steps in flight land at and what each changes there,
/// and the scope's actions (`None` meaning every action the store holds).
#[derive(Clone, Debug, Default)]
pub struct Laying<'a> {
    pub within: Option<&'a BTreeSet<String>>,
    pub landings: &'a [DateTime],
    pub landed: &'a [Landed],
    pub actions: Option<&'a BTreeSet<String>>,
}

/// THE CHANGEABLE PART CUT FROM EVERY FORECAST.
const FORECAST_PIECES_Q: &str = "
SELECT ?piece WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                                   ?piece a planning:ChangeableGraph ; prov:wasDerivedFrom ?source . ?source a orexis:ForecastGraph } }";

/// THE CHANGEABLE PART OF EVERY FORECAST THAT ENDS AFTER `$now`, and when.
const PIECES_ENDING_Q: &str = "
SELECT ?piece ?end WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?piece a planning:ChangeableGraph ; prov:wasDerivedFrom ?source .
               ?source a orexis:ForecastGraph ; dcterms:temporal/orexis:end ?end . FILTER(?end > $now) } }
ORDER BY ?end ?piece";

/// THE CHANGEABLE PART OF EVERY BELIEF THAT BEGINS AFTER `$now`, the graph it was cut from and when.
const PIECES_AHEAD_Q: &str = "
SELECT ?piece ?source ?start WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?piece a planning:ChangeableGraph ; prov:wasDerivedFrom ?source .
               ?source dcterms:temporal/orexis:start ?start . FILTER(?start > $now) } }
ORDER BY ?start ?piece";

/// EVERY GRAPH CUT BY THE PATTERNS ASKED NOW, and saying which a graph was cut by.
const CUT_BY_Q: &str = "SELECT ?g WHERE { GRAPH $cat { ?g planning:cutBy $by } }";
const CUT_U: &str = "DELETE { GRAPH $cat { $g planning:cutBy ?was } } INSERT { GRAPH $cat { $g planning:cutBy $by } }
WHERE { OPTIONAL { GRAPH $cat { $g planning:cutBy ?was } } }";

/// EVERY CHANGEABLE GRAPH AND THE GRAPH IT WAS CUT FROM.
const CUT_Q: &str = "
SELECT ?piece ?source WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
  ?piece a planning:ChangeableGraph . OPTIONAL { ?piece prov:wasDerivedFrom ?source } } }";

/// EVERY BELIEF WHOSE PERIOD BEGINS AFTER `$now`.
const BELIEFS_AHEAD_Q: &str = "
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g a orexis:BeliefGraph ; dcterms:temporal/orexis:start ?start . FILTER(?start > $now) } }
ORDER BY ?g";

/// WHAT A BOUNDARY TAKES OUT OF THE GROUND IT MAKES: every triple under a key something there adds to.
const SUPERSEDE_U: &str =
    "DELETE { GRAPH $state { ?s ?p ?o } } WHERE { GRAPH $state { ?s ?p ?o } VALUES (?s ?p) { $keys } }";

/// THE VERDICTS ABOUT A GROUND, with the violation rows hanging off each.
const UNWEIGH_U: &str = "
DELETE { GRAPH ?cat { ?x ?p ?o . ?v ?vp ?vo } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                      ?x a planning:Weighing ; planning:weighs $world ; ?p ?o .
                      OPTIONAL { ?x planning:violation ?v . ?v ?vp ?vo } } }";

/// Build one ground world per period the agent can see, classified with its stretch; the graphs made, earliest
/// first. In place: it lays the grounds into whichever store it is handed.
pub fn lay_ground(store: &Store, now: DateTime, laying: &Laying<'_>) -> Result<Vec<String>, Error> {
    //  WHAT A BELIEF AHEAD IS LAID FOR: some text of the pass reads it, or some transition does.
    let gate = match laying.within {
        None => None,
        Some(within) => read_by_transitions(store)?.map(|read| within | &read),
    };
    split(store, laying.actions, now, gate.as_ref())?;
    let ahead = foreseen(store, now)?;
    let boundaries = ahead.len();
    let here = present(store, now)?;
    let mut ground = Ground {
        store,
        within: laying.within,
        landed: laying.landed,
        marks: marked(store, &here, laying.within)?,
        made: vec![here.clone()],
        here,
        opened: vec![now],
        landing: laying.landings.iter().copied().filter(|at| *at > now).collect(),
        ending: Vec::new(),
        alone: HashSet::new(),
    };
    for (at, piece) in ending(store, now)? {
        match ground.ending.iter_mut().find(|(t, _)| *t == at) {
            Some((_, pieces)) => pieces.push(piece),
            None => ground.ending.push((at, vec![piece])),
        }
    }
    if !ground.ending.is_empty() {
        ground.alone = foreseen_alone(store)?;
    }
    let ends: Vec<DateTime> = ground.ending.iter().map(|(at, _)| *at).collect();
    for (at, group) in by_instant(ahead, &ground.landing, &ends) {
        if at <= now {
            continue;
        }
        let mut added = Vec::new();
        for (piece, _) in &group {
            added.extend(store.triples(piece)?);
        }
        if added.is_empty() && !ground.landing.contains(&at) && !ends.contains(&at) {
            //  A boundary that changes nothing is not a period — an early-out, not a guard.
            continue;
        }
        ground.lay(at, added)?;
    }
    store.classify(
        &ground.here,
        GROUND_GRAPH,
        DERIVED,
        None,
        ground.opened.last().copied(),
        None,
    )?;
    log::debug!(
        "{} ground world(s) over {} boundar(ies) ahead",
        ground.made.len(),
        boundaries
    );
    Ok(ground.made)
}

/// The grounds as they are being laid: the one standing and what it is told apart by, and what each boundary
/// brings.
struct Ground<'a> {
    store: &'a Store,
    within: Option<&'a BTreeSet<String>>,
    landed: &'a [Landed],
    here: String,
    marks: String,
    made: Vec<String>,
    opened: Vec<DateTime>,
    landing: Vec<DateTime>,
    ending: Vec<(DateTime, Vec<String>)>,
    alone: HashSet<NamedOrBlankNode>,
}

impl Ground<'_> {
    /// One ground at `at`, forked from the one standing: `added` laid superseding by key, with what every step
    /// landing here changes — and kept only where it differs from the one before, or lands a step.
    fn lay(&mut self, at: DateTime, mut added: Vec<Triple>) -> Result<(), Error> {
        let store = self.store;
        let mut retracted: Vec<Triple> = Vec::new();
        for change in self.landed.iter().filter(|l| l.at == at) {
            added.extend(change.adds.iter().cloned());
            retracted.extend(change.retracts.iter().cloned());
        }
        //  WHAT A FORECAST ENDING HERE ADDED, and nothing here adds again, goes with it.
        for (_, pieces) in self.ending.iter().filter(|(t, _)| *t == at) {
            for piece in pieces {
                retracted.extend(
                    store
                        .triples(piece)?
                        .into_iter()
                        .filter(|t| self.alone.contains(&t.subject)),
                );
            }
        }
        //  EVERYTHING BEGINNING AT ONE INSTANT IS ONE WORLD CHANGE, each retraction read against the ground
        //  standing before the instant.
        let there = fork(store, &self.here, &name(at), &added)?;
        let kept: HashSet<&Triple> = added.iter().collect();
        let into = named(&there)?;
        let gone: Vec<Quad> = retracted
            .iter()
            .filter(|t| !kept.contains(t))
            .map(|t| t.clone().in_graph(into.clone()))
            .collect();
        store.remove_all(&gone)?;
        let mark = marked(store, &there, self.within)?;
        if mark == self.marks && !self.landing.contains(&at) {
            //  THE SAME GROUND UNDER ANOTHER NAME: this instant is not a period of its own.
            return store.forget_graph(&there, Some(BELIEF));
        }
        //  THE ONE BEFORE IT ENDS HERE, classified when its successor arrives.
        store.classify(
            &self.here,
            GROUND_GRAPH,
            DERIVED,
            None,
            self.opened.last().copied(),
            Some(at),
        )?;
        self.made.push(there.clone());
        self.opened.push(at);
        self.here = there;
        self.marks = mark;
        Ok(())
    }
}

/// Every boundary ahead of `now` — the instant, the changeable part laid there and the graph it was cut from —
/// earliest first.
fn foreseen(store: &Store, now: DateTime) -> Result<Vec<(DateTime, String, String)>, Error> {
    let text = bind(PIECES_AHEAD_Q, &[("now", orexis::store::instant(now))])?;
    let mut out = Vec::new();
    for row in store.rows(&text, &[])? {
        if let (Some(piece), Some(source), Some(start)) =
            (iri(&row, "piece"), iri(&row, "source"), lexical(&row, "start"))
        {
            out.push((start?, piece, source));
        }
    }
    out.sort_by(|a, b| {
        a.0.partial_cmp(&b.0)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| (&a.1, &a.2).cmp(&(&b.1, &b.2)))
    });
    Ok(out)
}

/// Every forecast's end ahead of `now` — the instant, and the changeable part cut from it — earliest first.
fn ending(store: &Store, now: DateTime) -> Result<Vec<(DateTime, String)>, Error> {
    let text = bind(PIECES_ENDING_Q, &[("now", orexis::store::instant(now))])?;
    let mut out = Vec::new();
    for row in store.rows(&text, &[])? {
        if let (Some(piece), Some(end)) = (iri(&row, "piece"), lexical(&row, "end")) {
            out.push((end?, piece));
        }
    }
    out.sort_by(|a, b| {
        a.0.partial_cmp(&b.0)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| a.1.cmp(&b.1))
    });
    Ok(out)
}

fn lexical(row: &orexis::store::Row, variable: &str) -> Option<Result<DateTime, Error>> {
    match row.get(variable)? {
        Term::Literal(l) => Some(instant(l.value())),
        _ => None,
    }
}

/// Every subject nothing but a forecast says anything of, which a forecast's end may take back whole.
fn foreseen_alone(store: &Store) -> Result<HashSet<NamedOrBlankNode>, Error> {
    let mut forecasts: BTreeSet<String> = store.graphs_of(&[FORECAST], &Within::default())?.into_iter().collect();
    forecasts.extend(
        store
            .rows(FORECAST_PIECES_Q, &[])?
            .iter()
            .filter_map(|r| iri(r, "piece")),
    );
    let mut aside = forecasts.clone();
    aside.extend(store.graphs_of(&[GROUND_GRAPH, POSSIBLE_GRAPH], &Within::default())?);
    aside.extend(store.catalogue()?);
    let mut told = HashSet::new();
    for graph in &forecasts {
        told.extend(store.quads(graph)?.into_iter().map(|q| q.subject));
    }
    let mut out = HashSet::new();
    for subject in told {
        let mut elsewhere = false;
        for quad in store
            .engine()
            .quads_for_pattern(Some(subject.as_ref()), None, None, None)
        {
            let quad = quad.map_err(|e| Error::Evaluation(e.to_string()))?;
            let aside_it = match quad.graph_name.as_ref() {
                GraphNameRef::NamedNode(n) => aside.contains(n.as_str()),
                _ => false,
            };
            if !aside_it {
                elsewhere = true;
                break;
            }
        }
        if !elsewhere {
            out.insert(subject);
        }
    }
    Ok(out)
}

/// What is laid, grouped by the instant it applies, earliest first — every landing and every forecast's end a
/// boundary too, with what applies there or nothing.
fn by_instant(
    ahead: Vec<(DateTime, String, String)>,
    landings: &[DateTime],
    endings: &[DateTime],
) -> Vec<(DateTime, Vec<(String, String)>)> {
    let mut out: Vec<(DateTime, Vec<(String, String)>)> = Vec::new();
    for at in landings.iter().chain(endings) {
        if !out.iter().any(|(t, _)| t == at) {
            out.push((*at, Vec::new()));
        }
    }
    for (at, piece, source) in ahead {
        match out.iter_mut().find(|(t, _)| *t == at) {
            Some((_, group)) => group.push((piece, source)),
            None => out.push((at, vec![(piece, source)])),
        }
    }
    out.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
    out
}

/// The agent's state as it stands, as a ground of its own: every changeable graph cut, but what begins later.
fn present(store: &Store, now: DateTime) -> Result<String, Error> {
    let name = name(now);
    relaid(store, &name)?;
    let text = bind(PIECES_AHEAD_Q, &[("now", orexis::store::instant(now))])?;
    let ahead: HashSet<String> = store.rows(&text, &[])?.iter().filter_map(|r| iri(r, "piece")).collect();
    let into = named(&name)?;
    for source in store.graphs_of(&[CHANGEABLE_GRAPH], &Within::default())? {
        if ahead.contains(&source) {
            continue;
        }
        store.add(
            store
                .quads(&source)?
                .into_iter()
                .map(|q| Quad::new(q.subject, q.predicate, q.object, into.clone())),
        )?;
    }
    Ok(name)
}

/// Cut out of every graph a search reads beside its worlds what the search can change, each into a
/// `planning:ChangeableGraph` derived from it. A cut stands while its source and its patterns do.
fn split(
    store: &Store,
    actions: Option<&BTreeSet<String>>,
    at: DateTime,
    gate: Option<&BTreeSet<String>>,
) -> Result<Vec<String>, Error> {
    let cat = store
        .catalogue()?
        .ok_or_else(|| Error::Catalogue("no graph describes itself as the catalogue".into()))?;
    let patterns = match footprint::changeable(store, actions, at)? {
        Some(mut patterns) => {
            patterns.extend(predicted(store, at, gate)?);
            Some(footprint::sorted(patterns))
        }
        None => None,
    };
    let by = signature(patterns.as_deref());
    let mut pieces: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for row in store.rows(CUT_Q, &[])? {
        let Some(piece) = iri(&row, "piece") else { continue };
        match iri(&row, "source") {
            Some(source) if classified(store, &source)? => pieces.entry(source).or_default().push(piece),
            _ => store.forget_graph(&piece, Some(BELIEF))?,
        }
    }
    let defining: HashSet<String> = store.graphs_of(&[ONTOLOGY], &Within::default())?.into_iter().collect();
    let by_literal = Value::Term(oxigraph::model::Literal::new_simple_literal(&by).into());
    let text = bind(
        CUT_BY_Q,
        &[("cat", Value::raw(format!("<{cat}>"))), ("by", by_literal.clone())],
    )?;
    let standing: HashSet<String> = store.rows(&text, &[])?.iter().filter_map(|r| iri(r, "g")).collect();
    let (catalogue, derived) = (named(&cat)?, named(PROV_DERIVED)?);
    let mut made = Vec::new();
    for graph in store.graphs_of(&[BELIEF, RECORD], &Within::default())? {
        if defining.contains(&graph) || standing.contains(&graph) {
            continue;
        }
        let g = named(&graph)?;
        for piece in pieces.get(&graph).into_iter().flatten() {
            store.add(
                store
                    .quads(piece)?
                    .into_iter()
                    .map(|q| Quad::new(q.subject, q.predicate, q.object, g.clone())),
            )?;
            store.forget_graph(piece, Some(BELIEF))?;
        }
        store.update(&bind(
            CUT_U,
            &[
                ("cat", Value::raw(format!("<{cat}>"))),
                ("g", Value::iri(graph.clone())),
                ("by", by_literal.clone()),
            ],
        )?)?;
        let cut: Vec<Quad> = match &patterns {
            None => store.quads(&graph)?,
            Some(patterns) => {
                let mut out: Vec<Quad> = Vec::new();
                for pattern in patterns {
                    let predicate = named(&pattern.predicate)?;
                    for quad in store.engine().quads_for_pattern(
                        None,
                        Some(predicate.as_ref()),
                        pattern.object.as_ref().map(Term::as_ref),
                        Some(GraphNameRef::NamedNode(g.as_ref())),
                    ) {
                        let quad = quad.map_err(|e| Error::Evaluation(e.to_string()))?;
                        if !out.contains(&quad) {
                            out.push(quad);
                        }
                    }
                }
                out
            }
        };
        if cut.is_empty() {
            continue;
        }
        let piece = format!("{graph}.changeable");
        let into = named(&piece)?;
        store.remove_all(&cut)?;
        store.add(
            cut.into_iter()
                .map(|q| Quad::new(q.subject, q.predicate, q.object, into.clone())),
        )?;
        store.classify(&piece, CHANGEABLE_GRAPH, DERIVED, None, None, None)?;
        store.add([Quad::new(into.clone(), derived.clone(), g.clone(), catalogue.clone())])?;
        made.push(piece);
    }
    log::debug!(
        "{} changeable graph(s) cut over {} pattern(s), {} standing",
        made.len(),
        patterns.as_ref().map_or("every".to_string(), |p| p.len().to_string()),
        standing.len()
    );
    Ok(made)
}

/// The digest of a set of patterns, as the cut a source's row says it was made by.
fn signature(patterns: Option<&[Pattern]>) -> String {
    let text = match patterns {
        None => "every".to_string(),
        Some(patterns) => patterns
            .iter()
            .map(|p| format!("{} {}", p.predicate, p.spelled().unwrap_or_default()))
            .collect::<Vec<_>>()
            .join("\n"),
    };
    let hex: String = Sha256::digest(text.as_bytes())
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect();
    format!("sha256:{hex}")
}

/// What every belief beginning after `now` that something reads writes, as patterns: each predicate it adds, a
/// type with its class. `gate` is what is read; `None` reads anything, and lays every belief ahead.
fn predicted(store: &Store, now: DateTime, gate: Option<&BTreeSet<String>>) -> Result<Vec<Pattern>, Error> {
    let text = bind(BELIEFS_AHEAD_Q, &[("now", orexis::store::instant(now))])?;
    let ahead: Vec<String> = store.rows(&text, &[])?.iter().filter_map(|r| iri(r, "g")).collect();
    let mut read: Vec<Vec<String>> = Vec::new();
    for g in &ahead {
        let mut graphs = vec![g.clone()];
        graphs.extend(store.revisions_of(&[g], BELIEF)?);
        let whole = whole(store, graphs)?;
        let is_read = match gate {
            None => true,
            Some(gate) => reads_any(store, &whole, gate)?,
        };
        if is_read {
            read.push(whole);
        }
    }
    log::debug!("{} belief(s) ahead, {} read by something", ahead.len(), read.len());
    let mut seen = HashSet::new();
    let mut out = Vec::new();
    for graph in read.into_iter().flatten() {
        if !seen.insert(graph.clone()) {
            continue;
        }
        for quad in store.quads(&graph)? {
            let object = match &quad.object {
                Term::NamedNode(class) if quad.predicate.as_ref() == rdf::TYPE => Some(Term::from(class.clone())),
                _ => None,
            };
            out.push(Pattern {
                predicate: quad.predicate.as_str().to_string(),
                object,
            });
        }
    }
    Ok(out)
}

/// Whether some text reads a triple of `graphs`: its predicate is in `within`, or it is a type fact whose class is.
fn reads_any(store: &Store, graphs: &[String], within: &BTreeSet<String>) -> Result<bool, Error> {
    for graph in graphs {
        for quad in store.quads(graph)? {
            if within.contains(quad.predicate.as_str()) {
                return Ok(true);
            }
            if quad.predicate.as_ref() == rdf::TYPE
                && let Term::NamedNode(class) = &quad.object
                && within.contains(class.as_str())
            {
                return Ok(true);
            }
        }
    }
    Ok(false)
}

/// `graphs` and every changeable graph cut from one of them: each as it stood before the cut.
fn whole(store: &Store, mut graphs: Vec<String>) -> Result<Vec<String>, Error> {
    let wanted: HashSet<String> = graphs.iter().cloned().collect();
    for row in store.rows(CUT_Q, &[])? {
        if iri(&row, "source").is_some_and(|s| wanted.contains(&s))
            && let Some(piece) = iri(&row, "piece")
        {
            graphs.push(piece);
        }
    }
    Ok(graphs)
}

/// Whether the catalogue still says what `graph` is.
fn classified(store: &Store, graph: &str) -> Result<bool, Error> {
    let cat = store.catalogue()?.unwrap_or_default();
    store.ask(&format!("ASK {{ GRAPH <{cat}> {{ <{graph}> a ?kind }} }}"), &[])
}

/// Write the ground's hash on its row, within what is read where that is said, and answer the digest of everything
/// it holds — what a period is told from the one before it by.
fn marked(store: &Store, ground: &str, within: Option<&BTreeSet<String>>) -> Result<String, Error> {
    match within {
        None => hash_named_graph(store, ground, None),
        Some(within) => {
            hash_named_graph(store, ground, Some(within))?;
            digest_of(store, ground, None)
        }
    }
}

/// The ground one boundary past `parent`: its facts, less whatever stood under a key what is added there adds to,
/// plus what is added — and which ground it came from, on its row.
fn fork(store: &Store, parent: &str, name: &str, added: &[Triple]) -> Result<String, Error> {
    relaid(store, name)?;
    let mut keys: Vec<(&NamedNode, &NamedNode)> = added
        .iter()
        .filter_map(|t| match &t.subject {
            NamedOrBlankNode::NamedNode(s) => Some((s, &t.predicate)),
            _ => None,
        })
        .collect();
    keys.sort();
    keys.dedup();
    let supersede = if keys.is_empty() {
        Vec::new()
    } else {
        let keys = keys
            .iter()
            .map(|(s, p)| format!("(<{}> <{}>)", s.as_str(), p.as_str()))
            .collect::<Vec<_>>()
            .join(" ");
        vec![bind(
            SUPERSEDE_U,
            &[("state", Value::raw(format!("<{name}>"))), ("keys", Value::raw(keys))],
        )?]
    };
    store.fork(parent, name, added, &supersede)?;
    let cat = store.catalogue()?.unwrap_or_default();
    store.add([Quad::new(
        named(name)?,
        named(PROV_DERIVED)?,
        named(parent)?,
        named(&cat)?,
    )])?;
    Ok(name.to_string())
}

/// Take back a ground standing under the name this pass is about to lay under — its facts, its row and every
/// weighing of it: the imaginarium outlives the pass, and a ground is named for its instant.
fn relaid(store: &Store, name: &str) -> Result<(), Error> {
    store.forget_graph(name, Some(BELIEF))?;
    store.update(&bind(UNWEIGH_U, &[("world", Value::iri(name))])?)
}

/// A ground's name, for eyes: the instant it opens at.
fn name(at: DateTime) -> String {
    let stamp = isoformat(at).replace(':', "").replace('+', "p");
    format!("http://example.org/orexis/graph/ground/{stamp}")
}

#[cfg(test)]
mod tests {
    //! `lay_ground`, held to `agent/planning/tests/lay_ground/`'s cases as `test_lay_ground.py` holds the Python act,
    //! and to its tests beside them. The cases laid with the predictor's foresight, `tests/foreseen/`, come with the
    //! prediction package.

    use std::collections::{BTreeMap, HashSet};
    use std::path::PathBuf;

    use oxigraph::model::vocab::xsd;
    use oxigraph::model::{Literal, NamedNode};
    use oxsdatatypes::DayTimeDuration;

    use orexis::snapshots;

    use super::*;

    fn cases() -> PathBuf {
        snapshots::tree().join("planning/tests/lay_ground")
    }

    const T: &str = "http://example.org/test#";

    #[test]
    fn lay_ground_lays_the_grounds_the_diff_says() {
        for case in snapshots::cases_in(&cases()) {
            let store = snapshots::stand_in(&case);
            lay_ground(&store, snapshots::now(), &Laying::default()).unwrap();
            snapshots::held_to_diff(&case, &store, "lay_ground");
        }
    }

    #[test]
    fn every_case_is_read_and_no_diff_is_orphaned() {
        snapshots::all_read(&cases(), 3);
    }

    fn within(locals: &[&str]) -> BTreeSet<String> {
        locals.iter().map(|l| format!("{T}{l}")).collect()
    }

    fn hash_of(store: &Store, ground: &str) -> String {
        let text =
            format!("SELECT ?h WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{ground}> orexis:hash ?h }} }}");
        orexis::store::value(&store.rows(&text, &[]).unwrap()[0], "h").unwrap()
    }

    #[test]
    fn a_forecast_read_by_nothing_lays_no_ground_and_one_read_is_a_period_by_everything_it_holds() {
        let case = cases().join("two_stretches_in_one_scope_are_two_grounds.trig");
        let store = snapshots::stand_in(&case);
        let level = within(&["level"]);
        let grounds = lay_ground(
            &store,
            snapshots::now(),
            &Laying {
                within: Some(&level),
                ..Laying::default()
            },
        )
        .unwrap();
        assert_eq!(grounds.len(), 2, "the temperature is read by nothing");
        assert_ne!(
            hash_of(&store, &grounds[0]),
            hash_of(&store, &grounds[1]),
            "the level dropped, which is read"
        );
        let store = snapshots::stand_in(&case);
        let both = within(&["level", "temperature"]);
        let grounds = lay_ground(
            &store,
            snapshots::now(),
            &Laying {
                within: Some(&both),
                ..Laying::default()
            },
        )
        .unwrap();
        assert_eq!(grounds.len(), 3);
    }

    #[test]
    fn a_belief_ahead_that_no_text_reads_lays_no_ground() {
        let case = cases().join("a_forecast_holding_later_crosses_whole.trig");
        let laid = lay_ground(&snapshots::stand_in(&case), snapshots::now(), &Laying::default()).unwrap();
        assert_eq!(laid.len(), 2, "read anything: a ground at three");
        let store = snapshots::stand_in(&case);
        let level = within(&["level"]);
        let laid = lay_ground(
            &store,
            snapshots::now(),
            &Laying {
                within: Some(&level),
                ..Laying::default()
            },
        )
        .unwrap();
        assert_eq!(laid.len(), 1, "the warmth is read by nothing");
        assert!(
            store
                .graphs_of(&[CHANGEABLE_GRAPH], &Within::default())
                .unwrap()
                .is_empty(),
            "and nothing of the forecast was cut"
        );
    }

    fn node(local: &str) -> NamedNode {
        NamedNode::new(format!("{T}{local}")).unwrap()
    }

    fn integer(n: &str) -> Term {
        Literal::new_typed_literal(n, xsd::INTEGER).into()
    }

    #[test]
    fn the_ground_where_a_step_in_flight_lands_holds_the_steps_change() {
        let store = snapshots::stand_in(&cases().join("two_stretches_in_one_scope_are_two_grounds.trig"));
        let tank = node("tank1");
        let landing = snapshots::now()
            .checked_add_day_time_duration(DayTimeDuration::new(900))
            .unwrap();
        let landed = [Landed {
            at: landing,
            retracts: vec![Triple::new(tank.clone(), node("temperature"), integer("20"))],
            adds: vec![
                Triple::new(tank.clone(), node("level"), integer("15")),
                Triple::new(tank.clone(), node("valve"), node("open")),
            ],
        }];
        let laying = Laying {
            landings: &[landing],
            landed: &landed,
            ..Laying::default()
        };
        let grounds = lay_ground(&store, snapshots::now(), &laying).unwrap();
        let facts = |ground: &str| -> BTreeSet<(String, String)> {
            store
                .triples(ground)
                .unwrap()
                .into_iter()
                .filter(|t| t.subject == tank.clone().into())
                .map(|t| {
                    let p = t.predicate.as_str().rsplit('#').next().unwrap().to_string();
                    let o = match &t.object {
                        Term::NamedNode(n) => n.as_str().to_string(),
                        Term::Literal(l) => l.value().to_string(),
                        other => other.to_string(),
                    };
                    (p, o)
                })
                .collect()
        };
        let pairs = |p: &[(&str, &str)]| -> BTreeSet<(String, String)> {
            p.iter().map(|(a, b)| (a.to_string(), b.to_string())).collect()
        };
        let open = format!("{T}open");
        assert_eq!(grounds.len(), 4);
        assert_eq!(
            facts(&grounds[0]),
            pairs(&[("level", "20"), ("temperature", "20")]),
            "the present holds what the world has shown"
        );
        assert_eq!(
            facts(&grounds[1]),
            pairs(&[("level", "15"), ("valve", &open)]),
            "where the step lands, its change"
        );
        assert_eq!(
            facts(&grounds[2]),
            pairs(&[("level", "5"), ("valve", &open)]),
            "inherited, and superseded again by key"
        );
        assert_eq!(
            facts(&grounds[3]),
            pairs(&[("level", "5"), ("valve", &open), ("temperature", "40")])
        );
    }

    const OPENING: &str = r#"
PREFIX : <http://example.org/test#>
PREFIX orexis: <http://example.org/orexis#>
PREFIX planning: <http://example.org/orexis/planning#>
PREFIX belief: <http://example.org/orexis/belief#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
INSERT DATA { GRAPH :actions {
  :open a orexis:Action ; orexis:takes :tank ;
    planning:effect [ a planning:Effect ; sh:rule [ a belief:Transition ; belief:update """PREFIX : <http://example.org/test#>
      DELETE { $tank :lid :closed } INSERT { ?tank :lid :open } WHERE { $tank :lid :closed . BIND($tank AS ?tank) }""" ] ] .
} }"#;

    /// What every graph but the catalogue holds, by name.
    fn held(store: &Store) -> BTreeMap<String, HashSet<Triple>> {
        let cat = store.catalogue().unwrap().unwrap();
        let mut out: BTreeMap<String, HashSet<Triple>> = BTreeMap::new();
        for graph in store.graph_names().unwrap() {
            if graph != cat {
                out.insert(graph.clone(), store.triples(&graph).unwrap().into_iter().collect());
            }
        }
        out
    }

    #[test]
    fn an_action_added_makes_what_it_writes_changeable_and_nothing_else() {
        let store = snapshots::stand_in(&snapshots::tree().join("planning/tests/plans/a_low_tank_is_filled.trig"));
        let world = format!("{T}world");
        let lid = Triple::new(node("tank1"), node("lid"), node("closed"));
        store
            .add([lid.clone().in_graph(NamedNode::new(&world).unwrap())])
            .unwrap();
        let laid = lay_ground(&store, snapshots::now(), &Laying::default()).unwrap();
        let [ground] = laid.as_slice() else {
            panic!("one ground: {laid:?}")
        };
        let before = held(&store);
        assert!(
            before[&world].contains(&lid) && !before[ground].contains(&lid),
            "no writer writes a lid"
        );

        store.update(OPENING).unwrap();
        assert_eq!(
            lay_ground(&store, snapshots::now(), &Laying::default()).unwrap(),
            vec![ground.clone()]
        );
        let after = held(&store);

        let piece = format!("{world}.changeable");
        assert!(
            !before.contains_key(&piece) && after[&piece] == HashSet::from([lid.clone()]),
            "the lid is cut out"
        );
        let mut less = before[&world].clone();
        less.remove(&lid);
        assert_eq!(after[&world], less, "and out of the world");
        let mut more = before[ground].clone();
        more.insert(lid.clone());
        assert_eq!(after[ground], more, "and the present is laid with it");
        let actions = format!("{T}actions");
        assert!(after[&actions].is_superset(&before[&actions]) && after[&actions] != before[&actions]);
        let untouched: Vec<&String> = before
            .keys()
            .filter(|g| ![&world, ground, &actions].contains(g))
            .collect();
        assert!(!untouched.is_empty());
        let mut names: BTreeSet<&String> = after.keys().collect();
        names.remove(&piece);
        assert_eq!(names, before.keys().collect::<BTreeSet<_>>());
        for g in untouched {
            assert_eq!(after[g], before[g], "{g} changed");
        }
    }
}
