//! THE SPEAKER, the package's core: the role the self plays, read off its self graph, and what it does of a statement
//! written and of a step that says something - extract what it believes of each, and say each to whom it is said - and
//! of what arrives on the channels it listens on through the transport: a peer's document on the agent's own, kept as
//! what was said, and a person's words on a chat's, kept as prose; and the agent's own words carried back.

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::document::Document;
use orexis::events::Watch;
use orexis::ontology::RECEIVED;
use orexis::store::{Store, iri};
use orexis::task::{Heard as HeardEvent, Turn};
use orexis_transport::chat::Words;
use orexis_transport::{Exchange, Inbox, Members};
use oxigraph::model::NamedNode;

use crate::events::{Heard, Said, Statement};
use crate::extract::extract;
use crate::heard::heard;
use crate::ontology::{CARRYING, HEARING, LISTENING, SPEAKING, STATEMENT, TO, USED};
use crate::prose::{CHANNEL, KEPT, Prose, ProseKept, kept, prose_of, received};
use crate::said::said;
use crate::statements::{described, document_of};

pub(crate) const STATED: usize = 0;
const EXTRACTED: usize = 1;
pub(crate) const SPEAK: usize = 2;
pub(crate) const CARRY: usize = 3;

/// THE SPEAKER THE SELF PLAYS, the package's core: who says, whoever watches it say, and the beliefs extracted as it
/// started for the first turn to hand on. `speech:Speaker` states no figure.
pub struct Speaker {
    beliefs: Store,
    pub me: String,
    /// Whoever watches the agent, and the instant the pass stands at.
    pub watch: Watch,
    pending: Vec<String>,
    /// The agent's members, read once every core is made.
    members: Members,
    /// Where what arrives on a channel speech listens on is left.
    pub inbox: Inbox,
    /// What speech does of each channel for as long as it runs, its listening (`attend`): what a hearing of what
    /// arrived on that channel is part of.
    listening: std::collections::HashMap<String, orexis::activity::Activity>,
    /// The hearing that kept each statement received and not yet said heard.
    hearing: std::collections::HashMap<String, NamedNode>,
}

impl Speaker {
    /// The speaker the self plays, read off the store.
    pub fn new(store: &Store) -> Result<Self, Error> {
        Ok(Speaker {
            beliefs: store.clone(),
            me: orexis::boot::selves(store)?.into_iter().next().unwrap_or_default(),
            watch: Watch::default(),
            pending: Vec::new(),
            members: Members::default(),
            inbox: Inbox::default(),
            listening: Default::default(),
            hearing: Default::default(),
        })
    }

    /// SPEECH LISTENS through the members of the agent's, once every core is made: on the agent's own channel, where a
    /// peer's documents arrive, and on the channel of every chat the agent is in, each where a member reaches it as a
    /// channel listened to; the channels.
    pub(crate) fn listen(&mut self, members: &Members) -> Result<Vec<String>, Error> {
        /// THE CHANNEL OF EVERY CHAT THE AGENT IS IN.
        const CHANNELS_Q: &str = "PREFIX speech: <http://example.org/orexis/speech#>
        SELECT DISTINCT ?channel WHERE { ?chat a speech:Chat ; speech:participant $me ; speech:channel ?channel }
        ORDER BY ?channel";
        self.members = members.clone();
        let common = self
            .beliefs
            .graphs_of(&[orexis::ontology::BELIEF], &orexis::store::Within::common())?;
        let common: Vec<&str> = common.iter().map(String::as_str).collect();
        let mut channels = vec![self.me.clone()];
        channels.extend(
            self.beliefs
                .rows(&bind(CHANNELS_Q, &[("me", Value::iri(self.me.as_str()))])?, &common)?
                .iter()
                .filter_map(|r| iri(r, "channel")),
        );
        let mut listened = Vec::new();
        for channel in channels {
            if let Some(member) = members.reaching(&channel, Exchange::Listened)? {
                member.listen(&channel, self.inbox.clone())?;
                listened.push(channel);
            }
        }
        Ok(listened)
    }

    /// WHAT SPEECH DOES OF EACH CHANNEL FOR AS LONG AS IT RUNS: a listening of each of `channels`, an activity inside
    /// speech's running that names its channel (`prov:used`).
    pub(crate) async fn attend(&mut self, handed: &orexis::task::Handed, channels: &[String]) -> Result<(), Error> {
        for channel in channels {
            let Ok(node) = NamedNode::new(channel.as_str()) else {
                continue;
            };
            let activity = handed.lasting(LISTENING, vec![(USED, node.into())]).await?;
            self.listening.insert(channel.clone(), activity);
        }
        Ok(())
    }

    /// WHAT ARRIVED on the channels speech listens on, since the last take: a peer's document on the agent's own, kept
    /// as what was said (`heard`); a person's words on a chat's, kept as prose and said `speech:ProseKept`, but the
    /// agent's own the carrier hands back. The graphs written.
    pub(crate) fn arrived(&mut self, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let mut written = Vec::new();
        for message in self.inbox.take() {
            //  HEARING ONE ARRIVAL IS AN ACTIVITY, part of the listening of the channel it came on: what it kept is
            //  said of it, and what it says is said within it.
            let listening = self.listening.get(&message.topic);
            if let Some(listening) = listening {
                pass.step_in(listening);
            }
            let activity = pass.begin(HEARING, &[]);
            let hearing = activity.node.clone();
            let kept = self.keep(&message, pass);
            pass.wrote_by(activity, kept.as_deref().unwrap_or_default());
            if let Some(listening) = listening {
                pass.step_out(listening);
            }
            let kept = kept?;
            for graph in &kept {
                self.hearing.insert(graph.clone(), hearing.clone());
            }
            written.extend(kept);
        }
        Ok(written)
    }

    /// What one arrival is kept as: a peer's document as the statements it says, a person's words as prose, said kept;
    /// nothing of the agent's own words the carrier hands back.
    fn keep(&self, message: &orexis_transport::Message, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        if message.topic == self.me {
            return heard(&self.beliefs, &self.me, &message.payload);
        }
        let Some(words) = Words::of(&message.payload) else {
            return Ok(Vec::new());
        };
        if words.from.as_deref() == Some(self.me.as_str()) || words.text.trim().is_empty() {
            return Ok(Vec::new());
        }
        let prose = Prose {
            channel: message.topic.clone(),
            sender: words.from,
            text: words.text.trim().to_string(),
            at: message.at.or(Some(pass.now)),
            addressed: words.addressed,
            message: words.message,
            reply: None,
        };
        let graph = kept(&self.beliefs, &self.me, &prose)?;
        pass.emit(&ProseKept { prose: graph.clone() });
        Ok(vec![graph])
    }

    /// `payload` sent on `channel` through the member that reaches it as a channel sent on; whether one did.
    fn send(&self, channel: &str, payload: &[u8]) -> Result<bool, Error> {
        match self.members.reaching(channel, Exchange::Sent)? {
            Some(member) => {
                member.send(channel, payload, None)?;
                Ok(true)
            }
            None => Ok(false),
        }
    }

    /// The agent's own words a prose graph keeps, carried on their channel as a reply where they name one; and the
    /// agent shown writing on a channel where it says it is. A person's words, speech's own keeping, are translation's.
    fn carry(&mut self, event: &HeardEvent, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        if let Some(graph) = event.named(KEPT) {
            if received(&self.beliefs, graph.as_str())? {
                return Ok(Vec::new());
            }
            let Some(prose) = prose_of(&self.beliefs, graph.as_str())? else {
                return Ok(Vec::new());
            };
            let words = Words {
                reply: prose.reply.clone(),
                ..Words::said(&prose.text)
            };
            let activity = pass.begin(CARRYING, std::slice::from_ref(graph));
            let sent = self.send(&prose.channel, &words.bytes());
            pass.end(activity);
            if !sent? {
                log::warn!(
                    "{}: no member of the agent's carries it, so its words are not said",
                    orexis::ontology::local_of(&prose.channel)
                );
            }
        } else if let Some(channel) = event.named(CHANNEL) {
            let writing = Words {
                writing: true,
                ..Words::default()
            };
            self.send(channel.as_str(), &writing.bytes())?;
        }
        Ok(Vec::new())
    }

    /// What a restart finds unextracted: every statement nothing was extracted from, extracted now and handed on at
    /// the first turn.
    pub(crate) fn unextracted(&mut self) -> Result<(), Error> {
        /// EVERY STATEMENT NOTHING WAS EXTRACTED FROM YET: one no graph says it was derived from.
        const UNEXTRACTED_Q: &str = "PREFIX prov: <http://www.w3.org/ns/prov#>
        PREFIX speech: <http://example.org/orexis/speech#>
        SELECT ?g WHERE { GRAPH ?m_g { ?g a speech:StatementGraph }
                          FILTER NOT EXISTS { GRAPH ?m_b { ?b prov:wasDerivedFrom ?g } } } ORDER BY ?g";
        let unextracted: Vec<String> = self
            .beliefs
            .rows(UNEXTRACTED_Q, &[])?
            .iter()
            .filter_map(|r| iri(r, "g"))
            .collect();
        for statement in unextracted {
            self.pending.extend(extract(&self.beliefs, &statement)?);
        }
        Ok(())
    }

    /// Believe `document` as the agent said it, and say it said to every agent it is `to`; the graphs believed.
    pub fn say(&self, document: &Document, to: &[String]) -> Result<Vec<String>, Error> {
        let written = said(&self.beliefs, &self.me, document)?;
        self.tell_said(&written, to)?;
        Ok(written)
    }

    /// Say that the statements `written` were said to `to`, for whoever carries them to each.
    fn tell_said(&self, written: &[String], to: &[String]) -> Result<(), Error> {
        let watch = self.watch.clone();
        if !watch.connected() {
            return Ok(());
        }
        let mut statements = Vec::new();
        for graph in written {
            let (kinds, said) = described(&self.beliefs, graph)?;
            statements.push(Statement {
                graph: graph.clone(),
                kinds,
                said,
            });
        }
        watch.emit(&Said {
            statements,
            to: to.to_vec(),
            at: watch.at(),
        });
        Ok(())
    }

    fn arrival(&self, graph: &str) -> Result<Option<String>, Error> {
        /// HOW A STATEMENT ARRIVED, and THE KINDS IT SAYS IT IS: what is said of it.
        const ARRIVAL_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
            SELECT ?arrival WHERE { GRAPH ?m_graph { $graph orexis:arrivedBy ?arrival } }";
        Ok(self
            .beliefs
            .rows(&bind(ARRIVAL_Q, &[("graph", Value::iri(graph))])?, &[])?
            .first()
            .and_then(|r| iri(r, "arrival")))
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

    pub(crate) fn run(&mut self, job: usize, _pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        match job {
            EXTRACTED => Ok(std::mem::take(&mut self.pending)),
            _ => Ok(Vec::new()),
        }
    }

    /// The statements written together, each said heard where it was received, and each extracted.
    pub(crate) fn heard(&mut self, _job: usize, graphs: &[String], pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let watch = self.watch.clone();
        let mut written = Vec::new();
        for graph in graphs {
            //  SAID WITHIN THE HEARING THAT KEPT IT, which has ended: once the statement is told written.
            let hearing = self.hearing.remove(graph);
            if watch.connected() && self.arrival(graph)?.as_deref() == Some(RECEIVED) {
                let (kinds, said) = described(&self.beliefs, graph)?;
                let heard = Heard {
                    statement: graph.to_string(),
                    at: Some(pass.now),
                    kinds,
                    said,
                };
                match hearing {
                    Some(hearing) => watch.emit_within(&heard, Some(hearing)),
                    None => watch.emit(&heard),
                };
            }
            written.extend(extract(&self.beliefs, graph)?);
        }
        Ok(written)
    }

    /// What speech's policy does of a trigger: the agent's own words carried; or each statement it names told, as it
    /// was said, to each agent it names, the document sent through the member that reaches each, a person passed over.
    pub(crate) fn heard_event(
        &mut self,
        job: usize,
        event: &HeardEvent,
        pass: &mut Turn<'_>,
    ) -> Result<Vec<String>, Error> {
        if job == CARRY {
            return self.carry(event, pass);
        }
        let statements: Vec<NamedNode> = event.all(STATEMENT).into_iter().cloned().collect();
        let to: Vec<String> = event.all(TO).iter().map(|a| a.as_str().to_string()).collect();
        if statements.is_empty() || to.is_empty() {
            return Ok(Vec::new());
        }
        let graphs: Vec<String> = statements.iter().map(|s| s.as_str().to_string()).collect();
        let activity = pass.begin(SPEAKING, &statements);
        let told = self.tell_said(&graphs, &to).and_then(|()| {
            let document = document_of(&self.beliefs, &graphs)?.trig()?;
            to.iter().try_for_each(|agent| self.send(agent, &document).map(|_| ()))
        });
        pass.end(activity);
        told?;
        Ok(Vec::new())
    }

    fn submitted(&mut self) -> Vec<usize> {
        if self.pending.is_empty() {
            Vec::new()
        } else {
            vec![EXTRACTED]
        }
    }
}

#[cfg(test)]
mod tests {
    //! Speech's part, held as `agent/speech/tests/test_create.py` holds it: it says a document as the agent said it,
    //! and tells each agent it is to through whoever reaches a peer.

    use super::*;
    use crate::ontology::{STATEMENT, TO};
    use crate::said::tests::{T, me, quads, store};
    use oxigraph::model::NamedNode;
    use std::sync::{Arc, Mutex};

    #[test]
    fn its_part_believes_what_was_said_and_says_it_said_to_each_agent() {
        let store = store();
        let mut part = Speaker::new(&store).unwrap();
        part.me = me();
        let heard = Arc::new(Mutex::new(Vec::new()));
        let into = heard.clone();
        part.watch.connect(move |event, _| {
            into.lock().unwrap().push((event.kind(), event.about()));
        });
        let round = format!("{T}round");
        let to = [format!("{T}rose"), format!("{T}fern")];
        assert_eq!(
            part.say(&Document::of_quads(quads(&round, "open")), &to).unwrap(),
            std::slice::from_ref(&round)
        );
        let node = |s: &str| oxigraph::model::Term::NamedNode(NamedNode::new(s).unwrap());
        assert_eq!(
            *heard.lock().unwrap(),
            [(
                Some(crate::ontology::SAID),
                vec![(STATEMENT, node(&round)), (TO, node(&to[0])), (TO, node(&to[1]))]
            )],
            "one telling, naming its statement and each agent it is to"
        );
    }
}
