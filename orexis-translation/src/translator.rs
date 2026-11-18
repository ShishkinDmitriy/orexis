//! THE TRANSLATOR, the package's core: the role the self plays, read off its self graph and the world's deployment, and
//! what it does of a person's words and of what the agent says to a person - heard and answered, or phrased, through
//! the model, off the mind's thread.

use std::collections::{BTreeMap, VecDeque};
use std::sync::Arc;
use std::sync::mpsc::{Receiver, Sender, channel};
use std::time::Instant;

use oxigraph::model::NamedNode;
use oxigraph::store::Store as Engine;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::document::Document;
use orexis::events::Watch;
use orexis::ontology::local_of;
use orexis::ontology::{DEPLOYMENT, ONTOLOGY, SELF_GRAPH};
use orexis::series::Reader;
use orexis::store::{Store, Within, value};
use orexis::task::{Heard, Turn};
use orexis_speech::document_of;
use orexis_speech::ontology::{STATEMENT, TO};
use orexis_speech::prose::{KEPT, Prose, ProseKept, WritingAnnounced, prose_of, received, written};

use crate::ROLE;
use crate::briefing::briefing;
use crate::chat::{Chat, chats_of, named};
use crate::conversation::{
    Asked, Back, Conversation, Direct, EVENT, UNADDRESSED, converse, instant_block, prefixes_of, sent_as, translated,
    written_as,
};
use crate::model::Model;
use crate::past::Past;
use crate::readable::{Readable, namespaces};
use crate::stated::{PROPERTY, Stating, believe, listing, rendered, statement_of, words};

pub(crate) const BACK: usize = 0;
pub(crate) const STILL: usize = 1;
pub(crate) const TRANSLATE: usize = 2;

/// What translation does as an activity, and what starts it.
const TRANSLATING: &str = "http://example.org/orexis/translation#Translating";
pub(crate) const TRANSLATING_TRIGGER: &str = "http://example.org/orexis/translation#TranslatingTrigger";
pub(crate) const PHRASE: usize = 3;
const PHRASING: &str = "http://example.org/orexis/translation#Phrasing";
pub(crate) const PHRASING_TRIGGER: &str = "http://example.org/orexis/translation#PhrasingTrigger";

/// Provided by a test: the model is asked in the task's own turn and not on a thread of its own, so what it
/// answers is handed back before the turn ends.
pub struct Inline;

/// THE TRANSLATOR THE SELF PLAYS, the package's core: a field for each thing `translation:Translator` may state, each
/// what the role says in the agent's self graph and, where it says nothing, the default this package's ontology
/// states; and what it holds across turns: the model, what is being thought in which chat, and what the model's
/// threads handed back.
pub struct Translator {
    beliefs: Store,
    pub me: String,
    pub model: Option<Arc<dyn Model>>,
    /// Whether a conversation runs on the mind's own thread, as a test runs it, or a thread of its own.
    pub inline: bool,
    /// Each chat with an answer still being thought, and how many.
    pub writing: BTreeMap<String, (Chat, i64)>,
    pub journal: Option<Engine>,
    /// Where the journal lies, as whoever keeps it says whenever it starts: asked as a chat reads, where `journal`
    /// was set by nobody.
    pub journaled: orexis::task::Journaled,
    pub history: Option<Reader>,
    pub metrics: Option<Reader>,
    pub watch: Watch,
    /// How many turns a conversation may take, how many rows a query hands the model, and how long the model's
    /// thread waits for the mind's answer: the translator's role's figures (`translation:turns`, `rows`,
    /// `answeredWithinS`).
    pub turns: usize,
    pub rows: usize,
    pub answered_within_s: f64,
    /// How long one call of the model may take and how often a failing one is asked again (`translation:calledWithinS`,
    /// `retries`).
    pub called_within_s: f64,
    pub retries: u32,
    /// What the model is told first when it answers a person, and when it phrases what the agent says to one
    /// (`translation:conversePrompt`, `sayPrompt`).
    pub converse_prompt: String,
    pub say_prompt: String,
    /// Where the model the role names answers (`translation:translatedBy`), as the world's deployment states it: none
    /// where the role names none or the world says nothing of the one named.
    pub translated_by: Option<String>,
    tx: Sender<Back>,
    rx: Receiver<Back>,
    /// What the model's threads handed back, for the turn to do.
    pending: VecDeque<Back>,
}

impl Translator {
    /// The translator the self plays, read off the store in one query: what its role says of talking with the model,
    /// the default translation's ontology states where it says nothing, and where the model it names answers. THE
    /// SELF GRAPH WAS HELD TO ITS REQUIREMENTS AT ONBOARDING, so each figure is stated once at most; nothing is picked
    /// between here. It holds no model until it is handed one.
    pub fn new(beliefs: &Store) -> Result<Self, Error> {
        /// THE TRANSLATOR THE SELF PLAYS, IN ONE QUERY: the self, each figure its role says of talking with the model
        /// or, where it says none, the default translation's ontology states on its shape of the role
        /// (`sh:defaultValue`), and where the model a role names answers (`translation:translatedBy`), as the world's
        /// deployment states it, with the class of the role naming it.
        const TRANSLATOR_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
        PREFIX schema: <https://schema.org/>
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        PREFIX translation: <http://example.org/orexis/translation#>
        SELECT DISTINCT ?me ?kind ?model (COALESCE(?turnsSaid, ?turnsOwn) AS ?turns) \
        (COALESCE(?rowsSaid, ?rowsOwn) AS ?rows) (COALESCE(?answeredSaid, ?answeredOwn) AS ?answered) \
        (COALESCE(?calledSaid, ?calledOwn) AS ?called) (COALESCE(?retriesSaid, ?retriesOwn) AS ?retries) \
        (COALESCE(?converseSaid, ?converseOwn) AS ?converse) (COALESCE(?saySaid, ?sayOwn) AS ?say) WHERE { \
        ?shape sh:targetClass translation:Translator ; \
          sh:property [ sh:path translation:turns ; sh:defaultValue ?turnsOwn ] , [ sh:path translation:rows ; sh:defaultValue ?rowsOwn ] , \
                      [ sh:path translation:answeredWithinS ; sh:defaultValue ?answeredOwn ] , \
                      [ sh:path translation:calledWithinS ; sh:defaultValue ?calledOwn ] , \
                      [ sh:path translation:retries ; sh:defaultValue ?retriesOwn ] , \
                      [ sh:path translation:conversePrompt ; sh:defaultValue ?converseOwn ] , \
                      [ sh:path translation:sayPrompt ; sh:defaultValue ?sayOwn ] . \
        OPTIONAL { ?me a orexis:Self } \
        OPTIONAL { ?me orexis:plays ?r1 . ?r1 translation:turns ?turnsSaid } \
        OPTIONAL { ?me orexis:plays ?r2 . ?r2 translation:rows ?rowsSaid } \
        OPTIONAL { ?me orexis:plays ?r3 . ?r3 translation:answeredWithinS ?answeredSaid } \
        OPTIONAL { ?me orexis:plays ?r4 . ?r4 translation:calledWithinS ?calledSaid } \
        OPTIONAL { ?me orexis:plays ?r5 . ?r5 translation:retries ?retriesSaid } \
        OPTIONAL { ?me orexis:plays ?r6 . ?r6 translation:conversePrompt ?converseSaid } \
        OPTIONAL { ?me orexis:plays ?r7 . ?r7 translation:sayPrompt ?saySaid } \
        OPTIONAL { ?me orexis:plays ?named . ?named a ?kind ; translation:translatedBy ?by . ?by schema:url ?model } }";
        let mut known = beliefs.graphs_of(&[SELF_GRAPH], &Within::default())?;
        known.extend(beliefs.graphs_of(&[DEPLOYMENT], &Within::common())?);
        known.extend(beliefs.graphs_of(&[ONTOLOGY], &Within::default())?);
        let known: Vec<&str> = known.iter().map(String::as_str).collect();
        let rows = beliefs.rows(TRANSLATOR_Q, &known)?;
        let row = rows
            .first()
            .ok_or_else(|| Error::Document("the store states no translator's figures, and no default".into()))?;
        let said = |name: &str| value(row, name).unwrap_or_default();
        let whole = |name: &str| {
            said(name)
                .parse::<u32>()
                .map_err(|_| Error::Document(format!("a translator's {name} of {} is no whole number", said(name))))
        };
        let seconds = |name: &str| {
            said(name)
                .parse::<f64>()
                .map_err(|_| Error::Document(format!("a translator's {name} within {} is no number", said(name))))
        };
        let mut translated_by = None;
        for row in &rows {
            let Some(kind) = value(row, "kind") else { continue };
            if kind == ROLE || beliefs.closed(&kind)?.iter().any(|class| class == ROLE) {
                translated_by = value(row, "model").filter(|url| !url.is_empty());
                break;
            }
        }
        let (tx, rx) = channel();
        Ok(Translator {
            beliefs: beliefs.clone(),
            me: said("me"),
            model: None,
            inline: false,
            writing: BTreeMap::new(),
            journal: None,
            journaled: orexis::task::Journaled::default(),
            history: None,
            metrics: None,
            watch: Watch::default(),
            turns: whole("turns")? as usize,
            rows: whole("rows")? as usize,
            answered_within_s: seconds("answered")?,
            called_within_s: seconds("called")?,
            retries: whole("retries")?,
            converse_prompt: said("converse"),
            say_prompt: said("say"),
            translated_by,
            tx,
            rx,
            pending: VecDeque::new(),
        })
    }

    /// A person's words on a chat's channel: answered, or made a statement, off the mind's thread.
    pub fn heard(&mut self, prose: &Prose, now: DateTime) -> Result<Vec<String>, Error> {
        let store = &self.beliefs.clone();
        let Some(chat) = chats_of(store)?.into_iter().find(|c| c.channel == prose.channel) else {
            return Ok(Vec::new());
        };
        let Some(person) = chat.person(prose.sender.as_deref()) else {
            log::warn!(
                "{}: words in {} from someone the chat names not: dropped",
                local_of(&self.me),
                local_of(&chat.iri)
            );
            return Ok(Vec::new());
        };
        let others: Vec<&Vec<String>> = chat
            .agents
            .iter()
            .filter(|(a, _)| *a != self.me)
            .map(|(_, n)| n)
            .collect();
        let mine: Vec<String> = chat
            .agents
            .iter()
            .find(|(a, _)| *a == self.me)
            .map(|(_, n)| n.clone())
            .unwrap_or_else(|| vec![local_of(&self.me)]);
        let addressed = prose.addressed == Some(true) || named(&prose.text, &mine);
        if !addressed && (prose.addressed == Some(false) || others.iter().any(|n| named(&prose.text, n))) {
            return Ok(Vec::new());
        }
        let unaddressed = !others.is_empty() && !addressed;
        let Some(model) = self.model.clone() else {
            log::warn!(
                "{} wrote to {}, and there is no model to hear it with",
                person.1,
                local_of(&self.me)
            );
            return Ok(Vec::new());
        };
        let readable = if chat.reads.is_empty() {
            None
        } else {
            Some(Readable::new(store, &chat.reads, Some(&self.me), self.rows)?)
        };
        let prefixes = readable
            .as_ref()
            .map_or_else(|| prefixes_of(store, &self.me), |r| r.prefixes.clone());
        let past = chat.reads.iter().any(|k| k == EVENT).then(|| Past {
            journal: self.journal.clone().or_else(|| self.journaled.now()),
            history: self.history.clone(),
            metrics: self.metrics.clone(),
            rows: self.rows,
            prefixes: readable
                .as_ref()
                .map_or_else(|| namespaces(store), |r| r.prefixes.clone()),
        });
        let allowed = if unaddressed {
            Vec::new()
        } else {
            words(store, &chat.allows)?
        };
        let every = chat.allows.iter().any(|a| a == PROPERTY) && !unaddressed;
        let stating = (!allowed.is_empty()).then(|| Stating {
            allowed: allowed.clone(),
            every,
            prefixes: prefixes.clone(),
        });
        let pairs: Vec<(String, String)> = prefixes.iter().map(|(a, b)| (a.clone(), b.clone())).collect();
        let stated = if allowed.is_empty() {
            String::new()
        } else {
            listing(store, &allowed, every, &prefixes, readable.is_none())?
        };
        let mut system = vec![
            self.converse_prompt.clone() + if unaddressed { UNADDRESSED } else { "" },
            briefing(
                store,
                &self.me,
                &chat.reads,
                &readable.as_ref().map(Readable::listing).unwrap_or_default(),
                &stated,
                &pairs,
            )?,
        ];
        //  HOW TO WRITE ON THIS CHAT, by its style: a block of its own, before the instant, which is never cached.
        system.extend(written_as(&chat.style));
        system.push(instant_block(now));
        if !unaddressed {
            self.begin(&chat);
        }
        let conversation = Conversation {
            chat: chat.iri.clone(),
            channel: chat.channel.clone(),
            person,
            text: prose.text.clone(),
            system,
            stating: stating.clone(),
            readable,
            past,
            unaddressed,
            reply: prose.message.clone(),
            me: local_of(&self.me),
            at: now,
            turns: self.turns,
            messages_at_most: chat.style.messages_at_most,
        };
        let within_s = self.answered_within_s;
        if self.inline {
            let mind = Direct {
                store,
                stating,
                at: now,
            };
            converse(conversation, model.as_ref(), &mind, &self.tx);
        } else {
            let back = self.tx.clone();
            std::thread::spawn(move || {
                let mind = Asked {
                    back: back.clone(),
                    at: now,
                    stating,
                    within_s,
                };
                converse(conversation, model.as_ref(), &mind, &back);
            });
        }
        Ok(Vec::new())
    }

    /// A document the agent says to a person in a chat of its: rendered and sent through the chat's channel — the
    /// person's own chat with the agent first, a group they are in only where they have none.
    pub fn told(&mut self, to: &str, doc: &Document) -> Result<(), Error> {
        let store = &self.beliefs;
        let theirs: Vec<Chat> = chats_of(store)?
            .into_iter()
            .filter(|c| c.people.iter().any(|(p, _)| p == to))
            .collect();
        let Some(chat) = theirs
            .iter()
            .find(|c| c.people.len() == 1 && c.agents.len() == 1)
            .or_else(|| theirs.first())
            .cloned()
        else {
            return Ok(());
        };
        let Some(model) = self.model.clone() else {
            log::warn!(
                "{} told {} something, and there is no model to say it with",
                local_of(&self.me),
                local_of(to)
            );
            return Ok(());
        };
        let name = chat
            .people
            .iter()
            .find(|(p, _)| p == to)
            .map(|(_, n)| n.clone())
            .unwrap_or_default();
        let text = format!(
            "To: {name}\nFrom: {}, a software agent\nStatement:\n{}",
            local_of(&self.me),
            rendered(store, doc, &prefixes_of(store, &self.me))?
        );
        let (back, channel) = (self.tx.clone(), chat.channel.clone());
        let (system, at_most) = match written_as(&chat.style) {
            Some(style) => (format!("{} {style}", self.say_prompt), chat.style.messages_at_most),
            None => (self.say_prompt.clone(), 1),
        };
        let render = move || {
            let began = Instant::now();
            match model.ask(&system, &text) {
                Ok(answer) => {
                    let words = answer.text.trim().to_string();
                    let outcome = if words.is_empty() { "no words" } else { "said" };
                    let _ = back.send(Back::Spent(translated(
                        "render",
                        outcome,
                        model.name(),
                        1,
                        &answer.tokens,
                        began,
                    )));
                    if !words.is_empty() {
                        for part in sent_as(&words, at_most) {
                            let _ = back.send(Back::Said {
                                channel: channel.clone(),
                                words: part,
                                reply: None,
                            });
                        }
                    }
                }
                Err(e) => log::warn!("the model would not render what was said: {e}"),
            }
        };
        if self.inline {
            render();
        } else {
            std::thread::spawn(render);
        }
        Ok(())
    }

    /// One more answer thought in `chat`, and the agent shown writing there.
    fn begin(&mut self, chat: &Chat) {
        self.writing
            .entry(chat.iri.clone())
            .or_insert_with(|| (chat.clone(), 0))
            .1 += 1;
        self.show(&chat.channel);
    }

    /// Say the agent is writing on `channel`, for the transport that can show it there.
    fn show(&self, channel: &str) {
        self.watch.emit(&WritingAnnounced {
            channel: channel.to_string(),
        });
    }

    /// Every chat with an answer still being thought, shown again.
    pub fn still_writing(&self) {
        for (chat, _) in self.writing.values() {
            self.show(&chat.channel);
        }
    }

    /// `words` for the chat's channel, kept as the agent's own and said kept, for the transport that carries the
    /// channel; the prose graph written.
    pub fn say(&self, channel: &str, words: &str, reply: Option<&str>, at: DateTime) -> Result<String, Error> {
        let prose = Prose {
            channel: channel.to_string(),
            text: words.to_string(),
            at: Some(at),
            reply: reply.map(str::to_string),
            ..Prose::default()
        };
        let graph = written(&self.beliefs, &self.me, &prose)?;
        self.watch.emit(&ProseKept { prose: graph.clone() });
        Ok(graph)
    }

    /// Everything the model's threads handed back since the last ask, oldest first.
    fn arrived(&self) -> Vec<Back> {
        self.rx.try_iter().collect()
    }

    /// One thing handed back, done on the mind's thread: the graphs written.
    fn done(&mut self, back: Back, at: DateTime) -> Result<Vec<String>, Error> {
        match back {
            Back::Keep(payload) => {
                let written = orexis_speech::heard::heard(&self.beliefs, &self.me, &payload)?;
                let mut out = written.clone();
                for statement in &written {
                    out.extend(believe(&self.beliefs, statement)?);
                }
                log::info!("{} heard a statement from a person", local_of(&self.me));
                Ok(out)
            }
            Back::Said { channel, words, reply } => Ok(vec![self.say(&channel, &words, reply.as_deref(), at)?]),
            Back::Ended(chat) => {
                if let Some(entry) = self.writing.get_mut(&chat) {
                    entry.1 -= 1;
                    if entry.1 <= 0 {
                        self.writing.remove(&chat);
                    }
                }
                Ok(Vec::new())
            }
            Back::Spent(event) => {
                self.watch.emit(&event);
                Ok(Vec::new())
            }
            Back::Conversed(event) => {
                self.watch.emit(&event);
                Ok(Vec::new())
            }
            Back::Ask {
                stating,
                inputs,
                person,
                prose,
                at,
                answer,
            } => {
                let _ = answer.send(
                    statement_of(&self.beliefs, &stating, &inputs, &person, &prose, at).map_err(|e| e.to_string()),
                );
                Ok(Vec::new())
            }
        }
    }

    /// What translation's policy does of a document the agent said: phrased for each person it is to in a chat of
    /// theirs, read back from the store as it was said; an agent it is to is no person, and is passed over.
    fn phrase(&mut self, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let graphs: Vec<String> = event.all(STATEMENT).iter().map(|g| g.as_str().to_string()).collect();
        let to: Vec<String> = event.all(TO).iter().map(|a| a.as_str().to_string()).collect();
        if graphs.is_empty() || to.is_empty() {
            return Ok(Vec::new());
        }
        let store = self.beliefs.clone();
        let doc = document_of(&store, &graphs)?;
        let statements: Vec<NamedNode> = event.all(STATEMENT).into_iter().cloned().collect();
        let activity = pass.begin(PHRASING, &statements);
        let phrased = to.iter().try_for_each(|person| self.told(person, &doc));
        pass.end(activity);
        phrased?;
        Ok(Vec::new())
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

    /// What translation's policy does of a trigger: read the words it names back, and hear them where they are a
    /// person's; the agent's own it kept itself, for a transport to carry.
    pub(crate) fn heard_event(&mut self, job: usize, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        if job == PHRASE {
            return self.phrase(event, pass);
        }
        let Some(graph) = event.named(KEPT).cloned() else {
            return Ok(Vec::new());
        };
        let store = self.beliefs.clone();
        if !received(&store, graph.as_str())? {
            return Ok(Vec::new());
        }
        let Some(prose) = prose_of(&store, graph.as_str())? else {
            return Ok(Vec::new());
        };
        let at = prose.at.unwrap_or(pass.now);
        let activity = pass.begin(TRANSLATING, std::slice::from_ref(&graph));
        let written = self.heard(&prose, at);
        pass.end(activity);
        written
    }

    pub(crate) fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        match job {
            STILL => {
                self.still_writing();
                Ok(Vec::new())
            }
            _ => match self.pending.pop_front() {
                Some(back) => self.done(back, pass.now),
                None => Ok(Vec::new()),
            },
        }
    }

    fn submitted(&mut self) -> Vec<usize> {
        let arrived = self.arrived();
        let n = arrived.len();
        self.pending.extend(arrived);
        vec![BACK; n]
    }
}
