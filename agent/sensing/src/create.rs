//! SENSING'S PART, as `agent/sensing/create.py` makes it, and what it does of its own accord once started
//! (a-package-starts-itself): it asks, every `EVERY_S` of the one timeline, which sensors have gone silent
//! (`missed`), whether or not anything arrived (#843), and keeps each as a silence and says it in the log as it falls
//! silent. What a transport hands it, `received` writes.
//!
//! SENSING RUNS BELIEF'S REVISION OVER ITS OWN OBSERVATIONS (#944). An observation is no belief, and the belief
//! package, beneath, knows no kind of it, so this part, linked to belief's by whoever assembles them, hands it each
//! observation graph as it is written, and at start each one nothing was concluded of, with the kind its revision is
//! to be: `sensing:ObservationGraph`, this layer's own, so what the rules conclude of what a sensor said reaches no
//! reader of the mind either.
//!
//! NOT PORTED: the signals `observed`, `silence` and `doubted`, which wait for the journal and the series.

use oxigraph::model::Literal;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::isoformat;
use orexis::ontology::{BELIEF, DERIVED, local_of};
use orexis::runtime::{Part, Pass, Starting};
use orexis::store::{Store, Within, iri};

use crate::missed::missed;
use crate::ontology::{OBSERVATION_GRAPH, SILENCE_GRAPH, silence_graph};

/// HOW OFTEN SENSING ASKS WHAT HAS FALLEN DUE, in seconds of the one timeline.
pub const EVERY_S: f64 = 60.0;

const ASK: usize = 0;
const HEARD: usize = 1;

/// THE SENSORS KEPT SILENT NOW: each silence graph holding, its end not yet said by a reading.
const SILENT_Q: &str = "SELECT DISTINCT ?sensor WHERE { ?sensor sensing:silentSince ?since }";

/// EVERY OBSERVATION RECEIVED THAT NOTHING WAS CONCLUDED OF, oldest first: what a pass cut short of being handed to
/// belief left.
const UNREVISED_Q: &str = "
SELECT ?g WHERE {
  GRAPH $cat { ?g a sensing:ObservationGraph ; orexis:arrivedBy orexis:Received
               OPTIONAL { ?g dcterms:temporal/orexis:start ?start }
               FILTER NOT EXISTS { ?r prov:wasDerivedFrom ?g ; a sensing:ObservationGraph } } }
ORDER BY ?start ?g";

/// What sensing hands belief to revise: the graphs, the kind their revisions are to be, and the instant.
pub type Revises<'a> = Box<dyn FnMut(&[String], &str, DateTime) -> Result<(), Error> + 'a>;

/// Sensing's part.
pub struct Sensing<'a> {
    beliefs: &'a Store,
    me: String,
    /// Belief's revision, beneath, where the agent is linked to a deliberator.
    pub revise: Option<Revises<'a>>,
}

impl<'a> Sensing<'a> {
    pub fn new(beliefs: &'a Store, agent: &str) -> Result<Self, Error> {
        Ok(Sensing {
            beliefs,
            me: me_of(beliefs, agent)?,
            revise: None,
        })
    }

    /// The sensors silent at `now` (`missed`), each kept as a silence and said in the log at the first ask that
    /// finds it — the silences already kept, holding until a reading ends them, are the ones said, so a restart says
    /// none again. The silences written.
    pub fn ask(&self, now: DateTime) -> Result<Vec<String>, Error> {
        let beliefs = self.beliefs;
        let found = missed(beliefs, now)?;
        let holding = beliefs.graphs_of(&[SILENCE_GRAPH], &Within::at(now))?;
        let holding: Vec<&str> = holding.iter().map(String::as_str).collect();
        let kept: Vec<String> = beliefs
            .rows(SILENT_Q, &holding)?
            .iter()
            .filter_map(|r| iri(r, "sensor"))
            .collect();
        let mut written = Vec::new();
        for (sensor, since) in found {
            if kept.contains(&sensor) {
                continue;
            }
            let graph = silence_graph(&local_of(&self.me), &sensor, since);
            let entry = beliefs.entry(&graph, &[SILENCE_GRAPH], DERIVED, Some(&self.me), Some(since), None)?;
            beliefs.update(&format!(
                "INSERT DATA {{\n  GRAPH <{graph}> {{ <{sensor}> sensing:silentSince \"{}\"^^xsd:dateTime . }}\n  {entry} }}",
                isoformat(since)
            ))?;
            log::warn!(
                "{}: {} silent since {}",
                local_of(&self.me),
                local_of(&sensor),
                isoformat(since)
            );
            written.push(graph);
        }
        Ok(written)
    }

    fn revised(&mut self, graphs: &[String], at: DateTime) -> Result<(), Error> {
        match self.revise.as_mut() {
            Some(revise) if !graphs.is_empty() => revise(graphs, OBSERVATION_GRAPH, at),
            _ => Ok(()),
        }
    }
}

/// The agent told `agent` as its id, by the world's word: the one identifier a process is handed.
fn me_of(beliefs: &Store, agent: &str) -> Result<String, Error> {
    let common = beliefs.graphs_of(&[BELIEF], &Within::common())?;
    let common: Vec<&str> = common.iter().map(String::as_str).collect();
    let text = bind(
        "SELECT ?a WHERE { ?a a orexis:Agent ; orexis:localId $id } LIMIT 1",
        &[("id", Value::Term(Literal::new_simple_literal(agent).into()))],
    )?;
    beliefs
        .rows(&text, &common)?
        .first()
        .and_then(|r| iri(r, "a"))
        .ok_or_else(|| Error::Evaluation(format!("no agent with localId '{agent}' in this store")))
}

impl Part for Sensing<'_> {
    fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
        starting.every(EVERY_S, ASK);
        if self.revise.is_some() {
            if let Some(cat) = self.beliefs.catalogue()? {
                let unrevised: Vec<String> = self
                    .beliefs
                    .rows(&bind(UNREVISED_Q, &[("cat", Value::iri(cat))])?, &[])?
                    .iter()
                    .filter_map(|r| iri(r, "g"))
                    .collect();
                self.revised(&unrevised, starting.now())?;
            }
            starting.on(OBSERVATION_GRAPH, HEARD);
        }
        Ok(())
    }

    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        match job {
            ASK => self.ask(pass.now),
            _ => Ok(Vec::new()),
        }
    }

    fn heard(&mut self, _job: usize, graph: &str, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        self.revised(&[graph.to_string()], pass.now)?;
        Ok(Vec::new())
    }
}

#[cfg(test)]
mod tests {
    //! Sensing's part, held as `agent/sensing/tests/test_create.py` holds it: once started it asks every minute of
    //! the timeline what has fallen due, whether or not anything arrived, keeps each silence until a reading ends
    //! it, and hands belief each observation nothing was concluded of, with this layer's kind.

    use std::cell::RefCell;
    use std::path::Path;
    use std::rc::Rc;

    use orexis::clock::{Manual, instant as parse, seconds};
    use orexis::runtime::Runtime;
    use orexis::snapshots::{ME, now, stand_in};
    use orexis::store::value;

    use super::*;
    use crate::ontology::{SILENT_AFTER_TERM, default_of};
    use crate::received::{GRACE, received};

    const PROBE: &str = "http://example.org/test#probe";
    const CADENCE: f64 = 900.0;

    fn plus(at: DateTime, by: f64) -> DateTime {
        at.checked_add_day_time_duration(seconds(by)).unwrap()
    }

    fn pot() -> Store {
        stand_in(&Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/worlds/a_pot_and_its_probe.trig"))
    }

    #[test]
    fn its_part_asks_after_silence_every_minute_and_keeps_each_silence_until_a_reading_ends_it() {
        let store = pot();
        received(&store, ME, PROBE, br#"{"value": 0.2}"#, now()).unwrap();
        let silent_after = default_of(SILENT_AFTER_TERM).unwrap() as f64;
        let later = plus(now(), CADENCE * (1.0 + GRACE + silent_after));
        let since = plus(now(), CADENCE * (1.0 + GRACE));
        let clock = Manual::at(later);
        let mut part = Sensing::new(&store, "keeper").unwrap();
        let written = {
            let parts: Vec<(String, &mut dyn Part)> = vec![("sensing".into(), &mut part)];
            let mut runtime = Runtime::new(&store, "keeper", &clock, parts).unwrap();
            runtime.drain(later).unwrap()
        };
        assert_eq!(written.len(), 1, "the ask runs at the first pass: {written:?}");
        let silence = written[0].clone();
        assert_eq!(part.ask(later).unwrap(), Vec::<String>::new(), "kept once");
        let restarted = Sensing::new(&store, "keeper").unwrap();
        assert_eq!(
            restarted.ask(later).unwrap(),
            Vec::<String>::new(),
            "and not again by a restart"
        );
        let said =
            "SELECT ?since ?until WHERE { ?s sensing:silentSince ?since OPTIONAL { ?s sensing:silentUntil ?until } }";
        let read = |store: &Store| {
            let found = store.rows(said, &[&silence]).unwrap();
            assert_eq!(found.len(), 1);
            (
                parse(&value(&found[0], "since").unwrap()).unwrap(),
                value(&found[0], "until").map(|u| parse(&u).unwrap()),
            )
        };
        assert_eq!(read(&store), (since, None));
        received(&store, ME, PROBE, br#"{"value": 0.3}"#, later).unwrap();
        assert_eq!(read(&store), (since, Some(later)));
        assert_eq!(
            store.graphs_of(&[SILENCE_GRAPH], &Within::default()).unwrap(),
            std::slice::from_ref(&silence),
            "kept"
        );
        assert!(
            store
                .graphs_of(&[SILENCE_GRAPH], &Within::at(later))
                .unwrap()
                .is_empty(),
            "and holding no longer"
        );
    }

    #[test]
    fn linked_to_belief_it_hands_in_each_observation_with_this_layers_kind() {
        let store = pot();
        let before = received(&store, ME, PROBE, br#"{"value": 0.2}"#, now()).unwrap();
        type Handed = Rc<RefCell<Vec<(Vec<String>, String)>>>;
        let handed: Handed = Rc::new(RefCell::new(Vec::new()));
        let into = handed.clone();
        let clock = Manual::at(plus(now(), CADENCE));
        let mut part = Sensing::new(&store, "keeper").unwrap();
        part.revise = Some(Box::new(move |graphs, kind, _| {
            into.borrow_mut().push((graphs.to_vec(), kind.to_string()));
            Ok(())
        }));
        {
            let parts: Vec<(String, &mut dyn Part)> = vec![("sensing".into(), &mut part)];
            Runtime::new(&store, "keeper", &clock, parts).unwrap();
        }
        assert_eq!(
            *handed.borrow(),
            [(before, OBSERVATION_GRAPH.to_string())],
            "the one nothing was concluded of, at start"
        );
        let written = received(&store, ME, PROBE, br#"{"value": 0.22}"#, plus(now(), 2.0 * CADENCE)).unwrap();
        part.revised(&written, plus(now(), 2.0 * CADENCE)).unwrap();
        assert_eq!(handed.borrow().last(), Some(&(written, OBSERVATION_GRAPH.to_string())));
    }
}
