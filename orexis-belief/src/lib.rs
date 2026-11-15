//! BELIEF, in Rust, ported from `orexis-belief/`:
//!
//! - [`transition`]: rules that change a state rather than conclude of it, and the one machine that applies them,
//!   which planning applies an action's effect by;
//! - `revise`: what the rules conclude of one graph, its revisions;
//! - `trigger`: the transitions an arrival of testimony triggers, applied to the agent's own state;
//! - `deliberator`: the pass that sequences the two over what was written, within a budget;
//! - the start, below the modules: the package's policy on its deliberator, which revises what is written as it is
//!   written.

use oxigraph::model::NamedNode;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::ontology::BELIEF;
use orexis::store::Within;
use orexis::task::{Handed, Heard, Hears, Package, Task, Turn, Woke};

use crate::ontology::{INTO, REVISES, REVISING, REVISING_TRIGGER, REVISION_GRAPH};

mod deliberator;
pub mod ontology;
mod revise;
pub mod transition;
mod trigger;

pub use deliberator::{Deliberator, Revised};

const HEARD: usize = 0;
const REVISE: usize = 1;

//  THE PACKAGE'S POLICY, on its core: what the deliberator revises as the package starts and on what it hears.
impl Deliberator {
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
    let mut belief = Deliberator::new(&handed.store, &handed.id, None)?;
    belief.watch = handed.events.watch().clone();
    belief.start(handed.clock.now())?;
    let mut hears = handed.events.hears();
    hears.graph(BELIEF, HEARD);
    hears.event(REVISING_TRIGGER, REVISE);
    Ok(Some(Box::pin(task(handed.clone(), belief, hears))))
}

/// BELIEF'S TASK: it waits for a belief written, or an event beneath its trigger, and revises.
async fn task(handed: Handed, mut belief: Deliberator, mut hears: Hears) -> Result<(), Error> {
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

impl Deliberator {
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
    //! Belief's policy on its deliberator, held as `agent/belief/tests/test_create.py` holds it.

    use orexis::ontology::CATALOGUE_GRAPH;
    use orexis::snapshots;
    use orexis::store::Store;

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
        let mut part = Deliberator::new(&store, "urn:test:me", None).unwrap();
        let heard = Arc::new(Mutex::new(Vec::new()));
        let into = heard.clone();
        part.watch.connect(move |event, _| {
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
        let mut part = Deliberator::new(&store, "urn:test:me", None).unwrap();
        part.revise(&["urn:test:reading".to_string()], BELIEF, snapshots::now())
            .unwrap();
        assert!(part.pending().is_empty());
        let mut deliberator = Deliberator::new(&store, "urn:test:me", Some(0)).unwrap();
        let stated = store.graphs_of(&[BELIEF], &Within::common()).unwrap();
        assert_eq!(stated, ["urn:test:world"], "the common beliefs alone stand beside it");
        deliberator.changed("urn:test:observed", Some(stated), "urn:test:ObservedGraph");
        assert_eq!(deliberator.pending(), ["urn:test:observed"]);
    }
}
