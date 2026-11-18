//! WORDS ON A CHAT'S CHANNEL, speech's since a chat is (knowledge/domain/kernel/policy.md): speech listens on a
//! `speech:Chat`'s channel through the member that carries it, keeps a person's words as a `speech:ProseGraph` (`kept`)
//! and says `speech:ProseKept`, which translation's ontology puts beneath its trigger; translation keeps the agent's own
//! words the same way (`written`) and says the same event, and speech carries them back through the member. Which words
//! are whose is the graph's provenance (`received`), so no member imports speech or translation.

use oxigraph::model::{GraphName, Literal, NamedNode, Quad, Term};
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::document::Document;
use orexis::events::Event;
use orexis::ontology::{RECEIVED, RECORDED};
use orexis::rdf::mint;
use orexis::store::Store;

const SPEECH: &str = "http://example.org/orexis/speech#";

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
        "PREFIX orexis: <http://example.org/orexis#> ASK { GRAPH $cat { $graph orexis:arrivedBy $received } }",
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
    let word = |w: &str| NamedNode::new_unchecked(format!("{SPEECH}{w}"));
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
    let Some(text) = literal(&format!("{SPEECH}text")) else {
        return Ok(None);
    };
    let channel = match value(&format!("{SPEECH}channel")) {
        Some(Term::NamedNode(n)) => n.as_str().to_string(),
        _ => String::new(),
    };
    Ok(Some(Prose {
        channel,
        sender: literal(&format!("{SPEECH}sender")),
        text,
        at: literal(AT_TIME).and_then(|t| t.parse().ok()),
        addressed: literal(&format!("{SPEECH}addressed")).map(|a| a == "true"),
        message: literal(&format!("{SPEECH}message")),
        reply: literal(&format!("{SPEECH}repliesTo")),
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
            .map(|p| vec![(KEPT, Term::NamedNode(p))])
            .unwrap_or_default()
    }
}

/// The agent said it is writing on `channel`, for the transport that can show it there.
#[derive(Clone, Debug, PartialEq)]
pub struct WritingAnnounced {
    pub channel: String,
}

impl Event for WritingAnnounced {
    fn kind(&self) -> Option<&'static str> {
        Some(WRITING_ANNOUNCED)
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        NamedNode::new(self.channel.as_str())
            .map(|c| vec![(CHANNEL, Term::NamedNode(c))])
            .unwrap_or_default()
    }
}

use orexis::rdf::RDF_TYPE;
const AT_TIME: &str = "http://www.w3.org/ns/prov#atTime";
/// A person's words kept, as the event it is said as, and what it names.
pub const PROSE_KEPT: &str = "http://example.org/orexis/speech#ProseKept";
pub const KEPT: &str = "http://example.org/orexis/speech#kept";
pub const PROSE_GRAPH: &str = "http://example.org/orexis/speech#ProseGraph";
/// The agent said writing on a channel, as the event it is said as, and what it names.
pub const WRITING_ANNOUNCED: &str = "http://example.org/orexis/speech#WritingAnnounced";
pub const CHANNEL: &str = "http://example.org/orexis/speech#channel";
