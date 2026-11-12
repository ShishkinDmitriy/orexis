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
//! WHAT SENSING SAYS HAPPENED, to whoever watches the agent and made only where somebody does (`events`): an
//! observation graph written, heard as it is written and said with what the rules concluded of it, which belief has
//! written by then, and with how long after the percept before it it came; how many sensors are silent at each ask;
//! and which are said silent or stuck after each ask, one event per sensor doubted, and one saying neither for a
//! sensor doubted at the last ask and no longer, so the series' last word on it in a window is that it is fine.

use std::collections::BTreeSet;

use oxigraph::model::{Literal, NamedNode};
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{instant, isoformat, seconds_of};
use orexis::events::{Watch, round6};
use orexis::ontology::{BELIEF, DERIVED, local_of};
use orexis::store::{Store, Within, iri, value};
use orexis::task::{Arrived, Every, Handed, Heard, Hears, Package, Task, Turn, Woke, sooner};

use crate::cadence::cadence_of;
use crate::events::{Doubted, Observed, Perceived, Silence, tag_of};
use crate::missed::missed;
use crate::ontology::{OBSERVATION_GRAPH, OBSERVING, OBSERVING_TRIGGER, REVISED_SOURCE, SILENCE_GRAPH, silence_graph};

/// HOW OFTEN SENSING ASKS WHAT HAS FALLEN DUE, in seconds of the one timeline.
pub const EVERY_S: f64 = 60.0;

const ASK: usize = 0;
const HEARD: usize = 1;
const OBSERVE: usize = 2;

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

/// WHAT AN OBSERVATION SAYS, read off the graph and what was concluded of it.
const OBSERVED_Q: &str = "
SELECT ?sensor ?feature ?property ?value ?scaled ?defect ?t ?raw ?previous WHERE {
  ?o sosa:madeBySensor ?sensor ; sosa:resultTime ?t ; sosa:hasFeatureOfInterest ?feature ;
     sosa:observedProperty ?property
  OPTIONAL { ?o sosa:hasSimpleResult ?value } OPTIONAL { ?o sensing:scaledResult ?scaled }
  OPTIONAL { ?o sensing:defect ?defect }
  OPTIONAL { ?o sensing:rawResult ?raw } OPTIONAL { ?o sensing:previous ?previous } } LIMIT 1";

const MADE_Q: &str = "SELECT ?t WHERE { $percept sosa:resultTime ?t } LIMIT 1";

const STUCK_Q: &str = "SELECT DISTINCT ?sensor WHERE { ?sensor sensing:stuckOn ?number }";

/// Sensing's part.
pub struct Sensing {
    beliefs: Store,
    me: String,
    /// The percepts a restart found unrevised, said at the first ask, once anybody hears.
    due: Vec<String>,
    /// Whoever watches the agent.
    pub watch: Watch,
    /// The sensors doubted at the last ask.
    doubts: BTreeSet<String>,
}

impl Sensing {
    pub fn new(beliefs: &Store, agent: &str) -> Result<Self, Error> {
        Ok(Sensing {
            beliefs: beliefs.clone(),
            me: me_of(beliefs, agent)?,
            due: Vec::new(),
            watch: Watch::default(),
            doubts: BTreeSet::new(),
        })
    }

    /// The sensors silent at `now` (`missed`), each kept as a silence and said in the log at the first ask that
    /// finds it — the silences already kept, holding until a reading ends them, are the ones said, so a restart says
    /// none again. The silences written.
    pub fn ask(&mut self, now: DateTime) -> Result<Vec<String>, Error> {
        let (written, silent) = self.missed(now)?;
        if self.watch.connected() {
            self.watch.emit(&Silence {
                silent: i64::try_from(silent.len()).ok(),
            });
            for event in self.doubted(now, &silent)? {
                self.watch.emit(&event);
            }
        }
        Ok(written)
    }

    fn missed(&self, now: DateTime) -> Result<(Vec<String>, BTreeSet<String>), Error> {
        let beliefs = &self.beliefs;
        let found = missed(beliefs, now)?;
        let silent: BTreeSet<String> = found.iter().map(|(s, _)| s.clone()).collect();
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
        Ok((written, silent))
    }

    /// Which sensors are doubted at `now`, and how — `silent` as `missed` answered it; and, saying neither, each
    /// doubted at the last ask and no longer.
    fn doubted(&mut self, now: DateTime, silent: &BTreeSet<String>) -> Result<Vec<Doubted>, Error> {
        let holding = self.beliefs.graphs_of(
            &[OBSERVATION_GRAPH],
            &Within {
                at: Some(now),
                now: Some(now),
                ..Within::default()
            },
        )?;
        let holding: Vec<&str> = holding.iter().map(String::as_str).collect();
        let stuck: BTreeSet<String> = self
            .beliefs
            .rows(STUCK_Q, &holding)?
            .iter()
            .filter_map(|r| iri(r, "sensor"))
            .collect();
        let doubts: BTreeSet<String> = silent.union(&stuck).cloned().collect();
        let mut said: Vec<Doubted> = doubts
            .iter()
            .map(|sensor| Doubted {
                sensor: tag_of(sensor),
                silent: i64::from(silent.contains(sensor)),
                stuck: i64::from(stuck.contains(sensor)),
            })
            .collect();
        said.extend(self.doubts.difference(&doubts).map(|sensor| Doubted {
            sensor: tag_of(sensor),
            silent: 0,
            stuck: 0,
        }));
        self.doubts = doubts;
        Ok(said)
    }

    /// Say the observation `graph` holds, with how long after the percept before it it came.
    fn observation(&self, graph: &str) -> Result<(), Error> {
        let beliefs = &self.beliefs;
        let mut read = vec![graph.to_string()];
        read.extend(beliefs.revisions_of(&[graph], OBSERVATION_GRAPH)?);
        let read: Vec<&str> = read.iter().map(String::as_str).collect();
        let Some(o) = beliefs.rows(OBSERVED_Q, &read)?.into_iter().next() else {
            return Ok(());
        };
        let number = |key: &str| value(&o, key).and_then(|v| v.parse::<f64>().ok());
        let defective = o.contains_key("defect");
        let Some(reading) = number("value").or_else(|| if defective { number("scaled") } else { None }) else {
            return Ok(());
        };
        let (Some(sensor), Some(t)) = (iri(&o, "sensor"), value(&o, "t")) else {
            return Ok(());
        };
        let at = instant(&t)?;
        let before = match iri(&o, "previous") {
            Some(previous) => {
                let all = beliefs.graphs_of(&[OBSERVATION_GRAPH], &Within::default())?;
                let all: Vec<&str> = all.iter().map(String::as_str).collect();
                let made = beliefs.rows(&bind(MADE_Q, &[("percept", Value::iri(previous.as_str()))])?, &all)?;
                made.first()
                    .and_then(|r| value(r, "t"))
                    .map(|t| instant(&t))
                    .transpose()?
            }
            None => None,
        };
        let cadence = cadence_of(beliefs, &sensor)?;
        self.watch.emit(&Observed {
            observed_property: iri(&o, "property").unwrap_or_default(),
            value: round6(reading),
            at,
            sensor: Some(tag_of(&sensor)),
            sensor_id: Some(tag_of(&sensor)),
            feature_id: iri(&o, "feature").map(|f| tag_of(&f)),
            interval_s: before
                .and_then(|b| at.checked_sub(b))
                .map(|d| (seconds_of(d) * 1000.0).round() / 1000.0),
            cadence_s: cadence,
            raw: number("raw").map(round6),
            defective,
        });
        Ok(())
    }

    /// Say `graphs` were perceived, for belief to revise.
    pub fn perceived(&self, graphs: Vec<String>) {
        if !graphs.is_empty() {
            self.watch.emit(&Perceived { graphs });
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

inventory::submit! { Package { name: "sensing", start } }

/// THE PACKAGE'S START: its part made and started - what it hears, what it does every so often - and its task.
fn start(handed: &Handed) -> Result<Option<Task>, Error> {
    let mut part = Sensing::new(&handed.store, &handed.id)?;
    let mut hears = handed.events.hears();
    let arrived = handed.arrived();
    let mut timers = Vec::new();
    part.start(handed, &mut hears, &arrived, &mut timers)?;
    Ok(Some(Box::pin(task(handed.clone(), part, hears, arrived, timers))))
}

/// THE PACKAGE'S TASK: it decides as the run begins, then waits for what it hears, an arrival or the instant it is
/// next due; once nothing more waits to be heard it does what it queued for itself and what has fallen due.
async fn task(
    handed: Handed,
    mut part: Sensing,
    mut hears: Hears,
    mut arrived: Arrived,
    mut timers: Vec<(Every, usize)>,
) -> Result<(), Error> {
    let mut heard = None;
    let mut due = None;
    loop {
        let mut turn = handed.turn();
        match heard.take() {
            Some(Woke::Event(tag, event)) => {
                let wrote = part.heard_event(tag, &event, &mut turn);
                turn.done(wrote)?;
            }
            Some(Woke::Graphs(tag, graphs)) => {
                let wrote = part.heard(tag, &graphs, &mut turn);
                turn.done(wrote)?;
            }
            _ => {}
        }
        if hears.is_empty() {
            for (every, tag) in &mut timers {
                if every.due(turn.now) {
                    let wrote = part.run(*tag, &mut turn);
                    turn.done(wrote)?;
                }
            }
            due = timers
                .iter()
                .fold(turn.next(), |soonest, (every, _)| sooner(soonest, every.at()));
        }
        heard = tokio::select! {
            biased;
            _ = handed.stopped() => break,
            woke = hears.next() => match woke {
                Some(woke) => Some(woke),
                None => break,
            },
            _ = arrived.wait() => None,
            _ = handed.sleep_until(due) => None,
        };
    }
    Ok(())
}

impl Sensing {
    /// What a restart finds unrevised: every percept nothing was concluded of, said at the first ask - said as it
    /// starts, nobody would hear it yet.
    fn unrevised(&mut self) -> Result<(), Error> {
        if let Some(cat) = self.beliefs.catalogue()? {
            self.due = self
                .beliefs
                .rows(&bind(UNREVISED_Q, &[("cat", Value::iri(cat))])?, &[])?
                .iter()
                .filter_map(|r| iri(r, "g"))
                .collect();
        }
        Ok(())
    }

    fn start(
        &mut self,
        handed: &Handed,
        hears: &mut Hears,
        arrived: &Arrived,
        timers: &mut Vec<(Every, usize)>,
    ) -> Result<(), Error> {
        let _ = (&handed, &hears, &arrived, &timers);
        self.watch = handed.events.watch().clone();
        timers.push((Every::new(EVERY_S), ASK));
        self.unrevised()?;
        hears.graph(OBSERVATION_GRAPH, HEARD);
        hears.event(OBSERVING_TRIGGER, OBSERVE);
        Ok(())
    }

    fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        match job {
            ASK => {
                //  WHAT A RESTART FOUND UNREVISED is said at the first ask: said at start, nobody heard it yet.
                let due = std::mem::take(&mut self.due);
                self.perceived(due);
                self.ask(pass.now)
            }
            _ => Ok(Vec::new()),
        }
    }

    /// The percepts one message wrote, said together: belief revises them as one, and says so once.
    fn heard(&mut self, _job: usize, graphs: &[String], _pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        self.perceived(graphs.to_vec());
        Ok(Vec::new())
    }

    /// What sensing's policy does of a revision pass: say each percept it revised as the observation it is.
    fn heard_event(&mut self, _job: usize, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        if !self.watch.connected() {
            return Ok(Vec::new());
        }
        let revised = event.all(REVISED_SOURCE);
        if revised.is_empty() {
            return Ok(Vec::new());
        }
        let percepts = self.beliefs.graphs_of(&[OBSERVATION_GRAPH], &Within::default())?;
        let observed: Vec<NamedNode> = revised
            .into_iter()
            .filter(|g| percepts.iter().any(|p| p == g.as_str()))
            .cloned()
            .collect();
        if observed.is_empty() {
            return Ok(Vec::new());
        }
        let activity = pass.begin(OBSERVING, &observed);
        let said = observed.iter().try_for_each(|g| self.observation(g.as_str()));
        pass.end(activity);
        said?;
        Ok(Vec::new())
    }
}

#[cfg(test)]
mod tests {
    //! Sensing's part, held as `agent/sensing/tests/test_create.py` holds it: once started it asks every minute of
    //! the timeline what has fallen due, whether or not anything arrived, keeps each silence until a reading ends
    //! it, and hands belief each observation nothing was concluded of, with this layer's kind.

    use std::path::Path;

    use orexis::clock::{instant as parse, seconds};
    use orexis::snapshots::{ME, now, stand_in};
    use orexis::store::value;

    use super::*;
    use crate::ontology::{SILENT_AFTER_TERM, default_of};
    use crate::received::{GRACE, received};
    use std::sync::{Arc, Mutex};

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
        let mut part = Sensing::new(&store, "keeper").unwrap();
        let written = part.ask(later).unwrap();
        assert_eq!(written.len(), 1, "the first ask keeps the silence: {written:?}");
        let silence = written[0].clone();
        assert_eq!(part.ask(later).unwrap(), Vec::<String>::new(), "kept once");
        let mut restarted = Sensing::new(&store, "keeper").unwrap();
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
    fn it_says_each_percept_for_belief_to_revise_into_this_layers_kind() {
        let store = pot();
        let before = received(&store, ME, PROBE, br#"{"value": 0.2}"#, now()).unwrap();
        type Said = Arc<Mutex<Vec<Vec<(String, String)>>>>;
        let said: Said = Arc::new(Mutex::new(Vec::new()));
        let into = said.clone();
        let mut part = Sensing::new(&store, "keeper").unwrap();
        part.watch.connect(move |event, _| {
            if let Some(p) = orexis::events::as_of::<Perceived>(event) {
                into.lock().unwrap().push(
                    orexis::events::Event::about(p)
                        .into_iter()
                        .map(|(k, t)| (k.to_string(), t.to_string()))
                        .collect(),
                );
            }
        });
        let about = |graphs: &[String]| {
            let mut about: Vec<(String, String)> = graphs
                .iter()
                .map(|g| (crate::ontology::REVISES.to_string(), format!("<{g}>")))
                .collect();
            about.push((crate::ontology::INTO.to_string(), format!("<{OBSERVATION_GRAPH}>")));
            about
        };
        part.unrevised().unwrap();
        let events = orexis::task::Events::new(&store);
        let mut turn = events.turn(plus(now(), CADENCE), "keeper");
        part.run(ASK, &mut turn).unwrap();
        assert_eq!(
            *said.lock().unwrap(),
            [about(&before)],
            "the one nothing was concluded of, at the first ask"
        );
        let written = received(&store, ME, PROBE, br#"{"value": 0.22}"#, plus(now(), 2.0 * CADENCE)).unwrap();
        part.perceived(written.clone());
        assert_eq!(said.lock().unwrap().last(), Some(&about(&written)));
    }
}
