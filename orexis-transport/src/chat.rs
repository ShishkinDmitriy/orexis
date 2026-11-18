//! A CHAT ON THE WIRE: the words a member carrying a chat's channel hands the row listening on it, and is sent to say
//! there (`Words`); and a CHAT CARRIER, a member that polls its channel for what is written there and says what it is
//! sent, Telegram and email told apart by how they poll, read a message and say a text (`ChatMember`), the core that
//! runs them one (`ChatTransport`, `Carried`). What the words mean is the row's above, speech's; a carrier knows none of
//! its words (the-transport-is-the-bottom-layer-and-the-row-above-owns-the-loop).

use std::sync::{Arc, Mutex, MutexGuard};

use oxsdatatypes::DateTime;
use serde_json::{Map, Value as Json};

use orexis::Error;
use orexis::task::Turn;

use crate::inbox::{Inbox, Message};
use crate::jobs::{Jobs, Pending};
use crate::member::{Exchange, Member};

/// The job that polls the member's channel for what is written there.
pub const POLL: usize = 0;
/// The job that hands on one message the member's thread left.
pub const HANDLE: usize = 1;

/// How many messages no row listened for are kept for one that has yet to.
const UNHEARD_KEPT: usize = 64;

/// WORDS ON A CHAT'S CHANNEL, as a carrier hands them on and is sent them: the text, who wrote it where the carrier
/// tells (an IRI), whether it was for this agent where the carrier tells, the carrier's id of it, the id of the words
/// it answers, and whether it says only that the agent is writing. A JSON object of the fields that are said.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Words {
    pub text: String,
    pub from: Option<String>,
    pub addressed: Option<bool>,
    pub message: Option<String>,
    pub reply: Option<String>,
    pub writing: bool,
}

impl Words {
    /// Words with nothing said of them but their text.
    pub fn said(text: &str) -> Self {
        Words {
            text: text.to_string(),
            ..Words::default()
        }
    }

    /// The words as the bytes a carrier hands on or is sent: a JSON object of what is said.
    ///
    /// ```
    /// use orexis_transport::chat::Words;
    ///
    /// assert_eq!(Words::said("hi").bytes(), br#"{"text":"hi"}"#);
    /// let reply = Words { reply: Some("7".into()), ..Words::said("yes") };
    /// assert_eq!(reply.bytes(), br#"{"text":"yes","reply":"7"}"#);
    /// let writing = Words { writing: true, ..Words::default() };
    /// assert_eq!(writing.bytes(), br#"{"text":"","writing":true}"#);
    /// ```
    pub fn bytes(&self) -> Vec<u8> {
        let mut out = Map::new();
        out.insert("text".into(), Json::String(self.text.clone()));
        let mut put = |key: &str, value: Option<Json>| {
            if let Some(value) = value {
                out.insert(key.into(), value);
            }
        };
        put("from", self.from.clone().map(Json::String));
        put("addressed", self.addressed.map(Json::Bool));
        put("message", self.message.clone().map(Json::String));
        put("reply", self.reply.clone().map(Json::String));
        put("writing", self.writing.then_some(Json::Bool(true)));
        Json::Object(out).to_string().into_bytes()
    }

    /// The words `bytes` are, as `bytes` makes them; none where they are no JSON object.
    ///
    /// ```
    /// use orexis_transport::chat::Words;
    ///
    /// let words = Words { from: Some("http://example.org/anna".into()), addressed: Some(true), ..Words::said("hi") };
    /// assert_eq!(Words::of(&words.bytes()), Some(words));
    /// assert_eq!(Words::of(b"not json"), None);
    /// ```
    pub fn of(bytes: &[u8]) -> Option<Words> {
        let said: Json = serde_json::from_slice(bytes).ok()?;
        let said = said.as_object()?;
        let text = |key: &str| said.get(key).and_then(Json::as_str).map(str::to_string);
        Some(Words {
            text: text("text").unwrap_or_default(),
            from: text("from"),
            addressed: said.get("addressed").and_then(Json::as_bool),
            message: text("message"),
            reply: text("reply"),
            writing: said.get("writing").and_then(Json::as_bool).unwrap_or(false),
        })
    }
}

/// WHAT A CHAT CARRIER IS: a member that polls its channel, reads a message as the words on a chat's channel, and says
/// what it is sent, naming in its own words who holds the agent running.
pub trait ChatMember: Send + 'static {
    /// The name it holds the agent running under.
    const HOLDER: &'static str;

    /// Where its thread leaves what it receives.
    fn inbox(&self) -> &Inbox;
    /// Ask its channel for what is written there; what arrives is left in the inbox.
    fn poll(&self);
    /// Whether it carries the chat channel `channel`.
    fn carries(&self, channel: &str) -> Result<bool, Error>;
    /// A message its thread left, read: the chat channel it is on, and the words; none where it is no chat's the
    /// world names.
    fn handle(&mut self, topic: &str, payload: &[u8], at: DateTime) -> Result<Option<(String, Words)>, Error>;
    /// Say `words` on `channel`: the text, or that the agent is writing where the words say only that. Whether
    /// anything was sent.
    fn say(&mut self, channel: &str, words: &Words) -> bool;
}

/// A CHAT CARRIER, SHARED: the member, and who listens on which of its channels.
pub struct Carrier<M> {
    pub member: M,
    listeners: Vec<(String, Inbox)>,
    unheard: Vec<Message>,
}

impl<M: ChatMember> Carrier<M> {
    /// Leave `words` on `channel` with whoever listens there, or keep them for the first that does.
    fn hand_on(&mut self, channel: &str, words: &Words, at: DateTime) {
        let message = Message {
            topic: channel.to_string(),
            payload: words.bytes(),
            at: Some(at),
        };
        match self.listeners.iter().find(|(c, _)| c == channel) {
            Some((_, inbox)) => inbox.deliver_all(vec![message]),
            None => {
                self.unheard.push(message);
                let over = self.unheard.len().saturating_sub(UNHEARD_KEPT);
                self.unheard.drain(..over);
            }
        }
    }
}

/// THE CARRIER AS THE ROWS ABOVE SEE IT (`Member`): each chat channel it carries is listened to and sent on, the words
/// as `Words` both ways.
pub struct Carried<M>(pub Arc<Mutex<Carrier<M>>>);

impl<M: ChatMember> Carried<M> {
    fn carrier(&self) -> MutexGuard<'_, Carrier<M>> {
        self.0.lock().expect("a carrier nobody poisoned")
    }
}

impl<M: ChatMember> Member for Carried<M> {
    fn reaches(&self, channel: &str, exchange: Exchange) -> Result<bool, Error> {
        match exchange {
            Exchange::Listened | Exchange::Sent => self.carrier().member.carries(channel),
            Exchange::Requested => Ok(false),
        }
    }

    fn listen(&self, channel: &str, inbox: Inbox) -> Result<(), Error> {
        let mut carrier = self.carrier();
        let (early, rest): (Vec<Message>, Vec<Message>) = std::mem::take(&mut carrier.unheard)
            .into_iter()
            .partition(|m| m.topic == channel);
        carrier.unheard = rest;
        inbox.deliver_all(early);
        carrier.listeners.push((channel.to_string(), inbox));
        Ok(())
    }

    fn send(&self, channel: &str, payload: &[u8], _reply: Option<Inbox>) -> Result<(), Error> {
        let words =
            Words::of(payload).ok_or_else(|| Error::Evaluation(format!("{channel}: words that are no JSON object")))?;
        self.carrier().member.say(channel, &words);
        Ok(())
    }
}

/// THE CARRIER'S CORE: the carrier, shared with the rows above that listen and send on it, and the messages its thread
/// left, handed on one by one.
pub struct ChatTransport<M> {
    pub carrier: Arc<Mutex<Carrier<M>>>,
    pending: Pending,
}

impl<M: ChatMember> ChatTransport<M> {
    pub fn new(member: M) -> Self {
        ChatTransport {
            carrier: Arc::new(Mutex::new(Carrier {
                member,
                listeners: Vec::new(),
                unheard: Vec::new(),
            })),
            pending: Pending::default(),
        }
    }

    /// The carrier, held for one use.
    pub fn carrier(&self) -> MutexGuard<'_, Carrier<M>> {
        self.carrier.lock().expect("a carrier nobody poisoned")
    }

    /// The carrier as a member of the agent's, for the rows above.
    pub fn carried(&self) -> Carried<M> {
        Carried(self.carrier.clone())
    }
}

impl<M: ChatMember> Jobs for ChatTransport<M> {
    fn submitted(&mut self) -> Vec<usize> {
        let inbox = self.carrier().member.inbox().clone();
        vec![HANDLE; self.pending.arrived(&inbox)]
    }

    fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        pass.hold(M::HOLDER);
        match job {
            POLL => self.carrier().member.poll(),
            _ => {
                let Some(message) = self.pending.oldest() else {
                    return Ok(Vec::new());
                };
                let at = message.at.unwrap_or(pass.now);
                let mut carrier = self.carrier();
                if let Some((channel, words)) = carrier.member.handle(&message.topic, &message.payload, at)? {
                    carrier.hand_on(&channel, &words, at);
                }
            }
        }
        Ok(Vec::new())
    }
}
