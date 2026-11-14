//! THE BELIEF PACKAGE'S PART, as `agent/belief/create.py` makes it: its deliberator, which says by its own `revised`
//! what a pass revised. Started, it revises what the world authored as its state, once, so a fact concluded from
//! where things stand is believed from the first pass; then every belief written, as it is written, beside what the
//! world states and nothing else, and applies the transitions each triggers. Belief links to nothing.
//!
//! WHAT STANDS BESIDE A GRAPH REVISED is the common beliefs alone: never another testimony, and not the agent's own
//! state, which is a transition's premise and `trigger` hands it itself
//! (a-transition-changes-the-state-and-an-inference-only-concludes).
//!
//! A GRAPH WRITTEN MID-ACT is told `wrote` by whoever linked it — the executor, whose writes as the world are revised
//! before its walk goes on, as Python's `runtime.wrote` hands them on at once; a part cannot reach the runtime while
//! it runs.

use oxigraph::model::NamedNode;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::ontology::BELIEF;
use orexis::store::{Store, Within};
use orexis::task::{Handed, Heard, Hears, Package, Task, Turn, Woke};

use crate::Deliberator;
use crate::ontology::{INTO, REVISES, REVISING, REVISING_TRIGGER, REVISION_GRAPH};

const HEARD: usize = 0;
const REVISE: usize = 1;

/// Belief's part: its deliberator, shared with whoever links to it — a clone is the same part, as a linked part holds it.
pub struct Belief {
    beliefs: Store,
    pub deliberator: Deliberator,
}

impl Belief {
    pub fn new(beliefs: &Store, agent: &str) -> Result<Self, Error> {
        Ok(Belief {
            beliefs: beliefs.clone(),
            deliberator: Deliberator::new(beliefs, agent, None)?,
        })
    }

    /// Revise `graphs` beside what the world states and apply the transitions each triggers, now — their revisions
    /// classified `kind`.
    pub fn revise(&mut self, graphs: &[String], kind: &str, at: DateTime) -> Result<(), Error> {
        let stated = self.beliefs.graphs_of(&[BELIEF], &Within::common())?;
        let deliberator = &mut self.deliberator;
        for graph in graphs {
            deliberator.changed(graph, Some(stated.clone()), kind);
        }
        deliberator.deliberate(at)?;
        Ok(())
    }
}

impl Belief {
    /// Revise `graphs` as an activity, triggered by them.
    fn revising(&mut self, graphs: &[String], kind: &str, pass: &mut Turn<'_>) -> Result<(), Error> {
        let triggers: Vec<NamedNode> = graphs.iter().filter_map(|g| NamedNode::new(g.as_str()).ok()).collect();
        let activity = pass.begin(REVISING, &triggers);
        let revised = self.revise(graphs, kind, pass.now);
        pass.end(activity);
        revised
    }
}

inventory::submit! { Package { name: "belief", documents: orexis::documents!("ontology.ttl"), start } }

/// BELIEF'S START: its deliberator made, what the world authored as the agent's state revised, once, and its task,
/// which hears a belief written and its trigger's events.
/// ITS START, which every package this binary holds is given: it joins the agent or declines, by its own reason, and
/// joined, makes its core.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[crate::ontology::DELIBERATOR]).await? {
            return Ok(None);
        }
        make(&handed)
    })
}

fn make(handed: &Handed) -> Result<Option<Task>, Error> {
    let mut belief = Belief::new(&handed.store, &handed.id)?;
    belief.deliberator.watch = handed.events.watch().clone();
    belief.start(handed.clock.now())?;
    let mut hears = handed.events.hears();
    hears.graph(BELIEF, HEARD);
    hears.event(REVISING_TRIGGER, REVISE);
    Ok(Some(Box::pin(task(handed.clone(), belief, hears))))
}

/// BELIEF'S TASK: it waits for a belief written, or an event beneath its trigger, and revises.
async fn task(handed: Handed, mut belief: Belief, mut hears: Hears) -> Result<(), Error> {
    loop {
        let woke = tokio::select! {
            biased;
            _ = handed.stopped() => break,
            woke = hears.next() => woke,
        };
        let Some(woke) = woke else { break };
        let mut turn = handed.turn();
        let wrote = match woke {
            Woke::Graphs(_, graphs) => belief.revising(&graphs, BELIEF, &mut turn).map(|()| Vec::new()),
            Woke::Event(_, event) => belief.heard_event(&event, &mut turn),
        };
        turn.done(wrote)?;
    }
    Ok(())
}

impl Belief {
    fn start(&mut self, now: DateTime) -> Result<(), Error> {
        //  EVERY BELIEF NOT YET REVISED, but the common ones: the world's documents were concluded on at genesis.
        let mut skip = self.beliefs.graphs_of(&[REVISION_GRAPH], &Within::default())?;
        skip.extend(self.beliefs.graphs_of(&[BELIEF], &Within::common())?);
        let mut due = Vec::new();
        for g in self.beliefs.graphs_of(&[BELIEF], &Within::default())? {
            if !skip.contains(&g) && self.beliefs.revisions_of(&[&g], BELIEF)?.is_empty() {
                due.push(g);
            }
        }
        self.revise(&due, BELIEF, now)
    }

    /// What belief's policy does of a trigger: revise each graph it names, its revisions of the kind it names.
    fn heard_event(&mut self, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let graphs: Vec<String> = event.all(REVISES).iter().map(|g| g.as_str().to_string()).collect();
        let Some(kind) = event.named(INTO).map(|k| k.as_str().to_string()) else {
            return Ok(Vec::new());
        };
        if !graphs.is_empty() {
            self.revising(&graphs, &kind, pass)?;
        }
        Ok(Vec::new())
    }
}

#[cfg(test)]
mod tests {
    //! Belief's part, held as `agent/belief/tests/test_create.py` holds it.

    use orexis::ontology::CATALOGUE_GRAPH;
    use orexis::snapshots;

    use super::*;
    use std::sync::{Arc, Mutex};

    fn bare() -> Store {
        let store = Store::new(snapshots::namespaces()).unwrap();
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph }} }}"
            ))
            .unwrap();
        store
    }

    #[test]
    fn its_part_hears_beliefs_written_and_says_each_pass_revised() {
        let store = bare();
        let mut part = Belief::new(&store, "urn:test:me").unwrap();
        let heard = Arc::new(Mutex::new(Vec::new()));
        let into = heard.clone();
        part.deliberator.watch.connect(move |event, _| {
            if let Some(r) = orexis::events::as_of::<crate::deliberator::Revised>(event) {
                into.lock().unwrap().extend(r.graphs.clone());
            }
        });
        part.start(snapshots::now()).unwrap();
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <urn:test:nothing> a orexis:BeliefGraph }} }}"
            ))
            .unwrap();
        part.revise(&["urn:test:nothing".to_string()], BELIEF, snapshots::now())
            .unwrap();
        assert_eq!(
            *heard.lock().unwrap(),
            ["urn:test:nothing"],
            "each pass says what it revised"
        );
    }

    #[test]
    fn a_graph_written_is_revised_beside_the_world_alone() {
        let store = bare();
        let said = [
            (
                "urn:test:world",
                "orexis:BeliefGraph ; orexis:arrivedBy orexis:Asserted",
            ),
            (
                "urn:test:concluded",
                "orexis:BeliefGraph ; orexis:arrivedBy orexis:Derived ; orexis:ownedBy <urn:test:me>",
            ),
            (
                "urn:test:other_reading",
                "orexis:BeliefGraph ; orexis:arrivedBy orexis:Received ; orexis:ownedBy <urn:test:me>",
            ),
            (
                "urn:test:said",
                "orexis:BeliefGraph ; orexis:arrivedBy orexis:Recorded ; orexis:ownedBy <urn:test:me>",
            ),
        ];
        let rows: String = said.iter().map(|(g, s)| format!("<{g}> a {s} . ")).collect();
        store
            .update(&format!("INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ {rows} }} }}"))
            .unwrap();
        let mut part = Belief::new(&store, "urn:test:me").unwrap();
        part.revise(&["urn:test:reading".to_string()], BELIEF, snapshots::now())
            .unwrap();
        assert!(part.deliberator.pending().is_empty());
        let mut deliberator = Deliberator::new(&store, "urn:test:me", Some(0)).unwrap();
        let stated = store.graphs_of(&[BELIEF], &Within::common()).unwrap();
        assert_eq!(stated, ["urn:test:world"], "the common beliefs alone stand beside it");
        deliberator.changed("urn:test:observed", Some(stated), "urn:test:ObservedGraph");
        assert_eq!(deliberator.pending(), ["urn:test:observed"]);
    }
}
