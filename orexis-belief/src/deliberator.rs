//! THE DELIBERATOR: the belief package's pass, as `agent/belief/deliberator.py` sequences it.
//!
//! **WHAT IT OWNS IS A QUEUE.** A writer that wrote a graph says so, `changed(source)`, and nothing happens there;
//! `deliberate()` is the pass, which takes every source in the queue in turn, spending at most a budget of rule
//! executions across them, and answers what it spent. An arrival is concluded on before it is transitioned on: it is
//! revised until its rules settle, then the transitions it triggers are applied, once, in their orders. One done
//! with both leaves the queue; one the budget cut short stays, its revision graph's row saying `belief:settled
//! false`, and the next pass continues it.
//!
//! **ARRIVALS ARE TRANSITIONED ON IN TURN.** A later arrival may be revised while an earlier one is cut short, but
//! its transitions wait until every arrival queued before it has had its own — unless the earlier triggers none.
//!
//! **A CUT SURVIVES A RESTART.** As the package starts every revision graph whose row says it did not settle is
//! queued again, read off the catalogue (`resume`).
//!
//! **WHAT A PASS REVISED IS SAID** to whoever watches the agent, and with it the revisions the catalogue holds and how
//! many are unsettled, which only the metrics hear (`events.rs`).

use std::time::Instant;

use oxigraph::model::NamedNode;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::events::Watch;
use orexis::ontology::{BELIEF, ONTOLOGY, RECORD, SELF_GRAPH};
use orexis::store::{Store, Within, iri, value};
use orexis::task::{Heard, Turn};

use crate::events::{Revised, RevisionsHeld};
use crate::ontology::{INTO, REVISES, REVISING, REVISION_GRAPH, SETTLED, revision_graph};
use crate::revise::{self, revise, say_settled};
use crate::trigger::trigger;

/// THE DELIBERATOR THE SELF PLAYS, IN ONE QUERY: the default belief's ontology states on the role's shape
/// (`sh:defaultValue`), how many values the roles the self plays state, and one of them. Whichever role states it:
/// a domain's role beneath the deliberator is one too.
const DELIBERATOR_Q: &str = "SELECT ?own (COUNT(DISTINCT ?said) AS ?stated) (SAMPLE(?said) AS ?one) WHERE { \
?shape sh:targetClass <http://example.org/orexis/belief#Deliberator> ; sh:property ?property . \
?property sh:path <http://example.org/orexis/belief#budget> ; sh:defaultValue ?own . \
OPTIONAL { ?me a orexis:Self ; orexis:plays ?role . ?role <http://example.org/orexis/belief#budget> ?said } } \
GROUP BY ?own";

/// EVERY SOURCE WHOSE RULES DID NOT SETTLE, off the revision graphs' rows.
const UNSETTLED_Q: &str = "
SELECT ?source WHERE { GRAPH $cat { ?g $settled false ; prov:wasDerivedFrom ?source } } ORDER BY ?source";

/// THE REVISIONS THE CATALOGUE DESCRIBES, and how many are unsettled.
const HELD_Q: &str = "
SELECT (COUNT(?g) AS ?revisions) (SUM(IF(?settled, 0, 1)) AS ?unsettled)
WHERE { GRAPH $cat { ?g a $revision ; $settled ?settled } }";

/// A source queued: what stands beside it — None for the beliefs holding at the pass's instant — whether its
/// revision has settled, how many orders of its transitions are applied, whether its row was said unsettled for
/// its transitions, and the kind its revisions are.
#[derive(Clone, Debug)]
struct Arrival {
    read: Option<Vec<String>>,
    revised: bool,
    done: usize,
    said: bool,
    kind: String,
}

impl Arrival {
    fn new(read: Option<Vec<String>>, kind: &str) -> Self {
        Arrival {
            read,
            revised: false,
            done: 0,
            said: false,
            kind: kind.to_string(),
        }
    }
}

/// THE DELIBERATOR THE SELF PLAYS: the pass over what was written since the last one, within the budget its role
/// states.
pub struct Deliberator {
    pub(crate) beliefs: Store,
    /// Rule executions one pass may spend (`belief:budget`), and the default the ontology states where the role
    /// states none.
    pub budget: usize,
    /// Rule executions one source's revision may spend in a pass.
    pub per_source: usize,
    /// Source to where it stands, in the order changes arrived.
    queue: Vec<(String, Arrival)>,
    /// Whoever watches the agent.
    pub watch: Watch,
}

impl Deliberator {
    /// The deliberator the self plays, read off the store in one query: what its role says and, where it says
    /// nothing, the default belief's ontology states. Refused where the store holds no such default, the ontology
    /// being what the package brings as it joins.
    pub fn new(beliefs: &Store) -> Result<Self, Error> {
        let mut known = beliefs.graphs_of(&[SELF_GRAPH], &Within::default())?;
        known.extend(beliefs.graphs_of(&[ONTOLOGY], &Within::default())?);
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = beliefs.rows(DELIBERATOR_Q, &known)?;
        let [row] = rows.as_slice() else {
            return Err(Error::Document(format!(
                "belief's ontology states {} defaults for a deliberator's budget, and one is the default",
                rows.len()
            )));
        };
        let figure = |what: &str| value(row, what).and_then(|n| n.parse::<f64>().ok());
        let own = figure("own").ok_or_else(|| Error::Document("a deliberator's default budget is no number".into()))?;
        //  TWO ANSWERS ARE NEVER PICKED BETWEEN: several, or one that is no number, is the default, said in the log.
        let budget = match (figure("stated"), figure("one")) {
            (Some(0.0), _) => own,
            (Some(1.0), Some(one)) => one,
            _ => {
                log::warn!(
                    "the self's roles state no one number for a deliberator's budget: the default, {own}, holds"
                );
                own
            }
        };
        Ok(Deliberator {
            beliefs: beliefs.clone(),
            budget: budget as usize,
            per_source: revise::BUDGET,
            queue: Vec::new(),
            watch: Watch::default(),
        })
    }

    /// WHAT A BUDGET CUT SHORT BEFORE THIS DELIBERATOR WAS MADE is taken up again: every revision graph whose row
    /// says it did not settle is queued, read off the catalogue, so a cut survives a restart.
    pub(crate) fn resume(&mut self) -> Result<(), Error> {
        for source in self.unsettled()? {
            if !self.queue.iter().any(|(queued, _)| *queued == source) {
                self.queue.push((source, Arrival::new(None, BELIEF)));
            }
        }
        Ok(())
    }

    /// A graph was written: take it on the next pass, revised beside `read` where the writer says what stands, its
    /// revisions classified `kind`. Written again before it was done, it is a new arrival at the end of the queue.
    pub fn changed(&mut self, source: &str, read: Option<Vec<String>>, kind: &str) {
        self.queue.retain(|(s, _)| s != source);
        self.queue.push((source.to_string(), Arrival::new(read, kind)));
    }

    /// Revise `graphs` beside what the world states and apply the transitions each triggers, now — their revisions
    /// classified `kind`.
    pub fn revise(&mut self, graphs: &[String], kind: &str, at: DateTime) -> Result<(), Error> {
        let stated = self.beliefs.graphs_of(&[BELIEF], &Within::common())?;
        for graph in graphs {
            self.changed(graph, Some(stated.clone()), kind);
        }
        self.deliberate(at)?;
        Ok(())
    }

    /// What the next pass will take, in order.
    pub fn pending(&self) -> Vec<String> {
        self.queue.iter().map(|(s, _)| s.clone()).collect()
    }

    /// Take every queued source in turn — revise it, then apply the transitions it triggers — spending at most the
    /// budget across them: what the pass spent.
    pub fn deliberate(&mut self, at: DateTime) -> Result<usize, Error> {
        let started = Instant::now();
        let mut left = self.budget as i64;
        let mut spent = 0;
        let handed = self.queue.len();
        let mut done: Vec<String> = Vec::new();
        let mut changed: Vec<String> = Vec::new();
        let mut waiting = false;
        let mut i = 0;
        while i < self.queue.len() {
            if left <= 0 {
                break;
            }
            let source = self.queue[i].0.clone();
            if !self.queue[i].1.revised {
                let read = match &self.queue[i].1.read {
                    Some(read) => read.clone(),
                    None => self.beliefs.graphs_of(
                        &[BELIEF, RECORD],
                        &Within {
                            at: Some(at),
                            now: Some(at),
                            ..Within::default()
                        },
                    )?,
                };
                let share = (left as usize).min(self.per_source);
                let kind = self.queue[i].1.kind.clone();
                let used = revise(&self.beliefs, &source, &read, share, &kind)?;
                done.push(source.clone());
                spent += used;
                left -= used as i64;
                if self.unsettled()?.contains(&source) {
                    //  CUT IN ITS REVISION: the arrivals after it wait for its transitions — where it triggers any.
                    let arrival = &mut self.queue[i].1;
                    arrival.read = Some(read);
                    waiting = waiting || !trigger(&self.beliefs, &source, 0, arrival.done)?.finished;
                    i += 1;
                    continue;
                }
                self.queue[i].1.revised = true;
            }
            let budget = if waiting { 0 } else { left.max(0) as usize };
            let triggered = trigger(&self.beliefs, &source, budget, self.queue[i].1.done)?;
            spent += triggered.spent;
            left -= triggered.spent as i64;
            if triggered.spent > 0 && !done.contains(&source) {
                done.push(source.clone());
            }
            for g in triggered.changed {
                if !changed.contains(&g) {
                    changed.push(g);
                }
            }
            if !triggered.finished {
                self.queue[i].1.done = triggered.done;
                self.say(i, false)?;
                waiting = true;
                i += 1;
                continue;
            }
            if self.queue[i].1.said {
                self.say(i, true)?;
            }
            self.queue.remove(i);
        }
        if spent > 0 {
            log::debug!("{spent} execution(s), {} pending", self.queue.len());
        }
        if handed > 0 {
            let revised = Revised {
                graphs: done,
                changed,
                sources: handed,
                executions: spent,
                cut: self.queue.len(),
                duration_s: (started.elapsed().as_secs_f64() * 1e6).round() / 1e6,
            };
            if self.watch.connected() {
                self.watch.emit(&revised);
                let held = self.held()?;
                self.watch.emit(&held);
            }
        }
        Ok(spent)
    }

    /// The revisions the catalogue describes now, and how many are unsettled.
    pub fn held(&self) -> Result<RevisionsHeld, Error> {
        let Some(cat) = self.beliefs.catalogue()? else {
            return Ok(RevisionsHeld::default());
        };
        let found = self.beliefs.rows(
            &bind(
                HELD_Q,
                &[
                    ("cat", Value::iri(cat)),
                    ("revision", Value::iri(REVISION_GRAPH)),
                    ("settled", Value::iri(SETTLED)),
                ],
            )?,
            &[],
        )?;
        let count = |key: &str| {
            found
                .first()
                .and_then(|r| orexis::store::value(r, key))
                .and_then(|v| v.parse().ok())
                .unwrap_or(0)
        };
        Ok(RevisionsHeld {
            revisions: count("revisions"),
            unsettled: count("unsettled"),
        })
    }

    /// Say on the source's revision row whether it is done, so a restart continues an arrival whose transitions
    /// waited or were cut — where a row stands.
    fn say(&mut self, i: usize, settled: bool) -> Result<(), Error> {
        let (source, arrival) = &mut self.queue[i];
        if arrival.said != settled {
            return Ok(());
        }
        if let Some(cat) = self.beliefs.catalogue()? {
            say_settled(&self.beliefs, &cat, &revision_graph(source), settled)?;
        }
        arrival.said = !settled;
        Ok(())
    }

    fn unsettled(&self) -> Result<Vec<String>, Error> {
        let Some(cat) = self.beliefs.catalogue()? else {
            return Ok(Vec::new());
        };
        Ok(self
            .beliefs
            .rows(
                &bind(
                    UNSETTLED_Q,
                    &[("cat", Value::iri(cat)), ("settled", Value::iri(SETTLED))],
                )?,
                &[],
            )?
            .iter()
            .filter_map(|r| iri(r, "source"))
            .collect())
    }

    //  THE PACKAGE'S POLICY: what the deliberator revises as the package starts and on what it hears.

    /// Revise `graphs` as an activity, triggered by them.
    pub(crate) fn revising(&mut self, graphs: &[String], kind: &str, pass: &mut Turn<'_>) -> Result<(), Error> {
        let triggers: Vec<NamedNode> = graphs.iter().filter_map(|g| NamedNode::new(g.as_str()).ok()).collect();
        let activity = pass.begin(REVISING, &triggers);
        let revised = self.revise(graphs, kind, pass.now);
        pass.end(activity);
        revised
    }

    /// What is unrevised as the package starts, revised once, with what a budget cut short before it.
    pub(crate) fn unrevised(&mut self, now: DateTime) -> Result<(), Error> {
        self.resume()?;
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
    pub(crate) fn heard_event(&mut self, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
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
    //! The deliberator, held as `agent/belief/tests/test_deliberator.py` holds it: over the `revise/` cases for the
    //! sequencing, and over a counter and its ticks for an arrival concluded on, then transitioned on.

    use std::collections::BTreeMap;

    use orexis::snapshots;
    use oxsdatatypes::DayTimeDuration;

    use std::sync::{Arc, Mutex};

    use super::*;
    use crate::trigger::trigger as triggered;
    use orexis::ontology::CATALOGUE_GRAPH;

    const SENSED: &str = "http://example.org/test#sensed";
    const T: &str = "http://example.org/test#";
    const COUNTER_Q: &str = "SELECT ?p ?o WHERE { <http://example.org/test#counter> ?p ?o FILTER(?p != rdf:type) }";
    const OWN_STATE_Q: &str = "SELECT ?g WHERE { GRAPH ?c { ?c a orexis:CatalogueGraph .
    ?g a orexis:BeliefGraph ; orexis:arrivedBy orexis:Derived .
    FILTER NOT EXISTS { ?g a belief:RevisionGraph } ?g orexis:ownedBy ?owner . } } ORDER BY ?g";

    /// `store` with belief's ontology in it, as the package brings it when it joins: the deliberator's shape, whose
    /// default the role's budget is where no role states one.
    fn with_ontology(store: Store) -> Store {
        let ontology = orexis::document::Document::read(&snapshots::tree().join("orexis-belief/ontology.ttl")).unwrap();
        store.put_document(&ontology, None, None, None, true).unwrap();
        store
    }

    fn revise_case(name: &str) -> Store {
        with_ontology(snapshots::stand_in(
            &snapshots::tree().join(format!("orexis-belief/tests/revise/{name}.trig")),
        ))
    }

    fn ticks() -> Store {
        with_ontology(snapshots::stand_in(
            &snapshots::tree().join("orexis-belief/tests/worlds/a_counter_and_its_ticks.trig"),
        ))
    }

    fn row_settled(store: &Store, graph: &str) -> Option<String> {
        let found = store
            .rows(
                &format!("SELECT ?v WHERE {{ GRAPH ?c {{ <{graph}/revisions> <{SETTLED}> ?v }} }}"),
                &[],
            )
            .unwrap();
        found.first().and_then(|r| orexis::store::value(r, "v"))
    }

    fn concluded(store: &Store) -> Vec<String> {
        store
            .rows(
                &format!("SELECT ?p WHERE {{ GRAPH <{SENSED}/revisions> {{ ?s ?p ?o }} }}"),
                &[],
            )
            .unwrap()
            .iter()
            .filter_map(|r| iri(r, "p"))
            .collect()
    }

    fn minutes(n: i64) -> DateTime {
        snapshots::now()
            .checked_add_day_time_duration(DayTimeDuration::new(60 * n))
            .unwrap()
    }

    /// A tick arrived: its own graph, received and the keeper's, holding twenty minutes from `start`.
    fn tick(store: &Store, name: &str, start: DateTime, loud: bool) -> String {
        let graph = format!("{T}{name}");
        let end = start
            .checked_add_day_time_duration(DayTimeDuration::new(20 * 60))
            .unwrap();
        let entry = store
            .entry(
                &graph,
                &[&format!("{T}TickGraph")],
                "http://example.org/orexis#Received",
                Some(&format!("{T}keeper")),
                Some(start),
                Some(end),
            )
            .unwrap();
        let loudly = if loud {
            format!("; <{T}loud> true")
        } else {
            String::new()
        };
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{graph}> {{ <{T}{name}_t> a <{T}Tick> {loudly} }} {entry} }}"
            ))
            .unwrap();
        graph
    }

    fn own_state(store: &Store) -> Vec<String> {
        store
            .rows(OWN_STATE_Q, &[])
            .unwrap()
            .iter()
            .filter_map(|r| iri(r, "g"))
            .collect()
    }

    fn counter_in(store: &Store, graphs: &[String]) -> BTreeMap<String, String> {
        let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
        store
            .rows(COUNTER_Q, &graphs)
            .unwrap()
            .iter()
            .map(|r| {
                let local = |k: &str| {
                    orexis::store::value(r, k)
                        .unwrap()
                        .rsplit('#')
                        .next()
                        .unwrap()
                        .to_string()
                };
                (local("p"), local("o"))
            })
            .collect()
    }

    fn counter(store: &Store) -> BTreeMap<String, String> {
        counter_in(store, &own_state(store))
    }

    fn map(items: &[(&str, &str)]) -> BTreeMap<String, String> {
        items.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect()
    }

    #[test]
    fn a_changed_source_is_revised_on_the_pass_and_leaves_the_queue() {
        let store = revise_case("a_reading_below_its_range_is_concluded_below");
        let mut deliberator = Deliberator::new(&store).unwrap();
        deliberator.changed(SENSED, None, BELIEF);
        assert_eq!(deliberator.pending(), [SENSED]);
        assert!(deliberator.deliberate(snapshots::now()).unwrap() > 0);
        assert!(deliberator.pending().is_empty());
        assert!(!concluded(&store).is_empty());
        assert_eq!(row_settled(&store, SENSED).as_deref(), Some("true"));
    }

    #[test]
    fn nothing_changed_spends_nothing_and_says_nothing() {
        let store = revise_case("a_reading_below_its_range_is_concluded_below");
        let heard = std::sync::Arc::new(std::sync::atomic::AtomicUsize::new(0));
        let mut deliberator = Deliberator::new(&store).unwrap();
        let into = heard.clone();
        deliberator.watch.connect(move |event, _| {
            if orexis::events::as_of::<Revised>(event).is_some() {
                into.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
            }
        });
        assert_eq!(deliberator.deliberate(snapshots::now()).unwrap(), 0);
        assert_eq!(heard.load(std::sync::atomic::Ordering::SeqCst), 0);
    }

    #[test]
    fn a_budget_cuts_the_pass_and_the_next_continues() {
        let store = revise_case("a_chain_settles_in_a_later_round");
        let mut deliberator = Deliberator::new(&store).unwrap();
        deliberator.budget = 2;
        deliberator.changed(SENSED, None, BELIEF);
        assert_eq!(deliberator.deliberate(snapshots::now()).unwrap(), 2);
        assert_eq!(deliberator.pending(), [SENSED]);
        assert_eq!(row_settled(&store, SENSED).as_deref(), Some("false"));
        deliberator.budget = 64;
        assert!(deliberator.deliberate(snapshots::now()).unwrap() > 0);
        assert!(deliberator.pending().is_empty());
        assert_eq!(row_settled(&store, SENSED).as_deref(), Some("true"));
        let said: std::collections::BTreeSet<String> = concluded(&store)
            .iter()
            .map(|p| p.rsplit('#').next().unwrap().to_string())
            .collect();
        assert_eq!(said, ["isDry", "side"].map(String::from).into());
    }

    #[test]
    fn the_budget_is_the_deliberators_roles_where_one_states_it() {
        let store = revise_case("a_chain_settles_in_a_later_round");
        assert_eq!(Deliberator::new(&store).unwrap().budget, 256);
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{T}self> {{ <{T}keeper> a orexis:Self ; orexis:plays [ <http://example.org/orexis/belief#budget> 2 ] }} {} }}",
                store
                    .entry(
                        &format!("{T}self"),
                        &[orexis::ontology::SELF_GRAPH],
                        orexis::ontology::ASSERTED,
                        Some(&format!("{T}keeper")),
                        None,
                        None
                    )
                    .unwrap()
            ))
            .unwrap();
        let mut deliberator = Deliberator::new(&store).unwrap();
        deliberator.changed(SENSED, None, BELIEF);
        assert_eq!(deliberator.deliberate(snapshots::now()).unwrap(), 2);
        assert_eq!(deliberator.pending(), [SENSED]);
    }

    #[test]
    fn a_cut_survives_a_new_deliberator_over_the_store() {
        let store = revise_case("a_chain_settles_in_a_later_round");
        let mut first = Deliberator::new(&store).unwrap();
        first.budget = 2;
        first.changed(SENSED, None, BELIEF);
        first.deliberate(snapshots::now()).unwrap();
        let mut second = Deliberator::new(&store).unwrap();
        second.resume().unwrap();
        assert_eq!(second.pending(), [SENSED], "the row said the rules did not settle");
        second.deliberate(snapshots::now()).unwrap();
        assert!(second.pending().is_empty());
        assert_eq!(row_settled(&store, SENSED).as_deref(), Some("true"));
    }

    #[test]
    fn an_arrival_is_revised_before_its_transitions_run_and_both_are_spent_from_one_budget() {
        let store = ticks();
        let early = tick(&store, "early", snapshots::now(), true);
        triggered(&store, &early, revise::BUDGET, 0).unwrap();
        assert!(
            !counter(&store).contains_key("count"),
            "nothing the transition reads is concluded yet"
        );
        let store = ticks();
        let mut deliberator = Deliberator::new(&store).unwrap();
        deliberator.changed(&tick(&store, "first", snapshots::now(), true), None, BELIEF);
        assert_eq!(deliberator.deliberate(snapshots::now()).unwrap(), 5);
        assert_eq!(
            counter(&store),
            map(&[("count", "1"), ("echo", "1"), ("last", "first_t")])
        );
        assert!(deliberator.pending().is_empty());
    }

    #[test]
    fn arrivals_are_transitioned_on_in_turn_whatever_the_budget_cuts() {
        let store = ticks();
        let mut deliberator = Deliberator::new(&store).unwrap();
        deliberator.budget = 50;
        deliberator.per_source = 1;
        let loud = tick(&store, "loud", snapshots::now(), true);
        let quiet = tick(&store, "quiet", minutes(1), false);
        deliberator.changed(&loud, None, BELIEF);
        deliberator.changed(&quiet, None, BELIEF);
        deliberator.deliberate(snapshots::now()).unwrap();
        assert_eq!(deliberator.pending(), [loud.clone(), quiet.clone()]);
        assert!(
            counter(&store).is_empty(),
            "nothing transitioned while the first arrival is cut"
        );
        assert_eq!(row_settled(&store, &loud).as_deref(), Some("false"));
        deliberator.deliberate(snapshots::now()).unwrap();
        assert!(deliberator.pending().is_empty());
        assert_eq!(
            counter(&store),
            map(&[("count", "1"), ("echo", "1"), ("last", "quiet_t")])
        );
        assert_eq!(row_settled(&store, &loud).as_deref(), Some("true"));
        let held: BTreeMap<String, Vec<String>> = own_state(&store)
            .into_iter()
            .map(|g| {
                let said = counter_in(&store, std::slice::from_ref(&g)).into_keys().collect();
                (g.rsplit('#').next().unwrap().to_string(), said)
            })
            .collect();
        assert_eq!(
            held,
            BTreeMap::from([
                ("loud/believed".to_string(), vec!["count".to_string()]),
                (
                    "quiet/believed".to_string(),
                    vec!["echo".to_string(), "last".to_string()]
                ),
            ])
        );
    }

    #[test]
    fn an_arrival_that_triggers_nothing_holds_no_turn() {
        let store = ticks();
        let note = format!("{T}note");
        let entry = store
            .entry(
                &note,
                &[orexis::ontology::FORECAST],
                orexis::ontology::DERIVED,
                Some(&format!("{T}keeper")),
                None,
                None,
            )
            .unwrap();
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{note}> {{ <{T}note_t> a <{T}Tick> ; <{T}loud> true }} {entry} }}"
            ))
            .unwrap();
        let mut deliberator = Deliberator::new(&store).unwrap();
        deliberator.budget = 50;
        deliberator.per_source = 1;
        deliberator.changed(&note, None, BELIEF);
        let quiet = tick(&store, "quiet", snapshots::now(), false);
        deliberator.changed(&quiet, None, BELIEF);
        deliberator.deliberate(snapshots::now()).unwrap();
        assert_eq!(deliberator.pending(), [note], "the note is cut, and the tick done");
        assert_eq!(counter(&store), map(&[("last", "quiet_t")]));
    }

    #[test]
    fn a_graph_written_again_is_a_new_arrival_at_the_end_of_the_queue() {
        let store = ticks();
        let mut deliberator = Deliberator::new(&store).unwrap();
        deliberator.budget = 50;
        deliberator.per_source = 1;
        let loud = tick(&store, "loud", snapshots::now(), true);
        deliberator.changed(&loud, None, BELIEF);
        let quiet = tick(&store, "quiet", minutes(1), false);
        deliberator.changed(&quiet, None, BELIEF);
        deliberator.deliberate(snapshots::now()).unwrap();
        store.forget_graph(&loud, Some(BELIEF)).unwrap();
        let again = tick(&store, "loud", minutes(2), true);
        deliberator.changed(&again, None, BELIEF);
        assert_eq!(deliberator.pending(), [quiet, loud.clone()]);
        for _ in 0..5 {
            deliberator.deliberate(snapshots::now()).unwrap();
        }
        assert!(deliberator.pending().is_empty());
        assert_eq!(counter(&store)["last"], "loud_t");
        let found = store
            .rows(
                &format!("SELECT ?s WHERE {{ GRAPH ?c {{ <{loud}/believed> dcterms:temporal/orexis:start ?s }} }}"),
                &[],
            )
            .unwrap();
        assert!(
            orexis::store::value(&found[0], "s")
                .unwrap()
                .starts_with("2026-01-01T12:02"),
            "the later loud tick's period"
        );
    }

    #[test]
    fn transitions_a_budget_left_waiting_survive_a_new_deliberator() {
        let store = ticks();
        let first_tick = tick(&store, "first", snapshots::now(), true);
        let mut first = Deliberator::new(&store).unwrap();
        first.budget = 2;
        first.changed(&first_tick, None, BELIEF);
        assert_eq!(first.deliberate(snapshots::now()).unwrap(), 2);
        assert_eq!(first.pending(), std::slice::from_ref(&first_tick));
        assert!(counter(&store).is_empty());
        assert_eq!(row_settled(&store, &first_tick).as_deref(), Some("false"));
        let mut second = Deliberator::new(&store).unwrap();
        second.resume().unwrap();
        assert_eq!(
            second.pending(),
            std::slice::from_ref(&first_tick),
            "the row said the arrival was not done"
        );
        second.deliberate(snapshots::now()).unwrap();
        assert!(second.pending().is_empty());
        assert_eq!(row_settled(&store, &first_tick).as_deref(), Some("true"));
        assert_eq!(
            counter(&store),
            map(&[("count", "1"), ("echo", "1"), ("last", "first_t")])
        );
    }

    #[test]
    fn a_cut_between_orders_is_continued_from_the_order_it_stopped_at() {
        let store = ticks();
        let mut deliberator = Deliberator::new(&store).unwrap();
        deliberator.budget = 3;
        deliberator.changed(&tick(&store, "first", snapshots::now(), true), None, BELIEF);
        assert_eq!(deliberator.deliberate(snapshots::now()).unwrap(), 4);
        assert_eq!(counter(&store), map(&[("count", "1"), ("last", "first_t")]));
        assert_eq!(deliberator.deliberate(snapshots::now()).unwrap(), 1);
        assert!(deliberator.pending().is_empty());
        assert_eq!(
            counter(&store),
            map(&[("count", "1"), ("echo", "1"), ("last", "first_t")])
        );
    }

    fn bare() -> Store {
        let store = Store::new(snapshots::namespaces()).unwrap();
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph }} }}"
            ))
            .unwrap();
        with_ontology(store)
    }

    #[test]
    fn its_part_hears_beliefs_written_and_says_each_pass_revised() {
        let store = bare();
        let mut part = Deliberator::new(&store).unwrap();
        let heard = Arc::new(Mutex::new(Vec::new()));
        let into = heard.clone();
        part.watch.connect(move |event, _| {
            if let Some(r) = orexis::events::as_of::<Revised>(event) {
                into.lock().unwrap().extend(r.graphs.clone());
            }
        });
        part.unrevised(snapshots::now()).unwrap();
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
        let mut part = Deliberator::new(&store).unwrap();
        part.revise(&["urn:test:reading".to_string()], BELIEF, snapshots::now())
            .unwrap();
        assert!(part.pending().is_empty());
        let mut deliberator = Deliberator::new(&store).unwrap();
        deliberator.budget = 0;
        let stated = store.graphs_of(&[BELIEF], &Within::common()).unwrap();
        assert_eq!(stated, ["urn:test:world"], "the common beliefs alone stand beside it");
        deliberator.changed("urn:test:observed", Some(stated), "urn:test:ObservedGraph");
        assert_eq!(deliberator.pending(), ["urn:test:observed"]);
    }
}
