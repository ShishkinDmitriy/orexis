//! THE OBSERVER, the package's core: the role the self plays, read off its self graph, and what it does every so
//! often and of what it hears - ask after silence, hand each percept to belief, say each observation.

use std::collections::BTreeSet;

use oxigraph::model::NamedNode;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{instant, isoformat, seconds_of};
use orexis::events::Watch;
use orexis::ontology::{DERIVED, ONTOLOGY, SELF_GRAPH, local_of};
use orexis::store::{Store, Within, iri, value};
use orexis::task::{Heard, Turn};

use crate::cadence::cadence_of;
use crate::events::{Doubted, Perceived, Silence, tag_of};
use crate::missed::missed;
use crate::ontology::{OBSERVATION_GRAPH, OBSERVER, OBSERVING, REVISED_SOURCE, SILENCE_GRAPH, silence_graph};

pub(crate) const ASK: usize = 0;
pub(crate) const HEARD: usize = 1;
pub(crate) const OBSERVE: usize = 2;

/// THE OBSERVER THE SELF PLAYS, the package's core: the sensors its attentions name and how often sensing asks after
/// them, each what the role says in the agent's self graph and, where it says nothing, the default this package's
/// ontology states; and what it keeps between two asks. How long a sensor may be silent or stuck is said per
/// attention, so it is asked per sensor (`cadence::limit_of`); and what the role says of archiving is read by what
/// archives the readings.
pub struct Observer {
    /// Every sensor an attention of the role names (`sensing:attends`, `sensing:sensor`), sorted.
    pub sensors: Vec<String>,
    /// How often sensing asks which sensors have fallen due or gone silent, in the agent's seconds
    /// (`sensing:askedEveryS`).
    pub asked_every_s: f64,
    beliefs: Store,
    me: String,
    /// The percepts a restart found unrevised, said at the first ask, once anybody hears.
    due: Vec<String>,
    /// Whoever watches the agent.
    pub watch: Watch,
    /// The sensors doubted at the last ask.
    doubts: BTreeSet<String>,
}

impl Observer {
    /// The observer the self plays, read off the store in one query: what its role says and, where it says
    /// nothing, the default sensing's ontology states. THE SELF GRAPH WAS HELD TO ITS REQUIREMENTS AT ONBOARDING, so
    /// each figure is stated once at most; nothing is picked between here.
    pub fn new(store: &Store) -> Result<Self, Error> {
        /// THE OBSERVER THE SELF PLAYS, IN ONE QUERY: the self, every role it plays with its class, every sensor an
        /// attention of a role names, and how often sensing asks after them as the role says or, where it says none,
        /// the default sensing's ontology states on its shape of the observer (`sh:defaultValue`). A row per role and
        /// sensor.
        const OBSERVER_Q: &str = "PREFIX orexis: <http://example.org/orexis#> PREFIX sensing: <http://example.org/orexis/sensing#> PREFIX sh: <http://www.w3.org/ns/shacl#> SELECT DISTINCT ?me ?role ?kind ?sensor (COALESCE(?askedSaid, ?askedOwn) AS ?asked) WHERE { \
        ?shape sh:targetClass sensing:Observer ; sh:property [ sh:path sensing:askedEveryS ; sh:defaultValue ?askedOwn ] . \
        OPTIONAL { ?me a orexis:Self } \
        OPTIONAL { ?me orexis:plays ?role . ?role a ?kind } \
        OPTIONAL { ?me orexis:plays/sensing:attends/sensing:sensor ?sensor } \
        OPTIONAL { ?me orexis:plays ?asking . ?asking sensing:askedEveryS ?askedSaid } }";
        let mut known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        known.extend(store.graphs_of(&[ONTOLOGY], &Within::default())?);
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = store.rows(OBSERVER_Q, &known)?;
        //  ONE IS PLAYED: what the role says besides its attentions is said to sensing once for the agent, so sensors
        //  judged by different limits are two attentions of one observer, and a second observer is refused.
        let mut played = BTreeSet::new();
        for row in &rows {
            let Some(kind) = value(row, "kind") else { continue };
            if kind == OBSERVER || store.closed(&kind)?.iter().any(|class| class == OBSERVER) {
                played.extend(value(row, "role"));
            }
        }
        if played.len() > 1 {
            return Err(Error::Document(format!(
                "the self plays {} observers, and an agent plays one",
                played.len()
            )));
        }
        let first = rows
            .first()
            .ok_or_else(|| Error::Document("the store states no observer's figures, and no default".into()))?;
        let me = iri(first, "me").ok_or_else(|| Error::Document("the store holds no self".into()))?;
        let asked = value(first, "asked").unwrap_or_default();
        let asked_every_s = asked.parse::<f64>().map_err(|_| {
            Error::Document(format!(
                "an observer asked after its sensors every {asked} is no number"
            ))
        })?;
        let sensors: BTreeSet<String> = rows.iter().filter_map(|row| iri(row, "sensor")).collect();
        Ok(Observer {
            sensors: sensors.into_iter().collect(),
            asked_every_s,
            beliefs: store.clone(),
            me,
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
        /// THE SENSORS KEPT SILENT NOW: each silence graph holding, its end not yet said by a reading.
        const SILENT_Q: &str = "PREFIX sensing: <http://example.org/orexis/sensing#> SELECT DISTINCT ?sensor WHERE { ?sensor sensing:silentSince ?since }";
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
                "PREFIX sensing: <http://example.org/orexis/sensing#> PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> INSERT DATA {{\n  GRAPH <{graph}> {{ <{sensor}> sensing:silentSince \"{}\"^^xsd:dateTime . }}\n  {entry} }}",
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
        const STUCK_Q: &str = "PREFIX sensing: <http://example.org/orexis/sensing#> SELECT DISTINCT ?sensor WHERE { ?sensor sensing:stuckOn ?number }";
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
        /// WHAT AN OBSERVATION SAYS, read off the graph and what was concluded of it.
        const MADE_Q: &str =
            "PREFIX sosa: <http://www.w3.org/ns/sosa/> SELECT ?t WHERE { $percept sosa:resultTime ?t } LIMIT 1";
        let beliefs = &self.beliefs;
        let Some((mut observed, sensor, previous)) = crate::past::observed(beliefs, graph, OBSERVATION_GRAPH)? else {
            return Ok(());
        };
        let before = match previous {
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
        let at = observed.at;
        observed.cadence_s = cadence_of(beliefs, &sensor)?;
        observed.interval_s = before
            .and_then(|b| at.checked_sub(b))
            .map(|d| (seconds_of(d) * 1000.0).round() / 1000.0);
        self.watch.emit(&observed);
        Ok(())
    }

    /// Say `graphs` were perceived, for belief to revise.
    pub fn perceived(&self, graphs: Vec<String>) {
        if !graphs.is_empty() {
            self.watch.emit(&Perceived { graphs });
        }
    }

    /// What a restart finds unrevised: every percept nothing was concluded of, said at the first ask - said as it
    /// starts, nobody would hear it yet.
    pub(crate) fn unrevised(&mut self) -> Result<(), Error> {
        /// EVERY OBSERVATION RECEIVED THAT NOTHING WAS CONCLUDED OF, oldest first: what a pass cut short of being
        /// handed to belief left.
        const UNREVISED_Q: &str = "PREFIX dcterms: <http://purl.org/dc/terms/> PREFIX orexis: <http://example.org/orexis#> PREFIX prov: <http://www.w3.org/ns/prov#> PREFIX sensing: <http://example.org/orexis/sensing#> 
        SELECT ?g WHERE {
          GRAPH $cat { ?g a sensing:ObservationGraph ; orexis:arrivedBy orexis:Received
                       OPTIONAL { ?g dcterms:temporal/orexis:start ?start }
                       FILTER NOT EXISTS { ?r prov:wasDerivedFrom ?g ; a sensing:ObservationGraph } } }
        ORDER BY ?start ?g";
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

    pub(crate) fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
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
    pub(crate) fn heard(&mut self, _job: usize, graphs: &[String], _pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        self.perceived(graphs.to_vec());
        Ok(Vec::new())
    }

    /// What sensing's policy does of a revision pass: say each percept it revised as the observation it is.
    pub(crate) fn heard_event(
        &mut self,
        _job: usize,
        event: &Heard,
        pass: &mut Turn<'_>,
    ) -> Result<Vec<String>, Error> {
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
        let mut part = Observer::new(&store).unwrap();
        let written = part.ask(later).unwrap();
        assert_eq!(written.len(), 1, "the first ask keeps the silence: {written:?}");
        let silence = written[0].clone();
        assert_eq!(part.ask(later).unwrap(), Vec::<String>::new(), "kept once");
        let mut restarted = Observer::new(&store).unwrap();
        assert_eq!(
            restarted.ask(later).unwrap(),
            Vec::<String>::new(),
            "and not again by a restart"
        );
        let said = "PREFIX sensing: <http://example.org/orexis/sensing#> SELECT ?since ?until WHERE { ?s sensing:silentSince ?since OPTIONAL { ?s sensing:silentUntil ?until } }";
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
        let mut part = Observer::new(&store).unwrap();
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
