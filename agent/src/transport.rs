//! THE TRANSPORT FAMILY'S CONTRACT, as `agent/transport/transport.py` keeps what is the same of every member: a
//! member's task or thread leaves what it receives in an INBOX for the one executing thread to handle, ringing the mind awake, and a CHANNEL IS THE
//! TRANSPORT'S — a member carries bytes on a topic, a chat, a mailbox or a url and knows nothing of what they mean. For a
//! `speech:Chat`'s channel a member keeps a person's words as an `orexis:ProseGraph` (`kept`) and says
//! `orexis:ProseKept`, which translation's ontology puts beneath its trigger; translation keeps the agent's own words
//! the same way (`written`) and says the same event, which each member's ontology puts beneath its own trigger, and the
//! member that carries the channel sends them as a `Carrier`. Which words are whose is the graph's provenance
//! (`received`), so no member imports translation and translation imports no member.

use std::collections::VecDeque;
use std::sync::{Arc, Mutex, OnceLock};

use oxigraph::model::{GraphName, Literal, NamedNode, Quad, Term};
use oxsdatatypes::DateTime;

use crate::Error;
use crate::bind::{Value, bind};
use crate::document::Document;
use crate::events::{Event, mint};
use crate::ontology::{OREXIS, RECEIVED, RECORDED};
use crate::runtime::{Heard, Pass, Wake};
use crate::store::Store;

/// A message on a channel, and the instant it arrived where whoever handed it knows one — a network thread knows none
/// of the agent's timeline, so it is stamped with the instant of the pass that handles it.
#[derive(Clone, Debug, PartialEq)]
pub struct Message {
    pub topic: String,
    pub payload: Vec<u8>,
    pub at: Option<DateTime>,
}

/// Where the clients' threads leave what they receive, for the one executing thread to handle.
#[derive(Clone, Default)]
pub struct Inbox {
    queue: Arc<Mutex<VecDeque<Message>>>,
    wake: Arc<OnceLock<Wake>>,
}

impl Inbox {
    /// Ring `wake` at every message from now on; a part says so as it starts.
    pub fn wakes(&self, wake: Wake) {
        let _ = self.wake.set(wake);
    }

    /// A message arrived.
    pub fn deliver(&self, topic: &str, payload: &[u8], at: Option<DateTime>) {
        if let Ok(mut queue) = self.queue.lock() {
            queue.push_back(Message {
                topic: topic.to_string(),
                payload: payload.to_vec(),
                at,
            });
        }
        if let Some(wake) = self.wake.get() {
            wake.ring();
        }
    }

    /// Everything arrived since the last take, oldest first.
    pub fn take(&self) -> Vec<Message> {
        self.queue.lock().map(|mut q| q.drain(..).collect()).unwrap_or_default()
    }
}

/// A person's words on a channel at `at`: the channel's node in the world, the person who said them where the channel
/// tells, and the text. Where the carrier tells whom the words were for, `addressed` says so — true where they tagged
/// or replied to this agent's own account, false where they tagged or replied to someone else and not it — and
/// `message` is the carrier's id of the words, which an answer may reply to. The agent's own words name the carrier's
/// id of the words they answer by `reply`, where the carrier threads one.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Prose {
    pub channel: String,
    pub sender: Option<String>,
    pub text: String,
    pub at: Option<DateTime>,
    pub addressed: Option<bool>,
    pub message: Option<String>,
    pub reply: Option<String>,
}

/// A PERSON'S WORDS KEPT: the prose graph a transport keeps of `prose`, the agent `me`'s own and arrived from outside,
/// before anything is made of them; the graph's name.
pub fn kept(store: &Store, me: &str, prose: &Prose) -> Result<String, Error> {
    keep(store, me, prose, RECEIVED)
}

/// THE AGENT'S OWN WORDS KEPT: the prose graph translation keeps of `prose`, the agent `me`'s own act, before any
/// transport carries them; the graph's name.
pub fn written(store: &Store, me: &str, prose: &Prose) -> Result<String, Error> {
    keep(store, me, prose, RECORDED)
}

/// Whether the words a prose graph keeps arrived from outside, a person's, rather than the agent's own.
pub fn received(store: &Store, graph: &str) -> Result<bool, Error> {
    let Some(cat) = store.catalogue()? else {
        return Ok(false);
    };
    let text = bind(
        "ASK { GRAPH $cat { $graph orexis:arrivedBy $received } }",
        &[
            ("cat", Value::iri(cat.as_str())),
            ("graph", Value::iri(graph)),
            ("received", Value::iri(RECEIVED)),
        ],
    )?;
    store.ask(&text, &[])
}

fn keep(store: &Store, me: &str, prose: &Prose, arrived: &str) -> Result<String, Error> {
    let tail = mint();
    let tail = tail
        .as_str()
        .rsplit(['/', ':', '#'])
        .next()
        .unwrap_or_default()
        .to_string();
    let local = me.rsplit(['/', '#']).next().unwrap_or(me);
    let graph = NamedNode::new(format!("http://example.org/orexis/graph/prose/{local}/{tail}"))
        .map_err(|e| Error::Evaluation(e.to_string()))?;
    let into = GraphName::NamedNode(graph.clone());
    let word = |w: &str| NamedNode::new_unchecked(format!("{OREXIS}{w}"));
    let text = |t: &str| Term::Literal(Literal::new_simple_literal(t));
    let mut quads = vec![Quad::new(
        graph.clone(),
        NamedNode::new_unchecked(RDF_TYPE),
        word("ProseGraph"),
        GraphName::DefaultGraph,
    )];
    let mut say = |p: NamedNode, o: Term| quads.push(Quad::new(graph.clone(), p, o, into.clone()));
    say(word("text"), text(&prose.text));
    if let Ok(channel) = NamedNode::new(prose.channel.as_str()) {
        say(word("channel"), Term::NamedNode(channel));
    }
    if let Some(sender) = &prose.sender {
        say(word("sender"), text(sender));
    }
    if let Some(addressed) = prose.addressed {
        say(word("addressed"), Term::Literal(Literal::from(addressed)));
    }
    if let Some(message) = &prose.message {
        say(word("message"), text(message));
    }
    if let Some(reply) = &prose.reply {
        say(word("repliesTo"), text(reply));
    }
    if let Some(at) = prose.at {
        say(NamedNode::new_unchecked(AT_TIME), Term::Literal(Literal::from(at)));
    }
    store.put_document(&Document::of_quads(quads), Some(me), None, Some(arrived), true)?;
    Ok(graph.as_str().to_string())
}

/// The words a prose graph keeps, as they were handed to `kept`.
pub fn prose_of(store: &Store, graph: &str) -> Result<Option<Prose>, Error> {
    let g = NamedNode::new(graph).map_err(|e| Error::Evaluation(e.to_string()))?;
    let subject = g.clone();
    let value = |predicate: &str| -> Option<Term> {
        store
            .engine()
            .quads_for_pattern(
                Some(subject.as_ref().into()),
                Some(NamedNode::new_unchecked(predicate).as_ref()),
                None,
                Some(g.as_ref().into()),
            )
            .flatten()
            .next()
            .map(|q| q.object)
    };
    let literal = |predicate: &str| match value(predicate) {
        Some(Term::Literal(l)) => Some(l.value().to_string()),
        _ => None,
    };
    let Some(text) = literal(&format!("{OREXIS}text")) else {
        return Ok(None);
    };
    let channel = match value(&format!("{OREXIS}channel")) {
        Some(Term::NamedNode(n)) => n.as_str().to_string(),
        _ => String::new(),
    };
    Ok(Some(Prose {
        channel,
        sender: literal(&format!("{OREXIS}sender")),
        text,
        at: literal(AT_TIME).and_then(|t| t.parse().ok()),
        addressed: literal(&format!("{OREXIS}addressed")).map(|a| a == "true"),
        message: literal(&format!("{OREXIS}message")),
        reply: literal(&format!("{OREXIS}repliesTo")),
    }))
}

/// Words on a channel were kept: the prose graph, a person's for whoever above the transports hears it, the agent's own
/// for the transport that carries the channel.
#[derive(Clone, Debug, PartialEq)]
pub struct ProseKept {
    pub prose: String,
}

impl Event for ProseKept {
    fn kind(&self) -> Option<&'static str> {
        Some(PROSE_KEPT)
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        NamedNode::new(self.prose.as_str())
            .map(|p| vec![(PROSE, Term::NamedNode(p))])
            .unwrap_or_default()
    }
}

/// WHAT A MEMBER'S POLICY DOES OF ITS CARRYING TRIGGER, `trigger`'s activity `kind`: the agent's own words a prose graph
/// keeps sent on their channel, where this member carries it, and a person's left for whoever translates; or the agent
/// shown writing on a channel, where the member can show it there.
pub fn carry(
    store: &Store,
    carrier: &mut dyn Carrier,
    event: &Heard,
    pass: &mut Pass<'_>,
    kind: &'static str,
) -> Result<(), Error> {
    if let Some(graph) = event.named(PROSE) {
        if received(store, graph.as_str())? {
            return Ok(());
        }
        let Some(prose) = prose_of(store, graph.as_str())? else {
            return Ok(());
        };
        let activity = pass.begin(kind, std::slice::from_ref(graph));
        carrier.say_to(&prose.channel, &prose.text, prose.reply.as_deref());
        pass.end(activity);
    } else if let Some(channel) = event.named(CHANNEL) {
        carrier.writing_in(channel.as_str());
    }
    Ok(())
}

/// The agent is writing on `channel`, for the transport that can show it there.
#[derive(Clone, Debug, PartialEq)]
pub struct Writing {
    pub channel: String,
}

impl Event for Writing {
    fn kind(&self) -> Option<&'static str> {
        Some(WRITING)
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        NamedNode::new(self.channel.as_str())
            .map(|c| vec![(CHANNEL, Term::NamedNode(c))])
            .unwrap_or_default()
    }
}

const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const AT_TIME: &str = "http://www.w3.org/ns/prov#atTime";
/// A person's words kept, as the event it is said as, and what it names.
pub const PROSE_KEPT: &str = "http://example.org/orexis#ProseKept";
pub const PROSE: &str = "http://example.org/orexis#prose";
pub const PROSE_GRAPH: &str = "http://example.org/orexis#ProseGraph";
/// The agent writing on a channel, as the event it is said as, and what it names.
pub const WRITING: &str = "http://example.org/orexis#Writing";
pub const CHANNEL: &str = "http://example.org/orexis#channel";

/// A member that carries a chat's channel: the agent's own words out on it, and the agent shown writing there.
pub trait Carrier {
    /// Prose out on `channel`, as a reply to the message `reply` names where the carrier threads one. Whether anything
    /// was SENT: a member that does not carry the channel sends nothing.
    fn say_to(&mut self, channel: &str, text: &str, reply: Option<&str>) -> bool;

    /// Show on `channel` that the agent is writing, where the channel can show it. Whether it was SHOWN.
    fn writing_in(&mut self, channel: &str) -> bool;
}
