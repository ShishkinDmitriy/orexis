//! THE COORDINATOR, the package's core: the role the self plays, read off its self graph, and what it does of a
//! trigger heard, a question or an answer arrived, and the pass - ask the peers in range, answer them, conclude the
//! conflicts and lay what it yields to.

use std::collections::{BTreeMap, BTreeSet};

use orexis::Error;
use orexis::document::Document;
use orexis::events::Watch;
use orexis::ontology::local_of;
use orexis::ontology::{ONTOLOGY, SELF_GRAPH};
use orexis::store::{Store, Within, value};
use orexis::task::{Heard, Turn};
use oxsdatatypes::DateTime;

use crate::answer::answer;
use crate::ask::ask;
use crate::conclude::{conclude, conflicts, wins};
use crate::events::{ASKED, Concluded, DrawWon, FORESEEN, Held, SAID, Told};
use crate::holdings::{heard, walking_over};
use crate::lay::{laid, lay};
use crate::mint::mint;
use crate::ontology::{COORDINATING, COORDINATION};

pub(crate) const PASS: usize = 0;
pub(crate) const QUESTIONED: usize = 1;
pub(crate) const ANSWERED: usize = 2;
const MINTED: usize = 3;

/// THE COORDINATOR THE SELF PLAYS, the package's core: a field for each thing `coordination:Coordinator` may state,
/// one to one, each what the role says in the agent's self graph and, where it says nothing, the default this
/// package's ontology states; and what it keeps between two coordinatings.
pub struct Coordinator {
    /// How many seconds a draw may stand undecided, and a question holds (`coordination:patienceS`).
    pub patience_s: f64,
    /// How many rounds a conflict's draw may restart before the peer is taken as silent (`coordination:rounds`).
    pub rounds: f64,
    /// How many of a silent peer's steps the agent looks ahead (`coordination:lookahead`).
    pub lookahead: i64,
    beliefs: Store,
    me: String,
    pending: Vec<String>,
    /// Whoever watches the agent.
    pub watch: Watch,
    /// What was last said of each set, so a set is said where it changed.
    told: BTreeMap<(String, String, String), Vec<crate::holdings::Holding>>,
    concluded: Option<Vec<crate::events::Conflict>>,
    /// The events heard beneath its trigger since it last coordinated.
    triggers: Vec<oxigraph::model::NamedNode>,
    /// Whether it has coordinated yet, when it last asked anything, and the instant a patience running calls for it
    /// next, while it is asking or in conflict.
    started: bool,
    asked: Option<DateTime>,
    next: Option<DateTime>,
}

impl Coordinator {
    /// The coordinator the self plays, read off the store in one query: what its role says and, where it says
    /// nothing, the default coordination's ontology states. THE SELF GRAPH WAS HELD TO ITS REQUIREMENTS AT
    /// ONBOARDING (`requirements.ttl`), so each figure is stated once at most; nothing is picked between here.
    /// Refused where the store states no default, the ontology being what the package brings as it joins.
    pub fn new(store: &Store) -> Result<Self, Error> {
        /// THE COORDINATOR THE SELF PLAYS, IN ONE QUERY: the self, and each figure the role says or, where it says
        /// none, the default the coordination's ontology states on its shape of the role (`sh:defaultValue`).
        const COORDINATOR_Q: &str = "PREFIX orexis: <http://example.org/orexis#> PREFIX sh: <http://www.w3.org/ns/shacl#> SELECT DISTINCT ?me (COALESCE(?patienceSaid, ?patienceOwn) AS ?patience) \
        (COALESCE(?roundsSaid, ?roundsOwn) AS ?rounds) (COALESCE(?lookaheadSaid, ?lookaheadOwn) AS ?lookahead) WHERE { \
        ?shape sh:targetClass <http://example.org/orexis/coordination#Coordinator> ; \
          sh:property [ sh:path <http://example.org/orexis/coordination#patienceS> ; sh:defaultValue ?patienceOwn ] , \
                      [ sh:path <http://example.org/orexis/coordination#rounds> ; sh:defaultValue ?roundsOwn ] , \
                      [ sh:path <http://example.org/orexis/coordination#lookahead> ; sh:defaultValue ?lookaheadOwn ] . \
        OPTIONAL { ?me a orexis:Self } \
        OPTIONAL { ?me orexis:plays ?r1 . ?r1 <http://example.org/orexis/coordination#patienceS> ?patienceSaid } \
        OPTIONAL { ?me orexis:plays ?r2 . ?r2 <http://example.org/orexis/coordination#rounds> ?roundsSaid } \
        OPTIONAL { ?me orexis:plays ?r3 . ?r3 <http://example.org/orexis/coordination#lookahead> ?lookaheadSaid } }";
        let mut known = store.graphs_of(&[SELF_GRAPH], &Within::default())?;
        known.extend(store.graphs_of(&[ONTOLOGY], &Within::default())?);
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let row = store
            .rows(COORDINATOR_Q, &known)?
            .into_iter()
            .next()
            .ok_or_else(|| Error::Document("the store states no coordinator's figures, and no default".into()))?;
        let number = |name: &str| {
            value(&row, name)
                .and_then(|said| said.parse::<f64>().ok())
                .ok_or_else(|| Error::Document(format!("a coordinator's {name} is no number")))
        };
        let lookahead = value(&row, "lookahead")
            .and_then(|said| said.parse::<i64>().ok())
            .ok_or_else(|| Error::Document("a coordinator's lookahead is no whole number".into()))?;
        Ok(Coordinator {
            patience_s: number("patience")?,
            rounds: number("rounds")?,
            lookahead,
            beliefs: store.clone(),
            me: value(&row, "me").unwrap_or_default(),
            pending: Vec::new(),
            watch: Watch::default(),
            told: BTreeMap::new(),
            concluded: None,
            triggers: Vec::new(),
            started: false,
            asked: None,
            next: None,
        })
    }

    /// The secret its draws' numbers come from, minted as it starts and written at its first turn.
    pub(crate) fn mint(&mut self) -> Result<(), Error> {
        self.pending.extend(mint(&self.beliefs, &self.me)?);
        Ok(())
    }

    fn said(&mut self, peer: &str, document: &Document, at: DateTime) -> Result<Vec<String>, Error> {
        if self.watch.connected() {
            let scratch = Store::new()?;
            scratch
                .engine()
                .extend(document.quads().iter().cloned())
                .map_err(|e| Error::Evaluation(e.to_string()))?;
            let over = format!("{COORDINATION}over");
            let mut asked: BTreeMap<String, String> = BTreeMap::new();
            for q in document.quads() {
                if q.predicate.as_str() == over
                    && let (oxigraph::model::GraphName::NamedNode(g), oxigraph::model::Term::NamedNode(c)) =
                        (&q.graph_name, &q.object)
                {
                    asked
                        .entry(g.as_str().to_string())
                        .or_insert_with(|| c.as_str().to_string());
                }
            }
            for (graph, constraint) in asked {
                let holdings = heard(&scratch, &graph)?;
                self.tell_held(Held {
                    at,
                    origin: ASKED,
                    peer: peer.to_string(),
                    constraint,
                    holdings,
                });
            }
        }
        let graphs: Vec<String> = document.kinds().into_keys().collect();
        log::info!(
            "{}: says {} to {}",
            local_of(&self.me),
            graphs
                .iter()
                .map(|g| g.split("/coordination/").last().unwrap_or(g))
                .collect::<Vec<_>>()
                .join(", "),
            local_of(peer)
        );
        let statements = orexis_speech::said::said(&self.beliefs, &self.me, document)?;
        self.watch.emit(&Told {
            statements: statements.clone(),
            to: peer.to_string(),
        });
        Ok(statements)
    }

    /// When to coordinate again with nothing heard: a quarter patience on while the agent asked within the last two
    /// patiences or stands in a conflict, since a question expires and a peer turns silent by the patience alone.
    fn wait(&mut self, asking: bool, now: DateTime) -> Result<(), Error> {
        let patience = crate::ask::patience(&self.beliefs)?;
        self.started = true;
        if asking {
            self.asked = Some(now);
        }
        let recent = self
            .asked
            .and_then(|l| l.checked_add_day_time_duration(orexis::clock::seconds(2.0 * patience)))
            .is_some_and(|until| now <= until);
        let engaged = recent || !conflicts(&self.beliefs, &self.me)?.is_empty();
        self.next = if engaged {
            now.checked_add_day_time_duration(orexis::clock::seconds(patience / 4.0))
        } else {
            None
        };
        Ok(())
    }

    /// Say `event` where what it says differs from what was last said of the same set.
    fn tell_held(&mut self, event: Held) {
        let key = (event.origin.to_string(), event.peer.clone(), event.constraint.clone());
        if self.told.get(&key) != Some(&event.holdings) {
            self.told.insert(key, event.holdings.clone());
            self.watch.emit(&event);
        }
    }

    /// Conclude the conflicts and lay what the agent yields to; a draw won reopens what it decides.
    fn yielded(&mut self, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let (store, me, at) = (&self.beliefs.clone(), self.me.clone(), pass.now);
        let before = wins(store, &me)?;
        let mut written = conclude(store, &me, at)?;
        if self.watch.connected() {
            let now = conflicts(store, &me)?;
            if self.concluded.as_ref() != Some(&now) {
                self.concluded = Some(now.clone());
                self.watch.emit(&Concluded { at, conflicts: now });
            }
        }
        let won: Vec<String> = wins(store, &me)?
            .into_iter()
            .filter(|(draw, _)| !before.contains_key(draw))
            .map(|(_, constraint)| constraint)
            .collect();
        written.extend(lay(store, &me, at)?);
        if self.watch.connected() {
            for ((peer, constraint), (said, foreseen)) in laid(store, &me)? {
                for (origin, holdings) in [(SAID, said), (FORESEEN, foreseen)] {
                    self.tell_held(Held {
                        at,
                        origin,
                        peer: peer.clone(),
                        constraint: constraint.clone(),
                        holdings,
                    });
                }
            }
        }
        let mut wants = BTreeSet::new();
        for constraint in &won {
            wants.extend(walking_over(store, constraint)?);
        }
        if !wants.is_empty() {
            log::info!(
                "{}: won a draw, so asks that {} be planned again",
                local_of(&me),
                wants.iter().map(|w| local_of(w)).collect::<Vec<_>>().join(", ")
            );
            self.watch.emit(&DrawWon {
                wants: wants.into_iter().collect(),
            });
            pass.again();
        }
        Ok(written)
    }
    /// What it queued for itself, each in turn and what each wrote told, until nothing is left.
    pub(crate) fn queued(&mut self, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        loop {
            let jobs = self.submitted();
            if jobs.is_empty() {
                return Ok(Vec::new());
            }
            for job in jobs {
                let wrote = self.run(job, pass)?;
                pass.told(wrote)?;
            }
        }
    }

    /// What coordination's policy does of a trigger: coordinate at the pass.
    pub(crate) fn heard_event(
        &mut self,
        _job: usize,
        event: &Heard,
        _pass: &mut Turn<'_>,
    ) -> Result<Vec<String>, Error> {
        self.triggers.push(event.node.clone());
        Ok(Vec::new())
    }

    pub(crate) fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        match job {
            MINTED => Ok(std::mem::take(&mut self.pending)),
            PASS => {
                //  COORDINATION'S POLICY: coordinate where a trigger was heard since, at the first pass, or where a
                //  patience it is waiting on may have run; and otherwise nothing.
                let due = !self.started || self.next.is_some_and(|n| n <= pass.now);
                if !due && self.triggers.is_empty() {
                    if let Some(next) = self.next {
                        pass.wake_at(next);
                    }
                    return Ok(Vec::new());
                }
                let triggers = std::mem::take(&mut self.triggers);
                let activity = pass.begin(COORDINATING, &triggers);
                let mut written = Vec::new();
                let asked = ask(&self.beliefs, &self.me, pass.now)?;
                let asking = !asked.is_empty();
                for (peer, document) in asked {
                    written.extend(self.said(&peer, &document, pass.now)?);
                }
                written.extend(self.yielded(pass)?);
                self.wait(asking, pass.now)?;
                if let Some(next) = self.next {
                    pass.wake_at(next);
                }
                pass.end(activity);
                Ok(written)
            }
            _ => Ok(Vec::new()),
        }
    }

    /// The questions or answers written together: each question answered, and what they make of the draws
    /// concluded once.
    pub(crate) fn heard(&mut self, job: usize, graphs: &[String], pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let mut written = Vec::new();
        if job == QUESTIONED {
            for graph in graphs {
                if let Some((peer, document)) = answer(&self.beliefs, &self.me, graph, pass.now)? {
                    written.extend(self.said(&peer, &document, pass.now)?);
                }
            }
        }
        written.extend(self.yielded(pass)?);
        Ok(written)
    }

    fn submitted(&mut self) -> Vec<usize> {
        if self.pending.is_empty() {
            Vec::new()
        } else {
            vec![MINTED]
        }
    }
}
