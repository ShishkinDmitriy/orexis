//! THE MQTT DRIVER, as `agent/transport/mqtt/driver.py` answers the transport family's contract from MQTT4SSN's
//! words, with the topic filter matching MQTT itself specifies.
//!
//! **WHAT THE WORLD SAYS AND WHAT FOLLOWS**: a sensor speaks MQTT when it `mqtt4ssn:observesTopic` a topic; a row
//! above that listens to it (`listen_on`) has the agent subscribe to the pattern of every `mqtt4ssn:TopicFilter`
//! matching that topic, over the brokers the sensor's client is on, and every message a pattern matches is left in the
//! row's inbox with the sensor as its channel. A command goes to the topic the device or its board
//! `mqtt4ssn:listensToTopic`, by a pattern with no wildcard, not retained: a step's command and a nudge alike, each the
//! document the operator made.
//!
//! **THE TRANSPORT KNOWS NO CODEC AND NO SENSOR OF THE AGENT'S**: which sensors are the agent's, and what a message
//! says of each, are sensing's, which listens to the ones it attends through the contract
//! (the-transport-is-the-bottom-layer-and-the-row-above-owns-the-loop). A peer's document on the agent's own topic is
//! still kept by speech's `heard` here, and a chat's prose here, until speech listens through the contract too (#1221).
//!
//! **THE MEMBER BRINGS ITSELF UP, AND THE THREAD IS THE CONTAINER'S**: `connect` makes a client per broker the
//! world says the agent is connected to, at the url the world's deployment graph states of it, under the credential
//! the environment holds — `MQTT_USERNAME` and `MQTT_PASSWORD`, and
//! `MQTT_CA`, `MQTT_CERT` and `MQTT_KEY` for a url that is `mqtts` — and refuses without a broker or a credential
//! rather than guess one. A message arrives on a session's task and goes to the member's inbox, which the part
//! hands the one executing thread as a job. **A TOPIC GOES OVER A BROKER THE AGENT SHARES WITH THE CLIENT IT IS
//! ABOUT**, and a member of one client sends everything over it, as a test's does.

use std::collections::BTreeSet;
use std::future::Future;
use std::pin::Pin;
use std::time::Duration;

use oxsdatatypes::DateTime;
use serde_json::Value as Json;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{BELIEF, local_of};
use orexis::rdf::repr;
use orexis::store::{Store, Within, iri, value};

/// Whether a topic filter matches a topic name, as MQTT specifies: `+` matches one level, `#` the rest and may only
/// end a filter, and a topic beginning with `$` is matched by no wildcard at its first level.
pub fn matches(pattern: &str, topic: &str) -> bool {
    if topic.starts_with('$') && (pattern.starts_with('+') || pattern.starts_with('#')) {
        return false;
    }
    let (levels, names): (Vec<&str>, Vec<&str>) = (pattern.split('/').collect(), topic.split('/').collect());
    for (i, level) in levels.iter().enumerate() {
        if *level == "#" {
            return i == levels.len() - 1;
        }
        if i >= names.len() || (*level != "+" && *level != names[i]) {
            return false;
        }
    }
    levels.len() == names.len()
}

/// A document as Python's `json.dumps` spells it — `", "` and `": "` between, every key in its order, a float as
/// `repr` writes it, non-ASCII escaped — so the bytes on the wire are the ones the Python agent sends.
pub fn dumps(document: &Json) -> String {
    match document {
        Json::Null => "null".into(),
        Json::Bool(b) => if *b { "true" } else { "false" }.into(),
        Json::Number(n) => match (n.as_i64(), n.as_u64()) {
            (Some(i), _) => i.to_string(),
            (_, Some(u)) => u.to_string(),
            _ => repr(n.as_f64().unwrap_or(0.0)),
        },
        Json::String(s) => quoted(s),
        Json::Array(items) => format!("[{}]", items.iter().map(dumps).collect::<Vec<_>>().join(", ")),
        Json::Object(fields) => format!(
            "{{{}}}",
            fields
                .iter()
                .map(|(k, v)| format!("{}: {}", quoted(k), dumps(v)))
                .collect::<Vec<_>>()
                .join(", ")
        ),
    }
}

fn quoted(text: &str) -> String {
    let mut out = String::from("\"");
    for c in text.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 || (c as u32) > 0x7e => {
                let mut buf = [0u16; 2];
                for unit in c.encode_utf16(&mut buf) {
                    out.push_str(&format!("\\u{unit:04x}"));
                }
            }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// One session with a broker, as the driver uses it: subscribe and publish.
pub trait Client: Send {
    fn subscribe(&mut self, pattern: &str) -> Result<(), Error>;
    fn publish(&mut self, topic: &str, payload: &[u8], retain: bool) -> Result<(), Error>;
    /// Whatever the session holds open, closed.
    fn stop(&mut self) {}
}

use orexis_transport::chat::Words;
pub use orexis_transport::{Inbox, Message};

/// A session's listening, for the part to run as a task once it starts.
pub type Listening = Pin<Box<dyn Future<Output = ()> + Send>>;

/// One agent's side of the bus: what the container needs of this transport, answered from the world in MQTT4SSN's
/// words, over the clients the container connected — by the IRI of the broker each is connected to, or one client
/// standing for them all (`None`).
pub struct Mqtt {
    beliefs: Store,
    pub me: String,
    pub clients: Vec<(Option<String>, Box<dyn Client>)>,
    pub inbox: Inbox,
    /// What the sessions connected are yet to listen for, taken by the part as it starts.
    pub listening: Vec<Listening>,
    unreachable: BTreeSet<String>,
    /// WHO LISTENS ON WHAT: each channel a row above listens to, the patterns of the topics it is on, and the inbox
    /// every message on one is left in (`Member::listen`).
    listeners: Vec<(String, Vec<String>, Inbox)>,
    /// The patterns each client is subscribed to, by client.
    subscribed: Vec<BTreeSet<String>>,
    /// Messages no row listened for yet, the latest few, handed to the first that listens on a channel they are on:
    /// what arrives between the boot and a row's first listening is not lost.
    unheard: Vec<Message>,
}

/// How many messages no row listened for are kept for one that has yet to.
const UNHEARD_KEPT: usize = 64;

fn strs(names: &[String]) -> Vec<&str> {
    names.iter().map(String::as_str).collect()
}

fn no_wildcard(pattern: &str) -> bool {
    !pattern.contains('+') && !pattern.contains('#')
}

impl Mqtt {
    /// The store the member keeps what it carries in.
    pub fn beliefs(&self) -> &Store {
        &self.beliefs
    }

    pub fn new(beliefs: &Store, me: &str, clients: Vec<(Option<String>, Box<dyn Client>)>) -> Self {
        Mqtt {
            beliefs: beliefs.clone(),
            me: me.to_string(),
            clients,
            inbox: Inbox::default(),
            listening: Vec::new(),
            unreachable: BTreeSet::new(),
            listeners: Vec::new(),
            subscribed: Vec::new(),
            unheard: Vec::new(),
        }
    }

    /// A message on a chat's topic, `{"from": …, "text": …}` or bare text, as the words on a chat's channel a row is
    /// handed: who wrote them where they name an IRI.
    fn words_of(payload: &[u8]) -> Words {
        let said: Json = serde_json::from_slice(payload)
            .ok()
            .filter(Json::is_object)
            .unwrap_or_else(|| serde_json::json!({"text": String::from_utf8_lossy(payload)}));
        let text = match said.get("text") {
            Some(Json::String(t)) => t.trim().to_string(),
            Some(other) => other.to_string().trim().to_string(),
            None => String::new(),
        };
        Words {
            from: said
                .get("from")
                .and_then(Json::as_str)
                .filter(|f| f.starts_with("http"))
                .map(str::to_string),
            ..Words::said(&text)
        }
    }

    fn common(&self) -> Result<Vec<String>, Error> {
        self.beliefs.graphs_of(&[BELIEF], &Within::common())
    }

    fn rows_of(&self, text: &str, values: &[(&str, Value)]) -> Result<Vec<orexis::store::Row>, Error> {
        let common = self.common()?;
        self.beliefs.rows(&bind(text, values)?, &strs(&common))
    }

    fn patterns(&self, text: &str, values: &[(&str, Value)]) -> Result<Vec<String>, Error> {
        Ok(self
            .rows_of(text, values)?
            .iter()
            .filter_map(|r| value(r, "pattern"))
            .collect())
    }

    /// The filter patterns of the topic `agent` listens to itself: where it is told things.
    fn listens(&self, agent: &str) -> Result<Vec<String>, Error> {
        const LISTENS_Q: &str = "PREFIX mqtt4ssn: <https://www.w3id.org/MQTT4SSN-Ontology#>
        SELECT ?pattern WHERE {
          $agent mqtt4ssn:listensToTopic ?topic .
          ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
        ORDER BY ?pattern";
        self.patterns(LISTENS_Q, &[("agent", Value::iri(agent))])
    }

    /// The topics of the chats this agent is in, each with a filter pattern matching it, by topic.
    fn chat_topics(&self) -> Result<Vec<(String, String)>, Error> {
        const CHAT_TOPICS_Q: &str = "PREFIX mqtt4ssn: <https://www.w3id.org/MQTT4SSN-Ontology#>
        PREFIX speech: <http://example.org/orexis/speech#>
        SELECT ?topic ?pattern WHERE {
          ?chat a speech:Chat ; speech:participant $agent ; speech:channel ?topic . ?topic a mqtt4ssn:Topic .
          ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern } ORDER BY ?topic ?pattern";
        Ok(self
            .rows_of(CHAT_TOPICS_Q, &[("agent", Value::iri(self.me.as_str()))])?
            .iter()
            .filter_map(|r| Some((iri(r, "topic")?, value(r, "pattern")?)))
            .collect())
    }

    /// The clients `thing` is reached over, by index: each broker this member is connected to that the world says
    /// carries it; the one client, where the member has one.
    fn over(&self, thing: &str) -> Result<Vec<usize>, Error> {
        /// THE BROKERS A THING IS REACHED OVER: the ones it is connected to where it is a client, and otherwise the
        /// ones of the client hosting it or the system it is part of.
        const BROKERS_Q: &str = "PREFIX mqtt4ssn: <https://www.w3id.org/MQTT4SSN-Ontology#>
        PREFIX ssn: <http://www.w3.org/ns/ssn/>
        SELECT DISTINCT ?broker WHERE {
          { $thing mqtt4ssn:isConnectedToBroker ?broker }
          UNION { ?client mqtt4ssn:hosts ?system ; mqtt4ssn:isConnectedToBroker ?broker . ?system ssn:hasSubSystem* $thing } }
        ORDER BY ?broker";
        if let Some(i) = self.clients.iter().position(|(b, _)| b.is_none()) {
            return Ok(vec![i]);
        }
        let carried: Vec<String> = self
            .rows_of(BROKERS_Q, &[("thing", Value::iri(thing))])?
            .iter()
            .filter_map(|r| iri(r, "broker"))
            .collect();
        Ok(carried
            .iter()
            .filter_map(|b| self.clients.iter().position(|(c, _)| c.as_deref() == Some(b.as_str())))
            .collect())
    }

    /// The filter patterns of the topics a row above would listen to `channel` on: the agent's own, where it is told
    /// things; a chat's topic, where its words are; and a sensor's, where it publishes.
    fn patterns_of(&self, channel: &str) -> Result<Vec<String>, Error> {
        if channel == self.me {
            return self.listens(channel);
        }
        let chat: Vec<String> = self
            .chat_topics()?
            .into_iter()
            .filter(|(topic, _)| topic == channel)
            .map(|(_, pattern)| pattern)
            .collect();
        if !chat.is_empty() {
            return Ok(chat);
        }
        const OBSERVES_Q: &str = "PREFIX mqtt4ssn: <https://www.w3id.org/MQTT4SSN-Ontology#>
        SELECT ?pattern WHERE {
          $sensor mqtt4ssn:observesTopic ?topic .
          ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
        ORDER BY ?pattern";
        self.patterns(OBSERVES_Q, &[("sensor", Value::iri(channel))])
    }

    /// Whether a row above may listen to `channel` on the bus: the agent itself where it listens to a topic, a chat's
    /// topic, or a sensor publishing on one.
    pub fn listened(&self, channel: &str) -> Result<bool, Error> {
        Ok(!self.patterns_of(channel)?.is_empty())
    }

    /// Subscribe each client in `over` to `pattern`, once.
    fn subscribe(&mut self, over: &[usize], pattern: &str) -> Result<(), Error> {
        self.subscribed.resize_with(self.clients.len(), BTreeSet::new);
        for &i in over {
            if self.subscribed[i].insert(pattern.to_string()) {
                self.clients[i].1.subscribe(pattern)?;
            }
        }
        Ok(())
    }

    /// LISTEN TO `channel` FOR A ROW ABOVE: every pattern of its topics subscribed to over each broker it is reached
    /// over — the agent's own and a chat's over every broker it is connected to — and every message on one left in
    /// `inbox`, those that arrived before anybody listened among them; the patterns.
    pub fn listen_on(&mut self, channel: &str, inbox: Inbox) -> Result<Vec<String>, Error> {
        let patterns = self.patterns_of(channel)?;
        let own = channel == self.me || self.chat_topics()?.iter().any(|(topic, _)| topic == channel);
        let over: Vec<usize> = if own {
            (0..self.clients.len()).collect()
        } else {
            self.over(channel)?
        };
        for pattern in &patterns {
            self.subscribe(&over, pattern)?;
        }
        log::info!(
            "{} listening on {patterns:?} for {}",
            local_of(&self.me),
            local_of(channel)
        );
        let (early, rest): (Vec<Message>, Vec<Message>) = std::mem::take(&mut self.unheard)
            .into_iter()
            .partition(|m| patterns.iter().any(|p| matches(p, &m.topic)));
        self.unheard = rest;
        let chat = self.chat_topics()?.iter().any(|(topic, _)| topic == channel);
        inbox.deliver_all(
            early
                .into_iter()
                .map(|m| Message {
                    topic: channel.to_string(),
                    payload: if chat {
                        Self::words_of(&m.payload).bytes()
                    } else {
                        m.payload
                    },
                    at: m.at,
                })
                .collect(),
        );
        self.listeners.push((channel.to_string(), patterns.clone(), inbox));
        Ok(patterns)
    }

    /// ROUTE ONE MESSAGE: left, as one, with every row listening on a channel whose topic's filter matches `topic`, the
    /// channel as the message's topic — a chat's as the words on its channel, a document or a reading as it came — and
    /// kept for one yet to listen where none does. The channels it was left on, in the order they were listened to.
    pub fn handle(&mut self, topic: &str, payload: &[u8], at: DateTime) -> Result<Vec<String>, Error> {
        let chats: BTreeSet<String> = self.chat_topics()?.into_iter().map(|(topic, _)| topic).collect();
        let mut handed: Vec<String> = Vec::new();
        let mut batches: Vec<(Inbox, Vec<Message>)> = Vec::new();
        for (channel, patterns, inbox) in &self.listeners {
            if !patterns.iter().any(|p| matches(p, topic)) || handed.contains(channel) {
                continue;
            }
            handed.push(channel.clone());
            let message = Message {
                topic: channel.clone(),
                payload: if chats.contains(channel) {
                    Self::words_of(payload).bytes()
                } else {
                    payload.to_vec()
                },
                at: Some(at),
            };
            match batches.iter_mut().find(|(i, _)| i.is(inbox)) {
                Some((_, batch)) => batch.push(message),
                None => batches.push((inbox.clone(), vec![message])),
            }
        }
        for (inbox, batch) in batches {
            inbox.deliver_all(batch);
        }
        if handed.is_empty() {
            log::debug!("{}: a message on {topic} nobody listens for yet", local_of(&self.me));
            self.unheard.push(Message {
                topic: topic.to_string(),
                payload: payload.to_vec(),
                at: Some(at),
            });
            let over = self.unheard.len().saturating_sub(UNHEARD_KEPT);
            self.unheard.drain(..over);
        }
        Ok(handed)
    }

    /// Whether `who` is an agent, whom a document is told to on the bus, since a person's is not the bus's.
    pub fn is_agent(&self, who: &str) -> Result<bool, Error> {
        const AGENT_Q: &str = "PREFIX orexis: <http://example.org/orexis#> ASK { $who a orexis:Agent }";
        let common = self.common()?;
        self.beliefs
            .ask(&bind(AGENT_Q, &[("who", Value::iri(who))])?, &strs(&common))
    }

    /// Whether this member reaches `device`.
    pub fn reaches(&self, device: &str) -> Result<bool, Error> {
        /// WHAT THIS MEMBER REACHES: a device that publishes on a topic, or listens on one, or whose board does.
        const REACHES_Q: &str = "PREFIX mqtt4ssn: <https://www.w3id.org/MQTT4SSN-Ontology#>
        PREFIX ssn: <http://www.w3.org/ns/ssn/>
        ASK { { $device mqtt4ssn:observesTopic ?topic } UNION { $device mqtt4ssn:listensToTopic ?topic }
              UNION { ?board ssn:hasSubSystem $device ; mqtt4ssn:listensToTopic ?topic } }";
        let common = self.common()?;
        self.beliefs
            .ask(&bind(REACHES_Q, &[("device", Value::iri(device))])?, &strs(&common))
    }

    /// Whether `device` takes commands on a topic, its own or its board's: a channel the bus is sent on.
    pub fn takes_commands(&self, device: &str) -> Result<bool, Error> {
        const TAKES_Q: &str = "PREFIX mqtt4ssn: <https://www.w3id.org/MQTT4SSN-Ontology#>
        PREFIX ssn: <http://www.w3.org/ns/ssn/>
        ASK { { $device mqtt4ssn:listensToTopic ?topic } UNION { ?board ssn:hasSubSystem $device ; mqtt4ssn:listensToTopic ?topic } }";
        let common = self.common()?;
        self.beliefs
            .ask(&bind(TAKES_Q, &[("device", Value::iri(device))])?, &strs(&common))
    }

    /// Publish a step's command on the topic the actuator listens to, or its board's; not retained, since a command is
    /// an act and a retained one would be taken again by a device that reconnects.
    pub fn actuate(&mut self, actuator: &str, payload: &Json) -> Result<bool, Error> {
        /// WHERE AN ACTUATOR TAKES COMMANDS: a topic it listens to itself, or its board's.
        const ACTUATES_Q: &str = "PREFIX mqtt4ssn: <https://www.w3id.org/MQTT4SSN-Ontology#>
        PREFIX ssn: <http://www.w3.org/ns/ssn/>
        SELECT ?pattern WHERE {
          { $actuator mqtt4ssn:listensToTopic ?topic } UNION { ?board ssn:hasSubSystem $actuator ; mqtt4ssn:listensToTopic ?topic }
          ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
        ORDER BY ?pattern";
        let names: Vec<String> = self
            .patterns(ACTUATES_Q, &[("actuator", Value::iri(actuator))])?
            .into_iter()
            .filter(|p| no_wildcard(p))
            .collect();
        let Some(name) = names.first() else {
            return Ok(self.unreached(actuator, "the command is not sent"));
        };
        if !self.publish(actuator, name, payload, false)? {
            return Ok(false);
        }
        self.unreachable.remove(actuator);
        log::info!("{}: {} on {name}", local_of(actuator), dumps(payload));
        Ok(true)
    }

    /// Publish a document on the topic the agent `to` listens to, by a pattern with no wildcard; not retained. A
    /// document to a person is not the bus's, and is passed over in silence.
    pub fn tell(&mut self, to: &str, document: &[u8]) -> Result<bool, Error> {
        if !self.is_agent(to)? {
            return Ok(false);
        }
        let names: Vec<String> = self.listens(to)?.into_iter().filter(|p| no_wildcard(p)).collect();
        let Some(name) = names.first() else {
            return Ok(self.unreached(to, "nothing said to it is sent"));
        };
        let over = self.over(to)?;
        let Some(first) = over.first() else {
            return Ok(self.unshared(to, "nothing said to it is sent"));
        };
        self.unreachable.remove(to);
        self.clients[*first].1.publish(name, document, false)?;
        log::info!("told {} on {name}", local_of(to));
        Ok(true)
    }

    /// A command to `device` out, as the JSON document the firmware reads, over the first broker this member shares
    /// with it; false, said once, where it shares none.
    pub fn publish(&mut self, device: &str, topic: &str, payload: &Json, retain: bool) -> Result<bool, Error> {
        let over = self.over(device)?;
        let Some(first) = over.first() else {
            return Ok(self.unshared(device, "no command is sent"));
        };
        self.clients[*first]
            .1
            .publish(topic, dumps(payload).as_bytes(), retain)?;
        Ok(true)
    }

    /// Whatever the clients hold open, closed.
    pub fn stop(&mut self) {
        for (_, client) in &mut self.clients {
            client.stop();
        }
    }

    fn unreached(&mut self, who: &str, what: &str) -> bool {
        if self.unreachable.insert(who.to_string()) {
            log::warn!("{} listens on no topic name, so {what}", local_of(who));
        }
        false
    }

    fn unshared(&mut self, who: &str, what: &str) -> bool {
        if self.unreachable.insert(who.to_string()) {
            log::warn!(
                "{} is on no broker this agent is connected to, so {what}",
                local_of(who)
            );
        }
        false
    }
}

// --- bringing the bus up ---------------------------------------------------------------------------------------------

/// What one session is brought up with: the broker it is connected to, where it listens, the agent's name and
/// credential, and its certificate where the url is `mqtts`.
#[derive(Clone, Debug, PartialEq)]
pub struct Session {
    pub broker: String,
    pub host: String,
    pub port: u16,
    pub client_id: String,
    pub username: String,
    pub password: Option<String>,
    /// The authority, the agent's certificate and its key, as paths.
    pub tls: Option<(String, String, String)>,
}

/// Each broker `me` is connected to, by its IRI, with the url the world's deployment graph says it answers at.
/// Refused where the world says nothing of where one answers, since a guess puts a misconfigured agent on the real
/// topics; empty where the agent is connected to none.
pub fn reached(beliefs: &Store, me: &str) -> Result<Vec<(String, String)>, Error> {
    /// THE BROKERS THE SELF IS CONNECTED TO, AND WHERE EACH ANSWERS: connected as the society says
    /// (`mqtt4ssn:isConnectedToBroker`), answering at the `schema:url` the world's deployment graph states of it.
    const REACHED_Q: &str = "PREFIX mqtt4ssn: <https://www.w3id.org/MQTT4SSN-Ontology#>
    PREFIX schema: <https://schema.org/>
    SELECT ?broker ?url WHERE { $me mqtt4ssn:isConnectedToBroker ?broker
      OPTIONAL { ?broker schema:url ?url } } ORDER BY ?broker ?url";
    let mut known = beliefs.graphs_of(&[BELIEF], &Within::common())?;
    known.extend(beliefs.graphs_of(&[orexis::ontology::DEPLOYMENT], &Within::common())?);
    let mut out: Vec<(String, String)> = Vec::new();
    for row in beliefs.rows(&bind(REACHED_Q, &[("me", Value::iri(me))])?, &strs(&known))? {
        let Some(broker) = iri(&row, "broker") else { continue };
        if out.iter().any(|(b, _)| *b == broker) {
            continue;
        }
        let Some(url) = value(&row, "url") else {
            return Err(Error::Evaluation(format!(
                "this agent is connected to {} and the world's deployment says nothing of where it answers — run \
                 `orexis-onboard`, which derives it",
                local_of(&broker)
            )));
        };
        out.push((broker, url));
    }
    Ok(out)
}

/// The sessions of an agent connected to `brokers`, each by its IRI with the url it answers at: a client per
/// broker, under the agent's credential from its environment, with its certificate where the url is `mqtts`.
/// Refused without a broker or a credential, since a guess puts a misconfigured agent on the real topics.
pub fn sessions(
    me: &str,
    brokers: &[(String, String)],
    env: &dyn Fn(&str) -> Option<String>,
) -> Result<Vec<Session>, Error> {
    if brokers.is_empty() {
        return Err(Error::Evaluation(
            "this agent is connected to no broker (mqtt4ssn:isConnectedToBroker) — it is told where its bus is by its \
             world, never guesses"
                .into(),
        ));
    }
    let Some(username) = env("MQTT_USERNAME").filter(|u| !u.is_empty()) else {
        return Err(Error::Evaluation(
            "no MQTT_USERNAME in the environment — this agent has no credential for the bus. Run `orexis-mqtt <world>` \
             and regenerate the compose file."
                .into(),
        ));
    };
    let (ca, cert, key) = (env("MQTT_CA"), env("MQTT_CERT"), env("MQTT_KEY"));
    let mut out = Vec::new();
    for (broker, text) in brokers {
        let refused = || {
            Error::Evaluation(format!(
                "the world's deployment says {} is at '{text}', which is no mqtt:// or mqtts:// url",
                local_of(broker)
            ))
        };
        let (scheme, rest) = text.split_once("://").ok_or_else(refused)?;
        if scheme != "mqtt" && scheme != "mqtts" {
            return Err(refused());
        }
        let authority = rest.split('/').next().unwrap_or_default();
        let (host, port) = match authority.rsplit_once(':') {
            Some((h, p)) => (h.to_string(), p.parse::<u16>().map_err(|_| refused())?),
            None => (authority.to_string(), if scheme == "mqtt" { 1883 } else { 8883 }),
        };
        if host.is_empty() {
            return Err(refused());
        }
        let tls = if scheme == "mqtts" {
            match (&ca, &cert, &key) {
                (Some(ca), Some(cert), Some(key)) => Some((ca.clone(), cert.clone(), key.clone())),
                _ => {
                    return Err(Error::Evaluation(format!(
                        "{} is at {text}, and the environment holds no MQTT_CA, MQTT_CERT and MQTT_KEY to reach it with",
                        local_of(broker)
                    )));
                }
            }
        } else {
            None
        };
        out.push(Session {
            broker: broker.clone(),
            host,
            port,
            client_id: local_of(me),
            username: username.clone(),
            password: env("MQTT_PASSWORD"),
            tls,
        });
    }
    Ok(out)
}

/// A session over rumqttc: the mind publishes through its client, which queues a request and never waits, and the
/// event loop is a task, handing every message to the inbox.
pub struct Rumqtt {
    client: rumqttc::AsyncClient,
}

/// How many requests a session queues for its event loop before one is refused.
const REQUESTS: usize = 256;

impl Rumqtt {
    /// The session up, and what listens on it, every message it receives left in `inbox`.
    pub fn connect(session: &Session, inbox: Inbox) -> Result<(Self, Listening), Error> {
        let mut options = rumqttc::MqttOptions::new(&session.client_id, &session.host, session.port);
        options.set_credentials(session.username.clone(), session.password.clone().unwrap_or_default());
        options.set_keep_alive(Duration::from_secs(30));
        if let Some((ca, cert, key)) = &session.tls {
            let read = |path: &str| std::fs::read(path).map_err(|e| Error::Evaluation(format!("{path}: {e}")));
            options.set_transport(rumqttc::Transport::tls_with_config(rumqttc::TlsConfiguration::Simple {
                ca: read(ca)?,
                alpn: None,
                client_auth: Some((read(cert)?, read(key)?)),
            }));
        }
        //  NO RUNTIME OF ITS OWN: the event loop is polled among the process's tasks. rumqttc's blocking client makes
        //  a runtime with its connection, and this is called among those tasks, where dropping one panics - the
        //  agent died as it connected, every boot, once its packages were started inside its runtime.
        let (client, mut events) = rumqttc::AsyncClient::new(options, REQUESTS);
        let broker = local_of(&session.broker);
        let listening = Box::pin(async move {
            loop {
                match events.poll().await {
                    Ok(rumqttc::Event::Incoming(rumqttc::Packet::Publish(p))) => {
                        inbox.deliver(&p.topic, &p.payload, None)
                    }
                    Ok(_) => {}
                    Err(rumqttc::ConnectionError::RequestsDone) => break,
                    Err(e) => {
                        log::warn!("{broker}: {e}; reconnecting");
                        tokio::time::sleep(Duration::from_secs(1)).await;
                    }
                }
            }
        });
        log::info!(
            "{} on {} at {}:{}{}",
            session.client_id,
            local_of(&session.broker),
            session.host,
            session.port,
            if session.tls.is_some() {
                " with a certificate"
            } else {
                ""
            }
        );
        Ok((Rumqtt { client }, listening))
    }
}

impl Client for Rumqtt {
    fn subscribe(&mut self, pattern: &str) -> Result<(), Error> {
        self.client
            .try_subscribe(pattern, rumqttc::QoS::AtLeastOnce)
            .map_err(|e| Error::Evaluation(format!("subscribing to {pattern}: {e}")))
    }

    fn publish(&mut self, topic: &str, payload: &[u8], retain: bool) -> Result<(), Error> {
        self.client
            .try_publish(topic, rumqttc::QoS::AtLeastOnce, retain, payload.to_vec())
            .map_err(|e| Error::Evaluation(format!("publishing on {topic}: {e}")))
    }

    fn stop(&mut self) {
        let _ = self.client.try_disconnect();
    }
}

/// The agent's side of the bus, up: a rumqttc session per broker the world says it is connected to, where the
/// world's deployment says each answers, under the credential its environment holds.
pub fn connect(beliefs: &Store, me: &str, env: &dyn Fn(&str) -> Option<String>) -> Result<Mqtt, Error> {
    let mut member = Mqtt::new(beliefs, me, Vec::new());
    for session in sessions(me, &reached(beliefs, me)?, env)? {
        let (client, listening) = Rumqtt::connect(&session, member.inbox.clone())?;
        member.listening.push(listening);
        member.clients.push((Some(session.broker.clone()), Box::new(client)));
    }
    Ok(member)
}

impl Mqtt {
    /// Whether `channel` is the topic of a chat this agent is in.
    pub fn is_chat(&self, channel: &str) -> Result<bool, Error> {
        Ok(self.chat_topics()?.iter().any(|(topic, _)| topic == channel))
    }

    /// `words` said on the topic node `channel`, a chat's topic, by the one pattern naming it with no wildcard, as
    /// `{"from": the agent, "text": …}` so the agent knows its own when the broker hands it back; a topic shows no
    /// writing, so words saying only that send nothing. False where the channel is no topic of a chat this agent is
    /// in, or it is on no broker of this member's.
    pub fn say_on(&mut self, channel: &str, words: &Words) -> Result<bool, Error> {
        if words.writing {
            return Ok(false);
        }
        let names: Vec<String> = self
            .chat_topics()?
            .into_iter()
            .filter(|(topic, pattern)| topic == channel && no_wildcard(pattern))
            .map(|(_, pattern)| pattern)
            .collect();
        let Some(name) = names.first() else { return Ok(false) };
        let me = self.me.clone();
        let over = self.over(&me)?;
        let Some(first) = over.first() else {
            return Ok(self.unshared(&me, "nothing is said on a chat's topic"));
        };
        let payload = dumps(&serde_json::json!({"from": me, "text": words.text}));
        self.clients[*first].1.publish(name, payload.as_bytes(), false)?;
        Ok(true)
    }
}

#[cfg(test)]
mod tests {
    //! The MQTT driver over a board on a bus and a stand-in client, held as `orexis-transport-mqtt/tests/
    //! test_driver.py` holds it: what the agent subscribes to, whose a message is, where a command goes and as what,
    //! how a message becomes observations through sensing — and MQTT's own filter matching.

    use std::collections::BTreeMap;
    use std::path::{Path, PathBuf};

    use orexis::snapshots::{ME, now, stand_in, stand_in_with};

    use super::*;
    use std::sync::{Arc, Mutex};

    const TEST: &str = "http://example.org/test#";

    /// A session is made among the agent's tasks, where its packages are started, and is used and dropped there:
    /// it brings no runtime of its own, which dropped among them panics. It queues what it is asked and waits for
    /// no broker.
    #[tokio::test]
    async fn a_session_is_made_used_and_dropped_among_the_agents_tasks() {
        let session = Session {
            broker: format!("{TEST}broker"),
            host: "localhost".into(),
            port: 1,
            client_id: "keeper".into(),
            username: "keeper".into(),
            password: None,
            tls: None,
        };
        let (mut client, listening) = Rumqtt::connect(&session, Inbox::default()).unwrap();
        client.subscribe("sensors/+/reading").unwrap();
        client.publish("sensors/keeper/command", b"{}", false).unwrap();
        client.stop();
        drop(listening);
        drop(client);
    }
    const BOARD_MESSAGE: &[u8] = br#"{"temperature": 21.5, "humidity": 0.61}"#;

    /// What a client was asked: the patterns subscribed and what was published, as (topic, payload, retained).
    #[derive(Default)]
    struct Asked {
        subscribed: Vec<String>,
        published: Vec<(String, String, bool)>,
    }

    #[derive(Clone, Default)]
    struct Fake(Arc<Mutex<Asked>>);

    impl Client for Fake {
        fn subscribe(&mut self, pattern: &str) -> Result<(), Error> {
            self.0.lock().unwrap().subscribed.push(pattern.to_string());
            Ok(())
        }

        fn publish(&mut self, topic: &str, payload: &[u8], retain: bool) -> Result<(), Error> {
            let payload = String::from_utf8_lossy(payload).into_owned();
            self.0
                .lock()
                .unwrap()
                .published
                .push((topic.to_string(), payload, retain));
            Ok(())
        }
    }

    fn world() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/worlds/a_board_on_a_bus.trig")
    }

    fn bus(store: &Store) -> (Mqtt, Fake) {
        let client = Fake::default();
        (Mqtt::new(store, ME, vec![(None, Box::new(client.clone()))]), client)
    }

    fn t(local: &str) -> String {
        format!("{TEST}{local}")
    }

    fn sent(topic: &str, payload: &str, retained: bool) -> (String, String, bool) {
        (topic.to_string(), payload.to_string(), retained)
    }

    #[test]
    fn the_driver_listens_where_a_sensor_a_row_listens_to_publishes() {
        let store = stand_in(&world());
        let (mut driver, client) = bus(&store);
        assert!(
            client.0.lock().unwrap().subscribed.is_empty(),
            "nothing is subscribed to until a row listens"
        );
        assert!(driver.listened(&t("hygro")).unwrap());
        assert!(
            driver.listened(&t("photometer")).unwrap(),
            "the neighbour's lamp is on the bus too: which sensors are the agent's is sensing's to say"
        );
        assert!(
            !driver.listened(&t("board")).unwrap(),
            "a board publishes nothing of its own"
        );
        let inbox = Inbox::default();
        assert_eq!(
            driver.listen_on(&t("hygro"), inbox.clone()).unwrap(),
            ["sensors/board/reading"]
        );
        driver.listen_on(&t("thermo"), inbox).unwrap();
        assert_eq!(
            client.0.lock().unwrap().subscribed,
            ["sensors/board/reading"],
            "one board, one topic, two sensors, subscribed once"
        );
    }

    #[test]
    fn a_document_for_a_sensor_goes_to_the_topic_its_board_listens_on_not_retained() {
        let store = stand_in(&world());
        let (mut driver, client) = bus(&store);
        assert!(
            driver
                .actuate(&t("hygro"), &serde_json::json!({"sense": true}))
                .unwrap()
        );
        assert_eq!(
            client.0.lock().unwrap().published,
            [sent("sensors/board/command", r#"{"sense": true}"#, false)]
        );
    }

    #[test]
    fn a_sensor_whose_board_listens_nowhere_takes_no_command() {
        let store = stand_in(&world());
        let (mut driver, client) = bus(&store);
        assert!(!driver.takes_commands(&t("photometer")).unwrap());
        assert!(
            !driver
                .actuate(&t("probe"), &serde_json::json!({"sense": true}))
                .unwrap()
        );
        assert!(client.0.lock().unwrap().published.is_empty());
    }

    #[test]
    fn one_message_on_the_boards_topic_is_left_once_with_each_sensor_listened_to_on_it() {
        let store = stand_in(&world());
        let (mut driver, _) = bus(&store);
        let inbox = Inbox::default();
        driver.listen_on(&t("hygro"), inbox.clone()).unwrap();
        driver.listen_on(&t("thermo"), inbox.clone()).unwrap();
        driver.handle("sensors/board/reading", BOARD_MESSAGE, now()).unwrap();
        let left: Vec<(String, Vec<u8>)> = inbox.take().into_iter().map(|m| (m.topic, m.payload)).collect();
        assert_eq!(
            left,
            [
                (t("hygro"), BOARD_MESSAGE.to_vec()),
                (t("thermo"), BOARD_MESSAGE.to_vec())
            ],
            "each sensor's channel, the message as it came"
        );
    }

    #[test]
    fn a_neighbours_message_on_the_same_broker_is_left_with_nobody() {
        let store = stand_in(&world());
        let (mut driver, _) = bus(&store);
        let inbox = Inbox::default();
        driver.listen_on(&t("hygro"), inbox.clone()).unwrap();
        driver
            .handle("sensors/lamp/reading", br#"{"value": 300}"#, now())
            .unwrap();
        driver.handle("sensors/nowhere", BOARD_MESSAGE, now()).unwrap();
        assert!(inbox.take().is_empty());
    }

    #[test]
    fn a_message_that_came_before_anybody_listened_is_left_with_the_first_that_does() {
        let store = stand_in(&world());
        let (mut driver, _) = bus(&store);
        driver.handle("sensors/board/reading", BOARD_MESSAGE, now()).unwrap();
        let inbox = Inbox::default();
        driver.listen_on(&t("thermo"), inbox.clone()).unwrap();
        let left: Vec<String> = inbox.take().into_iter().map(|m| m.topic).collect();
        assert_eq!(left, [t("thermo")]);
    }

    fn env(pairs: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> + use<> {
        let map: BTreeMap<String, String> = pairs.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect();
        move |name| map.get(name).cloned()
    }

    #[test]
    fn the_environment_names_each_session_and_its_credential() {
        let broker = t("broker");
        let said = [(broker.clone(), "mqtt://broker:1888".to_string())];
        let by_password = env(&[("MQTT_USERNAME", "keeper"), ("MQTT_PASSWORD", "s3cret")]);
        let found = sessions(ME, &said, &by_password).unwrap();
        assert_eq!(
            found,
            [Session {
                broker: broker.clone(),
                host: "broker".into(),
                port: 1888,
                client_id: "keeper".into(),
                username: "keeper".into(),
                password: Some("s3cret".into()),
                tls: None,
            }],
            "an mqtt:// url, so by password"
        );
        let tls = [(broker.clone(), "mqtts://broker:8888".to_string())];
        let by_certificate = env(&[
            ("MQTT_USERNAME", "keeper"),
            ("MQTT_CA", "ca.pem"),
            ("MQTT_CERT", "keeper.pem"),
            ("MQTT_KEY", "keeper.key"),
        ]);
        let found = sessions(ME, &tls, &by_certificate).unwrap();
        assert_eq!(
            found[0].tls,
            Some(("ca.pem".into(), "keeper.pem".into(), "keeper.key".into()))
        );
        assert_eq!(found[0].port, 8888);
    }

    #[test]
    fn a_session_is_refused_rather_than_a_broker_or_a_credential_guessed() {
        let at = |url: &str| vec![(t("broker"), url.to_string())];
        for (brokers, pairs, refusal) in [
            (Vec::new(), vec![("MQTT_USERNAME", "keeper")], "connected to no broker"),
            (
                at("broker:1888"),
                vec![("MQTT_USERNAME", "keeper")],
                "no mqtt:// or mqtts:// url",
            ),
            (
                at("mqtts://broker:8888"),
                vec![("MQTT_USERNAME", "keeper")],
                "no MQTT_CA",
            ),
            (at("mqtt://broker:1888"), Vec::new(), "MQTT_USERNAME"),
        ] {
            let refused = sessions(ME, &brokers, &env(&pairs)).unwrap_err().to_string();
            assert!(refused.contains(refusal), "{refused}");
        }
    }

    /// A SECOND BROKER, which the keeper connects to as well, and a peer on it alone.
    const TWO_BROKERS: &str = r#"
GRAPH :world {
  :elsewhere a mqtt4ssn:Broker .
  :keeper mqtt4ssn:isConnectedToBroker :elsewhere .
  :peer a orexis:Agent , mqtt4ssn:Client ; mqtt4ssn:isConnectedToBroker :elsewhere ; mqtt4ssn:listensToTopic :peer_inbox .
  :peer_filter a mqtt4ssn:TopicFilter ; mqtt4ssn:hasFilterPattern "agents/peer/inbox" ; mqtt4ssn:matchesTopic :peer_inbox .
}
"#;

    #[test]
    fn each_topic_goes_over_a_broker_the_agent_shares_with_its_client() {
        let store = stand_in_with(&world(), TWO_BROKERS);
        let (here, there) = (Fake::default(), Fake::default());
        let mut mqtt = Mqtt::new(
            &store,
            ME,
            vec![
                (Some(t("broker")), Box::new(here.clone())),
                (Some(t("elsewhere")), Box::new(there.clone())),
            ],
        );
        mqtt.listen_on(&t("hygro"), Inbox::default()).unwrap();
        assert_eq!(here.0.lock().unwrap().subscribed, ["sensors/board/reading"]);
        assert!(there.0.lock().unwrap().subscribed.is_empty());
        assert!(mqtt.actuate(&t("board"), &serde_json::json!({"dose_ml": 250})).unwrap());
        assert!(mqtt.tell(&t("peer"), b"{}").unwrap());
        let topics = |f: &Fake| {
            f.0.lock()
                .unwrap()
                .published
                .iter()
                .map(|p| p.0.clone())
                .collect::<Vec<_>>()
        };
        assert_eq!(topics(&here), ["sensors/board/command"]);
        assert_eq!(topics(&there), ["agents/peer/inbox"]);
        let alone_client = Fake::default();
        let mut alone = Mqtt::new(&store, ME, vec![(Some(t("broker")), Box::new(alone_client.clone()))]);
        assert!(!alone.tell(&t("peer"), b"{}").unwrap());
        assert!(!alone.tell(&t("peer"), b"{}").unwrap());
        assert!(alone_client.0.lock().unwrap().published.is_empty());
    }

    #[test]
    fn filter_matching_is_mqtts_own() {
        assert!(matches("sensors/board/reading", "sensors/board/reading"));
        assert!(matches("sensors/+/reading", "sensors/board/reading"));
        assert!(!matches("sensors/+/reading", "sensors/a/b/reading"));
        assert!(matches("sensors/#", "sensors/board/reading") && matches("sensors/#", "sensors"));
        assert!(matches("#", "anything/at/all") && !matches("#", "$SYS/broker/load"));
        assert!(
            !matches("sensors/#/reading", "sensors/board/reading"),
            "# ends a filter or matches nothing"
        );
        assert!(!matches("sensors/board", "sensors/board/reading"));
    }

    #[test]
    fn a_steps_command_goes_to_the_topic_the_actuator_listens_on_and_is_not_retained() {
        let store = stand_in(&world());
        let (mut driver, client) = bus(&store);
        assert!(
            driver
                .actuate(&t("board"), &serde_json::json!({"dose_ml": 250}))
                .unwrap()
        );
        assert_eq!(
            client.0.lock().unwrap().published,
            [sent("sensors/board/command", r#"{"dose_ml": 250}"#, false)]
        );
    }

    #[test]
    fn an_actuator_that_listens_nowhere_is_sent_nothing() {
        let store = stand_in(&world());
        let (mut driver, client) = bus(&store);
        let dose = serde_json::json!({"dose_ml": 250});
        assert!(!driver.actuate(&t("probe"), &dose).unwrap());
        assert!(!driver.actuate(&t("probe"), &dose).unwrap());
        assert!(!driver.tell(&t("probe"), b"{}").unwrap());
        assert!(!driver.actuate(&t("nobody"), &dose).unwrap());
        assert!(client.0.lock().unwrap().published.is_empty());
    }

    /// THE KEEPER AND A PEER, each listening on a topic of its own for what the other says.
    const PEERS: &str = r#"
GRAPH :world {
  :keeper mqtt4ssn:listensToTopic :keeper_inbox .
  :keeper_filter a mqtt4ssn:TopicFilter ; mqtt4ssn:hasFilterPattern "agents/keeper/inbox" ; mqtt4ssn:matchesTopic :keeper_inbox .
  :peer a orexis:Agent , mqtt4ssn:Client ; mqtt4ssn:listensToTopic :peer_inbox .
  :peer_filter a mqtt4ssn:TopicFilter ; mqtt4ssn:hasFilterPattern "agents/peer/inbox" ; mqtt4ssn:matchesTopic :peer_inbox .
}
"#;

    #[test]
    fn the_driver_listens_on_the_agents_own_topic_and_tells_a_peer_on_its() {
        let store = stand_in_with(&world(), PEERS);
        let (mut mqtt, client) = bus(&store);
        assert!(
            mqtt.listened(ME).unwrap(),
            "the agent itself is listened on, where it is told things"
        );
        assert_eq!(mqtt.listen_on(ME, Inbox::default()).unwrap(), ["agents/keeper/inbox"]);
        assert!(mqtt.tell(&t("peer"), b"<urn:g> { }").unwrap());
        assert_eq!(
            client.0.lock().unwrap().published,
            [sent("agents/peer/inbox", "<urn:g> { }", false)]
        );
        assert!(
            !mqtt.tell(&t("fern"), b"").unwrap(),
            "a thing that listens nowhere is told nothing"
        );
    }

    #[test]
    fn a_document_on_the_agents_own_topic_is_left_as_it_came_with_whoever_listens_on_the_agent() {
        let store = stand_in_with(&world(), PEERS);
        let (mut mqtt, _) = bus(&store);
        let inbox = Inbox::default();
        mqtt.listen_on(ME, inbox.clone()).unwrap();
        let document = b"<urn:note> { <urn:note> <urn:says> \"hello\" }";
        assert_eq!(
            mqtt.handle("agents/keeper/inbox", document, now()).unwrap(),
            [ME.to_string()]
        );
        let left = inbox.take();
        assert_eq!(
            (left[0].topic.as_str(), left[0].payload.as_slice()),
            (ME, document.as_slice())
        );
    }

    #[test]
    fn a_document_is_dumped_as_python_dumps_it() {
        let doc: Json = serde_json::from_str(r#"{"heat_s": 3600, "z": 0.5, "a": [true, null, "é"]}"#).unwrap();
        assert_eq!(
            dumps(&doc),
            "{\"heat_s\": 3600, \"z\": 0.5, \"a\": [true, null, \"\\u00e9\"]}"
        );
    }

    /// THE KEEPER IN A CHAT WITH ANNA over a topic of the bus, which her phone writes to as she types.
    const CHAT: &str = "
@prefix speech: <http://example.org/orexis/speech#> .
GRAPH :world {
  :anna a schema:Person .
  :keeper_and_anna a speech:Chat ; speech:participant :keeper , :anna ; speech:channel :anna_topic .
  :anna_topic a mqtt4ssn:Topic .
  :anna_filter a mqtt4ssn:TopicFilter ; mqtt4ssn:hasFilterPattern \"chats/keeper_and_anna\" ; mqtt4ssn:matchesTopic :anna_topic .
}
";

    fn chat() -> Store {
        stand_in_with(&world(), CHAT)
    }

    #[test]
    fn words_on_a_chats_topic_are_left_as_words_and_words_sent_there_are_said_as_the_agents() {
        let store = chat();
        let (mut mqtt, client) = bus(&store);
        assert!(mqtt.listened(&t("anna_topic")).unwrap() && mqtt.is_chat(&t("anna_topic")).unwrap());
        let inbox = Inbox::default();
        assert_eq!(
            mqtt.listen_on(&t("anna_topic"), inbox.clone()).unwrap(),
            ["chats/keeper_and_anna"]
        );
        let anna = format!(r#"{{"from": "{}", "text": " hello "}}"#, t("anna"));
        mqtt.handle("chats/keeper_and_anna", anna.as_bytes(), now()).unwrap();
        mqtt.handle("chats/keeper_and_anna", b"how is the fern?", now())
            .unwrap();
        let left: Vec<(String, Words)> = inbox
            .take()
            .into_iter()
            .map(|m| (m.topic, Words::of(&m.payload).unwrap()))
            .collect();
        assert_eq!(
            left,
            [
                (
                    t("anna_topic"),
                    Words {
                        from: Some(t("anna")),
                        ..Words::said("hello")
                    }
                ),
                (t("anna_topic"), Words::said("how is the fern?"))
            ],
            "whose the words are, and whether they are the agent's own, is speech's to judge"
        );
        assert!(mqtt.say_on(&t("anna_topic"), &Words::said("the fern is dry")).unwrap());
        assert_eq!(
            client.0.lock().unwrap().published.last().unwrap(),
            &(
                "chats/keeper_and_anna".to_string(),
                format!(r#"{{"from": "{}", "text": "the fern is dry"}}"#, t("keeper")),
                false
            )
        );
        assert!(
            !mqtt.say_on(&t("board_readings"), &Words::said("x")).unwrap(),
            "a topic of no chat of the agent's is not said on"
        );
    }
}
