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
use orexis::runtime::{Heard, Part, Pass, Starting};
use orexis::store::{Store, Within};

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
    fn revising(&mut self, graphs: &[String], kind: &str, pass: &mut Pass<'_>) -> Result<(), Error> {
        let triggers: Vec<NamedNode> = graphs.iter().filter_map(|g| NamedNode::new(g.as_str()).ok()).collect();
        let activity = pass.begin(REVISING, &triggers);
        let revised = self.revise(graphs, kind, pass.now);
        pass.end(activity);
        revised
    }
}

impl Part for Belief {
    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
        //  EVERY BELIEF NOT YET REVISED, but the common ones: the world's documents were concluded on at genesis.
        let mut skip = self.beliefs.graphs_of(&[REVISION_GRAPH], &Within::default())?;
        skip.extend(self.beliefs.graphs_of(&[BELIEF], &Within::common())?);
        let mut due = Vec::new();
        for g in self.beliefs.graphs_of(&[BELIEF], &Within::default())? {
            if !skip.contains(&g) && self.beliefs.revisions_of(&[&g], BELIEF)?.is_empty() {
                due.push(g);
            }
        }
        self.revise(&due, BELIEF, starting.now())?;
        starting.on(BELIEF, HEARD);
        starting.hears(REVISING_TRIGGER, REVISE);
        Ok(())
    }

    fn run(&mut self, _job: usize, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        Ok(Vec::new())
    }

    fn heard(&mut self, _job: usize, graph: &str, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        self.revising(&[graph.to_string()], BELIEF, pass)?;
        Ok(Vec::new())
    }

    fn watch(&self) -> Option<orexis::events::Watch> {
        Some(self.deliberator.watch.clone())
    }

    /// What belief's policy does of a trigger: revise each graph it names, its revisions of the kind it names.
    fn heard_event(&mut self, _job: usize, event: &Heard, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
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

    use orexis::clock::Manual;
    use orexis::ontology::CATALOGUE_GRAPH;
    use orexis::runtime::Runtime;
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
        let clock = std::sync::Arc::new(Manual::at(snapshots::now()));
        let part = std::sync::Arc::new(std::sync::Mutex::new(Belief::new(&store, "urn:test:me").unwrap()));
        let heard = Arc::new(Mutex::new(Vec::new()));
        let into = heard.clone();
        part.lock().unwrap().deliberator.watch.connect(move |event, _| {
            if let Some(r) = orexis::events::as_of::<crate::deliberator::Revised>(event) {
                into.lock().unwrap().extend(r.graphs.clone());
            }
        });
        {
            let parts: Vec<(String, Box<dyn Part>)> = vec![("belief".into(), orexis::runtime::Lent::of(&part))];
            Runtime::new(&store, "urn:test:me", clock.clone(), parts).unwrap();
        }
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <urn:test:nothing> a orexis:BeliefGraph }} }}"
            ))
            .unwrap();
        part.lock()
            .unwrap()
            .revise(&["urn:test:nothing".to_string()], BELIEF, snapshots::now())
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
