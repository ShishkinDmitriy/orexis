//! THE OBSERVER, the package's core: the role the self plays, read off its self graph, and what it does every so
//! often and of what it hears - ask after silence, hand each percept to belief, say each observation.

use std::collections::BTreeSet;
use std::sync::Arc;

use oxigraph::model::NamedNode;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{instant, isoformat, seconds_of};
use orexis::events::Watch;
use orexis::ontology::{DERIVED, ONTOLOGY, SELF_GRAPH, local_of};
use orexis::store::{Store, Within, iri, value};
use orexis::task::{Every, Heard, Turn};
use orexis_transport::{Exchange, Inbox, Member, Members};

use crate::cadence::{cadence_of, lapsed, next_lapse};
use crate::events::{Doubted, Perceived, ReadingLapsed, Silence, tag_of};
use crate::missed::missed;
use crate::ontology::{
    ASKING, ATTENDING, LISTENING, OBSERVATION_GRAPH, OBSERVER, OBSERVING, PERCEIVING, REVISED_SOURCE, SILENCE_GRAPH,
    silence_graph,
};
use crate::received::received_by;

pub(crate) const ASK: usize = 0;
pub(crate) const HEARD: usize = 1;
pub(crate) const OBSERVE: usize = 2;
/// The first of the jobs that each ask one sensor for its reading, one per sensor read by asking.
pub(crate) const REQUEST: usize = 3;
/// The timers of the jobs that ask a sensor on its cadence, each with its job.
pub(crate) type Timers = Vec<(Every, usize)>;

/// The name sensing holds the agent running under, while it asks a sensor on a cadence.
const HOLDER: &str = "sensing";

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
    /// How soon a reading is said due again where its board was told and no reading came, in the agent's seconds
    /// (`sensing:askedAgainAfterS`).
    pub asked_again_after_s: f64,
    beliefs: Store,
    me: String,
    /// The percepts a restart found unrevised, said at the first ask, once anybody hears.
    due: Vec<String>,
    /// Whoever watches the agent.
    pub watch: Watch,
    /// What each turn's percepts, written and not yet said, are perceived by, oldest first: the name it will be said
    /// under, and the perceiving it is said within, the last of the turn's.
    perceiving: std::collections::VecDeque<(oxigraph::model::NamedNode, oxigraph::model::NamedNode)>,
    /// The sensors doubted at the last ask.
    doubts: BTreeSet<String>,
    /// Each sensor read by asking, with the member asked, its job the index after `REQUEST`.
    requested: Vec<(String, Arc<dyn Member>)>,
    /// Each sensor listened to, its readings arriving of their own accord.
    listened: Vec<String>,
    /// What sensing does of each sensor for as long as it runs, its listening or its asking (`attend`): what a
    /// perceiving of that sensor's message is part of.
    attending: std::collections::HashMap<String, orexis::activity::Activity>,
    /// Where each asked sensor's answer is left.
    pub replies: Inbox,
    /// The agent's members, read once every core is made.
    members: Members,
    /// Whether to say what is due at the next turn whatever the instant: at the start, and after a reading, which
    /// moves when the next falls due.
    told: bool,
    /// When a reading next falls due, as the last saying worked out.
    next_due: Option<DateTime>,
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
        const OBSERVER_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
        PREFIX sensing: <http://example.org/orexis/sensing#>
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        SELECT DISTINCT ?me ?role ?kind ?sensor (COALESCE(?askedSaid, ?askedOwn) AS ?asked) \
        (COALESCE(?againSaid, ?againOwn) AS ?again) WHERE { \
        ?shape sh:targetClass sensing:Observer ; sh:property [ sh:path sensing:askedEveryS ; sh:defaultValue ?askedOwn ] ; \
            sh:property [ sh:path sensing:askedAgainAfterS ; sh:defaultValue ?againOwn ] . \
        OPTIONAL { ?me a orexis:Self } \
        OPTIONAL { ?me orexis:plays ?role . ?role a ?kind } \
        OPTIONAL { ?me orexis:plays/sensing:attends/sensing:sensor ?sensor } \
        OPTIONAL { ?me orexis:plays ?asking . ?asking sensing:askedEveryS ?askedSaid } \
        OPTIONAL { ?me orexis:plays ?asking_again . ?asking_again sensing:askedAgainAfterS ?againSaid } }";
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
        let again = value(first, "again").unwrap_or_default();
        let asked_again_after_s = again
            .parse::<f64>()
            .map_err(|_| Error::Document(format!("an observer asking again after {again} is no number")))?;
        let sensors: BTreeSet<String> = rows.iter().filter_map(|row| iri(row, "sensor")).collect();
        Ok(Observer {
            sensors: sensors.into_iter().collect(),
            asked_every_s,
            asked_again_after_s,
            beliefs: store.clone(),
            me,
            due: Vec::new(),
            watch: Watch::default(),
            perceiving: Default::default(),
            doubts: BTreeSet::new(),
            requested: Vec::new(),
            listened: Vec::new(),
            attending: std::collections::HashMap::new(),
            replies: Inbox::default(),
            members: Members::default(),
            told: true,
            next_due: None,
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
        const SILENT_Q: &str = "PREFIX sensing: <http://example.org/orexis/sensing#>
            SELECT DISTINCT ?sensor WHERE { ?sensor sensing:silentSince ?since }";
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
                "PREFIX sensing: <http://example.org/orexis/sensing#>
                    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                    INSERT DATA {{\n  GRAPH <{graph}> {{ <{sensor}> sensing:silentSince \"{}\"^^xsd:dateTime . }}\n  {entry} }}",
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
        const STUCK_Q: &str = "PREFIX sensing: <http://example.org/orexis/sensing#>
            SELECT DISTINCT ?sensor WHERE { ?sensor sensing:stuckOn ?number }";
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
        const UNREVISED_Q: &str = "PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX orexis: <http://example.org/orexis#>
        PREFIX prov: <http://www.w3.org/ns/prov#>
        PREFIX sensing: <http://example.org/orexis/sensing#>
        SELECT ?g WHERE {
          GRAPH ?m_g { ?g a sensing:ObservationGraph ; orexis:arrivedBy orexis:Received
                     OPTIONAL { ?g dcterms:temporal/orexis:start ?start } }
          FILTER NOT EXISTS { GRAPH ?m_r { ?r prov:wasDerivedFrom ?g ; a sensing:ObservationGraph } } }
        ORDER BY ?start ?g";
        self.due = self
            .beliefs
            .rows(UNREVISED_Q, &[])?
            .iter()
            .filter_map(|r| iri(r, "g"))
            .collect();
        Ok(())
    }

    /// EVERY SENSOR OF THE OBSERVER'S, READ THROUGH THE MEMBER THAT REACHES IT: one a member answers when asked
    /// (`Exchange::Requested`) a job each, asked at the cadence the sensor states, or once where it states none - POLLING
    /// IS A REQUEST IN A LOOP, AND THE LOOP IS SENSING'S, since the cadence is
    /// (the-transport-is-the-bottom-layer-and-the-row-above-owns-the-loop) - and one whose readings arrive of their own
    /// accord (`Exchange::Listened`) listened to, every message on it left with the answers. The timers, and the jobs
    /// run once.
    pub(crate) fn request(&mut self, members: &Members) -> Result<(Timers, Vec<usize>), Error> {
        self.members = members.clone();
        let (mut timers, mut once) = (Vec::new(), Vec::new());
        for sensor in &self.sensors {
            if let Some(member) = members.reaching(sensor, Exchange::Listened)? {
                member.listen(sensor, self.replies.clone())?;
                self.listened.push(sensor.clone());
                continue;
            }
            let Some(member) = members.reaching(sensor, Exchange::Requested)? else {
                continue;
            };
            let job = REQUEST + self.requested.len();
            match cadence_of(&self.beliefs, sensor)? {
                Some(every) => timers.push((Every::new(every), job)),
                None => once.push(job),
            }
            self.requested.push((sensor.clone(), member));
        }
        if !self.requested.is_empty() {
            log::info!(
                "{} asks {} for its readings",
                local_of(&self.me),
                self.requested
                    .iter()
                    .map(|(s, _)| local_of(s))
                    .collect::<Vec<_>>()
                    .join(", ")
            );
        }
        Ok((timers, once))
    }

    /// What each sensor asked answered, and each listened to said, since the last take, each handed to `received` as it
    /// arrived: the percepts written, of one message together.
    pub(crate) fn answered(&mut self, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let mut written = Vec::new();
        //  THE PERCEIVING IS NAMED BEFORE IT IS SAID: each percept it writes begins by it, and the one before ends by
        //  it, so the name comes first and the event is said under it once the turn's graphs are heard.
        let perceiving = orexis::rdf::mint();
        let mut last = None;
        for message in self.replies.take() {
            let at = message.at.unwrap_or(pass.now);
            //  PERCEIVING ONE MESSAGE IS AN ACTIVITY, part of the listening or the asking of the sensor it is of: the
            //  percepts it wrote are said of it, so what revises them is traced to it.
            let attending = self.attending.get(&message.topic);
            if let Some(attending) = attending {
                pass.step_in(attending);
            }
            let activity = pass.begin(PERCEIVING, &[]);
            last = Some(activity.node.clone());
            let wrote = received_by(
                &self.beliefs,
                &self.me,
                &message.topic,
                &message.payload,
                at,
                None,
                None,
                Some((perceiving.as_str(), pass.now)),
            );
            pass.wrote_by(activity, wrote.as_deref().unwrap_or_default());
            if let Some(attending) = attending {
                pass.step_out(attending);
            }
            written.extend(wrote?);
        }
        if let (false, Some(last)) = (written.is_empty(), last) {
            self.perceiving.push_back((perceiving, last));
        }
        Ok(written)
    }

    /// WHAT SENSING DOES OF EACH SENSOR FOR AS LONG AS IT RUNS: a listening of each sensor whose readings arrive of
    /// their own accord and an asking of each it asks, each an activity inside sensing's running that names its
    /// sensor (`prov:used`).
    pub(crate) async fn attend(&mut self, handed: &orexis::task::Handed) -> Result<(), Error> {
        let asked = self.requested.iter().map(|(sensor, _)| (sensor.clone(), ASKING));
        let attended: Vec<(String, &'static str)> = self
            .listened
            .iter()
            .map(|sensor| (sensor.clone(), LISTENING))
            .chain(asked)
            .collect();
        for (sensor, kind) in attended {
            let Ok(node) = oxigraph::model::NamedNode::new(sensor.as_str()) else {
                continue;
            };
            let activity = handed.lasting(kind, vec![(crate::ontology::USED, node.into())]).await?;
            self.attending.insert(sensor, activity);
        }
        Ok(())
    }

    pub(crate) fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        match job {
            ASK => {
                //  WHAT A RESTART FOUND UNREVISED is said at the first ask: said at start, nobody heard it yet.
                let due = std::mem::take(&mut self.due);
                if !due.is_empty() {
                    let activity = pass.begin(PERCEIVING, &[]);
                    self.perceived(due);
                    pass.end(activity);
                }
                //  THE ASK AFTER ITS SENSORS IS AN ACTIVITY, begun by the clock inside sensing's running: the silences
                //  it keeps and what it says of the silent and the doubted are its own.
                let activity = pass.begin(ATTENDING, &[]);
                let wrote = self.ask(pass.now);
                pass.wrote_by(activity, wrote.as_deref().unwrap_or_default());
                wrote
            }
            job if job >= REQUEST => {
                //  A SENSOR ASKED ON A CADENCE KEEPS THE AGENT RUNNING: what it reads goes on arriving.
                pass.hold(HOLDER);
                if let Some((sensor, member)) = self.requested.get(job - REQUEST) {
                    member.send(sensor, b"", Some(self.replies.clone()))?;
                }
                Ok(Vec::new())
            }
            _ => Ok(Vec::new()),
        }
    }

    /// The percepts one message wrote, said together: belief revises them as one, and says so once; and what is due
    /// is said again at the next turn, a reading having moved when the next falls due.
    pub(crate) fn heard(&mut self, _job: usize, graphs: &[String], _pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        match self.perceiving.pop_front() {
            //  SAID WITHIN A PERCEIVING, the last of the turn that wrote them, each percept still said generated by its
            //  own: said once the graphs are told, it is said within no running for want of an activity.
            Some((named, within)) if !graphs.is_empty() => {
                self.watch.emit_as_within(
                    &Perceived {
                        graphs: graphs.to_vec(),
                    },
                    named,
                    within,
                );
            }
            _ => self.perceived(graphs.to_vec()),
        }
        self.told = true;
        Ok(Vec::new())
    }

    /// SENSING'S POLICY FOR A READING DUE: at the start, after a reading and when one next falls due, the sensors of
    /// the observer's whose readings have fallen due (`cadence::lapsed`) that a member is sent on and none answers
    /// when asked, said together as `sensing:ReadingLapsed` for the operator to tell their boards; and the turn woken
    /// when the next falls due, or `asked_again_after_s` on where a board was told, since it may not have heard. A
    /// sensor asked on its cadence is asked by sensing itself (`request`), and none is said due.
    pub(crate) fn due(&mut self, pass: &mut Turn<'_>) -> Result<(), Error> {
        if self.told || self.next_due.is_some_and(|next| next <= pass.now) {
            self.told = false;
            let mut due: Vec<String> = Vec::new();
            for (sensor, _) in lapsed(&self.beliefs, pass.now)? {
                if due.contains(&sensor) || self.requested.iter().any(|(s, _)| *s == sensor) {
                    continue;
                }
                if self.members.reaching(&sensor, Exchange::Sent)?.is_some() {
                    due.push(sensor);
                }
            }
            let next = next_lapse(&self.beliefs, pass.now)?;
            self.next_due = if due.is_empty() {
                next
            } else {
                let activity = pass.begin(ATTENDING, &[]);
                pass.emit(&ReadingLapsed { sensors: due });
                pass.end(activity);
                let again = pass
                    .now
                    .checked_add_day_time_duration(orexis::clock::seconds(self.asked_again_after_s))
                    .unwrap_or(pass.now);
                Some(next.map_or(again, |n| if n < again { n } else { again }))
            };
        }
        if let Some(next) = self.next_due {
            pass.wake_at(next);
        }
        Ok(())
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
    use crate::ontology::{ASKED_AGAIN_AFTER_S_TERM, SILENT_AFTER_TERM, default_of};
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
        let said = "PREFIX sensing: <http://example.org/orexis/sensing#>
            SELECT ?since ?until WHERE { ?s sensing:silentSince ?since OPTIONAL { ?s sensing:silentUntil ?until } }";
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

    /// A member every channel of which is sent on, as a bus is for a board that takes commands.
    struct Board;

    impl Member for Board {
        fn reaches(&self, _channel: &str, exchange: Exchange) -> Result<bool, Error> {
            Ok(exchange == Exchange::Sent)
        }
        fn listen(&self, _channel: &str, _inbox: Inbox) -> Result<(), Error> {
            Ok(())
        }
        fn send(&self, _channel: &str, _payload: &[u8], _reply: Option<Inbox>) -> Result<(), Error> {
            Ok(())
        }
    }

    #[test]
    fn a_reading_is_said_due_when_it_lapses_and_again_a_minute_on_while_none_comes() {
        let store = pot();
        received(&store, ME, PROBE, br#"{"value": 0.2}"#, now()).unwrap();
        let mut part = Observer::new(&store).unwrap();
        let mut members = Members::default();
        members.add(Arc::new(Board));
        part.request(&members).unwrap();
        let events = orexis::task::Events::new(&store);
        let said: Arc<Mutex<Vec<Vec<String>>>> = Arc::default();
        let into = said.clone();
        events.watch().connect(move |event, _| {
            if let Some(due) = orexis::events::as_of::<ReadingLapsed>(event) {
                into.lock().unwrap().push(due.sensors.clone());
            }
        });
        let lapse = plus(now(), CADENCE * (1.0 + GRACE));
        let mut turn = events.turn(now(), ME);
        part.due(&mut turn).unwrap();
        assert_eq!(
            turn.next(),
            Some(lapse),
            "nothing due: it waits for the reading to lapse"
        );
        let mut turn = events.turn(lapse, ME);
        part.due(&mut turn).unwrap();
        let again = plus(lapse, default_of(ASKED_AGAIN_AFTER_S_TERM).unwrap() as f64);
        assert_eq!(turn.next(), Some(again), "said due, and again a minute on");
        let mut turn = events.turn(plus(lapse, 30.0), ME);
        part.due(&mut turn).unwrap();
        assert_eq!(turn.next(), Some(again), "not before");
        assert_eq!(
            *said.lock().unwrap(),
            [vec![PROBE.to_string()]],
            "said once, naming the probe"
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
