//! THE MQTT DRIVER, as `agent/transport/mqtt/driver.py` answers the transport family's contract from MQTT4SSN's
//! words, with the topic filter matching MQTT itself specifies.
//!
//! **WHAT THE WORLD SAYS AND WHAT FOLLOWS**: a sensor speaks MQTT when it `mqtt4ssn:observesTopic` a topic; the agent
//! subscribes to the pattern of every `mqtt4ssn:TopicFilter` matching a topic one of its sensors publishes on, and a
//! message is a sensor's when a pattern of its topic matches the channel. A command goes to the topic the device or
//! its board `mqtt4ssn:listensToTopic`, by a pattern with no wildcard; `{"sleep_s": n}` retained, `{"sense": true}`
//! and a step's command not. Which sensors are the agent's is its observer role's (`cadence::sensors`).
//!
//! **A MESSAGE BECOMES OBSERVATIONS THROUGH SENSING, AND THE TRANSPORT KNOWS NO CODEC**: `handle` calls sensing's
//! `received` once per sensor of the agent's whose pattern matches the topic.
//!
//! **THE MEMBER BRINGS ITSELF UP, AND THE THREAD IS THE CONTAINER'S**: `connect` makes a client per broker the
//! environment names — `MQTT_BROKERS`, each broker's IRI and its url, `MQTT_USERNAME` and `MQTT_PASSWORD`, and
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
use orexis::hash::py_float_repr;
use orexis::ontology::{BELIEF, local_of};
use orexis::store::{Store, Within, iri, value};
use orexis_sensing::cadence::{lapsed, next_lapse, sensors};
use orexis_sensing::received::received;
use orexis_speech::heard::heard;

/// HOW SOON THE MEMBER ASKS A BOARD AGAIN that it told to sense and that has not answered, in seconds of the one
/// timeline. Otherwise it asks when a reading next falls due (`cadence::next_lapse`).
pub const NUDGE_S: f64 = 60.0;

/// THE PATTERNS OF THE FILTERS THAT MATCH THE TOPIC A SENSOR'S BOARD LISTENS ON.
const COMMANDS_Q: &str = "
SELECT ?pattern WHERE {
  ?board ssn:hasSubSystem $sensor ; mqtt4ssn:listensToTopic ?topic .
  ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
ORDER BY ?pattern";

/// WHERE AN ACTUATOR TAKES COMMANDS: a topic it listens to itself, or its board's.
const ACTUATES_Q: &str = "
SELECT ?pattern WHERE {
  { $actuator mqtt4ssn:listensToTopic ?topic } UNION { ?board ssn:hasSubSystem $actuator ; mqtt4ssn:listensToTopic ?topic }
  ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
ORDER BY ?pattern";

/// EVERY PATTERN NAMING A TOPIC A SENSOR PUBLISHES ON, for the sensors the agent reads.
const TOPICS_Q: &str = "
SELECT ?sensor ?pattern WHERE {
  VALUES ?sensor { $sensors } ?sensor mqtt4ssn:observesTopic ?topic .
  ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
ORDER BY ?sensor ?pattern";

/// WHAT THIS MEMBER REACHES: a device that publishes on a topic, or listens on one, or whose board does.
const REACHES_Q: &str = "
ASK { { $device mqtt4ssn:observesTopic ?topic } UNION { $device mqtt4ssn:listensToTopic ?topic }
      UNION { ?board ssn:hasSubSystem $device ; mqtt4ssn:listensToTopic ?topic } }";

/// THE BROKERS A THING IS REACHED OVER: the ones it is connected to where it is a client, and otherwise the ones of
/// the client hosting it or the system it is part of.
const BROKERS_Q: &str = "
SELECT DISTINCT ?broker WHERE {
  { $thing mqtt4ssn:isConnectedToBroker ?broker }
  UNION { ?client mqtt4ssn:hosts ?system ; mqtt4ssn:isConnectedToBroker ?broker . ?system ssn:hasSubSystem* $thing } }
ORDER BY ?broker";

/// WHETHER WHOM A DOCUMENT IS TOLD TO IS AN AGENT, since a person's is not the bus's.
const AGENT_Q: &str = "ASK { $who a orexis:Agent }";

/// WHERE AN AGENT IS TOLD THINGS: the topic it listens to itself.
const LISTENS_Q: &str = "
SELECT ?pattern WHERE {
  $agent mqtt4ssn:listensToTopic ?topic .
  ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern }
ORDER BY ?pattern";

/// THE TOPICS OF THE CHATS THE AGENT IS IN.
const CHAT_TOPICS_Q: &str = "
SELECT ?topic ?pattern WHERE {
  ?chat a speech:Chat ; speech:participant $agent ; speech:channel ?topic . ?topic a mqtt4ssn:Topic .
  ?filter mqtt4ssn:matchesTopic ?topic ; mqtt4ssn:hasFilterPattern ?pattern } ORDER BY ?topic ?pattern";

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
            _ => py_float_repr(n.as_f64().unwrap_or(0.0)),
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

pub use orexis::transport::{Inbox, Message};

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
    /// A person's prose heard on a chat's topic, for the part to hand translation once it lets the member go.
    pub prose: Vec<orexis_speech::prose::Prose>,
    unreachable: BTreeSet<String>,
}

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
            prose: Vec::new(),
            unreachable: BTreeSet::new(),
        }
    }

    /// A message on a chat's topic: `{"from": …, "text": …}` or bare text, the prose it is unless the agent itself said
    /// it.
    fn prose_of(&self, channel: &str, payload: &[u8], at: DateTime) -> Option<orexis_speech::prose::Prose> {
        let said: Json = serde_json::from_slice(payload)
            .ok()
            .filter(Json::is_object)
            .unwrap_or_else(|| serde_json::json!({"text": String::from_utf8_lossy(payload)}));
        let from = said.get("from").and_then(Json::as_str);
        let text = match said.get("text") {
            Some(Json::String(t)) => t.trim().to_string(),
            Some(other) => other.to_string().trim().to_string(),
            None => String::new(),
        };
        if from == Some(self.me.as_str()) || text.is_empty() {
            return None;
        }
        Some(orexis_speech::prose::Prose {
            channel: channel.to_string(),
            sender: from.filter(|f| f.starts_with("http")).map(str::to_string),
            text,
            at: Some(at),
            addressed: None,
            message: None,
            reply: None,
        })
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

    /// The clients `thing` is reached over, by index: each broker this member is connected to that the world says
    /// carries it; the one client, where the member has one.
    fn over(&self, thing: &str) -> Result<Vec<usize>, Error> {
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

    /// Every sensor the agent reads that publishes on a topic, with each pattern naming it.
    fn topics(&self) -> Result<Vec<(String, String)>, Error> {
        let mine = sensors(&self.beliefs)?;
        if mine.is_empty() {
            return Ok(Vec::new());
        }
        let listed: String = mine.iter().map(|s| format!("<{s}> ")).collect();
        Ok(self
            .rows_of(TOPICS_Q, &[("sensors", Value::raw(listed))])?
            .iter()
            .filter_map(|r| Some((iri(r, "sensor")?, value(r, "pattern")?)))
            .collect())
    }

    /// Subscribe to every pattern the world implies for the agent's sensors, and to the topic it listens to itself;
    /// the patterns.
    pub fn open(&mut self) -> Result<Vec<String>, Error> {
        let me = Value::iri(self.me.as_str());
        let mut own: BTreeSet<String> = self
            .patterns(LISTENS_Q, &[("agent", me.clone())])?
            .into_iter()
            .collect();
        own.extend(self.patterns(CHAT_TOPICS_Q, &[("agent", me)])?);
        let mut on: Vec<BTreeSet<String>> = vec![own; self.clients.len()];
        for (sensor, pattern) in self.topics()? {
            for i in self.over(&sensor)? {
                on[i].insert(pattern.clone());
            }
        }
        let mut all = BTreeSet::new();
        for (i, patterns) in on.iter().enumerate() {
            for pattern in patterns {
                self.clients[i].1.subscribe(pattern)?;
                all.insert(pattern.clone());
            }
        }
        let all: Vec<String> = all.into_iter().collect();
        log::info!(
            "{} listening on {}",
            local_of(&self.me),
            if all.is_empty() {
                "nothing".to_string()
            } else {
                format!("{all:?}")
            }
        );
        Ok(all)
    }

    /// Route one message: on the topic the agent listens to, a peer's document, kept by speech's `heard`, each graph
    /// answered with no sensor; otherwise to sensing, for every sensor of the agent's whose topic's filter matches `topic`, the
    /// observation `received` writes of `payload` at `at`. The sensor and the graph written, first sensor first, and
    /// none where the topic is nobody's of the agent's.
    pub fn handle(
        &mut self,
        topic: &str,
        payload: &[u8],
        at: DateTime,
    ) -> Result<Vec<(Option<String>, String)>, Error> {
        let me = Value::iri(self.me.as_str());
        if self
            .patterns(LISTENS_Q, &[("agent", me.clone())])?
            .iter()
            .any(|p| matches(p, topic))
        {
            return Ok(heard(&self.beliefs, &self.me, payload)?
                .into_iter()
                .map(|g| (None, g))
                .collect());
        }
        let chats: Vec<String> = self
            .rows_of(CHAT_TOPICS_Q, &[("agent", me.clone())])?
            .iter()
            .filter(|r| value(r, "pattern").is_some_and(|p| matches(&p, topic)))
            .filter_map(|r| iri(r, "topic"))
            .collect();
        if let Some(channel) = chats.first() {
            if let Some(prose) = self.prose_of(channel, payload, at) {
                self.prose.push(prose);
            }
            return Ok(Vec::new());
        }
        let mut mine: Vec<String> = Vec::new();
        for (sensor, pattern) in self.topics()? {
            if matches(&pattern, topic) && !mine.contains(&sensor) {
                mine.push(sensor);
            }
        }
        if mine.is_empty() {
            log::debug!("{}: a message on {topic} is nobody's of mine", local_of(&self.me));
            return Ok(Vec::new());
        }
        let mut written = Vec::new();
        for sensor in mine {
            for graph in received(&self.beliefs, &self.me, &sensor, payload, at)? {
                written.push((Some(sensor.clone()), graph));
            }
        }
        Ok(written)
    }

    /// Tell the board of every sensor of this member's whose reading has fallen due to sense now, and say when to ask
    /// again: a nudge later where a board was told, since it may not have heard, and otherwise when a reading next falls
    /// due. Which readings have fallen due, and when one next will, is sensing's to say (`cadence`).
    pub fn nudge_until(&mut self, now: DateTime) -> Result<Option<DateTime>, Error> {
        let told = self.nudge(now)?;
        let next = next_lapse(&self.beliefs, now)?;
        if told.is_empty() {
            return Ok(next);
        }
        let again = now
            .checked_add_day_time_duration(orexis::clock::seconds(NUDGE_S))
            .unwrap_or(now);
        Ok(Some(next.map_or(again, |n| if n < again { n } else { again })))
    }

    /// Tell the board of every sensor of this member's whose reading has fallen due to sense now; the sensors whose
    /// board was told. Which readings have fallen due is sensing's to say (`cadence::lapsed`).
    pub fn nudge(&mut self, now: DateTime) -> Result<Vec<String>, Error> {
        let mine: BTreeSet<String> = self.topics()?.into_iter().map(|(s, _)| s).collect();
        let mut asked: Vec<String> = Vec::new();
        for (sensor, _) in lapsed(&self.beliefs, now)? {
            if mine.contains(&sensor) && !asked.contains(&sensor) {
                asked.push(sensor);
            }
        }
        let mut told = Vec::new();
        for sensor in asked {
            if self.sense_now(&sensor)? {
                told.push(sensor);
            }
        }
        Ok(told)
    }

    /// Whether this member reaches `device`.
    pub fn reaches(&self, device: &str) -> Result<bool, Error> {
        let common = self.common()?;
        self.beliefs
            .ask(&bind(REACHES_Q, &[("device", Value::iri(device))])?, &strs(&common))
    }

    /// A step's command: sent where this member reaches the actuator.
    pub fn command(&mut self, actuator: &str, payload: &Json) -> Result<(), Error> {
        if self.reaches(actuator)? {
            self.actuate(actuator, payload)?;
        }
        Ok(())
    }

    /// Standing policy, where the device accepts instruction: retained, so a board deep asleep finds it on waking.
    pub fn set_cadence(&mut self, sensor: &str, sleep_s: i64) -> Result<bool, Error> {
        let Some(topic) = self.command_topic(sensor)? else {
            return Ok(false);
        };
        self.publish(sensor, &topic, &serde_json::json!({ "sleep_s": sleep_s }), true)
    }

    /// Ask for a reading now, best-effort.
    pub fn sense_now(&mut self, sensor: &str) -> Result<bool, Error> {
        match self.command_topic(sensor)? {
            Some(topic) => self.publish(sensor, &topic, &serde_json::json!({ "sense": true }), false),
            None => Ok(false),
        }
    }

    /// Publish a step's command on the topic the actuator listens to, or its board's; not retained, since a command is
    /// an act and a retained one would be taken again by a device that reconnects.
    pub fn actuate(&mut self, actuator: &str, payload: &Json) -> Result<bool, Error> {
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
        let common = self.common()?;
        if !self
            .beliefs
            .ask(&bind(AGENT_Q, &[("who", Value::iri(to))])?, &strs(&common))?
        {
            return Ok(false);
        }
        let names: Vec<String> = self
            .patterns(LISTENS_Q, &[("agent", Value::iri(to))])?
            .into_iter()
            .filter(|p| no_wildcard(p))
            .collect();
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

    /// The topic name the sensor's board takes commands on: a pattern with no wildcard. None, said in the log once per
    /// sensor, where the board listens nowhere or every pattern is a wildcard: said at every nudge, a minute's five
    /// silent sensors were five incidents a minute, each keeping the log's window in the journal.
    fn command_topic(&mut self, sensor: &str) -> Result<Option<String>, Error> {
        let patterns = self.patterns(COMMANDS_Q, &[("sensor", Value::iri(sensor))])?;
        let name = patterns.iter().find(|p| no_wildcard(p)).cloned();
        if name.is_none() && self.unreachable.insert(sensor.to_string()) {
            log::warn!(
                "{}: its board listens on {}, and none is a topic name to publish to",
                local_of(sensor),
                if patterns.is_empty() {
                    "no topic".to_string()
                } else {
                    format!("{patterns:?}")
                }
            );
        }
        Ok(name)
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

/// The sessions the environment names: a client per broker `MQTT_BROKERS` names — its IRI, then the url the agent
/// reaches it at — under the agent's credential, with its certificate where the url is `mqtts`. Refused without a
/// broker or a credential, since a guess puts a misconfigured agent on the real topics.
pub fn sessions(me: &str, env: &dyn Fn(&str) -> Option<String>) -> Result<Vec<Session>, Error> {
    let said: Vec<String> = env("MQTT_BROKERS")
        .unwrap_or_default()
        .split_whitespace()
        .map(String::from)
        .collect();
    if said.is_empty() || said.len() % 2 == 1 {
        return Err(Error::Evaluation(
            "no MQTT_BROKERS in the environment, each a broker's IRI and its url — this agent is told where its bus is, \
             never guesses"
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
    for pair in said.chunks(2) {
        let (broker, text) = (&pair[0], &pair[1]);
        let refused = || {
            Error::Evaluation(format!(
                "MQTT_BROKERS says {} is at '{text}', which is no mqtt:// or mqtts:// url",
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

/// A session over rumqttc: the mind publishes through its blocking client and the event loop is a task, handing every
/// message to the inbox.
pub struct Rumqtt {
    client: rumqttc::Client,
}

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
        //  THE CONNECTION'S OWN RUNTIME GOES, AND ITS EVENT LOOP IS POLLED AMONG THE PROCESS'S TASKS.
        let (client, connection) = rumqttc::Client::new(options, 64);
        let mut events = connection.eventloop;
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
            .subscribe(pattern, rumqttc::QoS::AtLeastOnce)
            .map_err(|e| Error::Evaluation(format!("subscribing to {pattern}: {e}")))
    }

    fn publish(&mut self, topic: &str, payload: &[u8], retain: bool) -> Result<(), Error> {
        self.client
            .publish(topic, rumqttc::QoS::AtLeastOnce, retain, payload.to_vec())
            .map_err(|e| Error::Evaluation(format!("publishing on {topic}: {e}")))
    }

    fn stop(&mut self) {
        let _ = self.client.disconnect();
    }
}

/// The agent's side of the bus, up from the environment: a rumqttc session per broker it names.
pub fn connect(beliefs: &Store, me: &str, env: &dyn Fn(&str) -> Option<String>) -> Result<Mqtt, Error> {
    let mut member = Mqtt::new(beliefs, me, Vec::new());
    for session in sessions(me, env)? {
        let (client, listening) = Rumqtt::connect(&session, member.inbox.clone())?;
        member.listening.push(listening);
        member.clients.push((Some(session.broker.clone()), Box::new(client)));
    }
    Ok(member)
}

impl orexis_speech::prose::Carrier for Mqtt {
    /// Prose out on the topic node `channel`, a chat's topic, by the one pattern naming it with no wildcard, as
    /// `{"from": the agent, "text": …}` so the agent knows its own when the broker hands it back; false where the
    /// channel is no topic of a chat this agent is in, or it is on no broker of this member's.
    fn say_to(&mut self, channel: &str, text: &str, _reply: Option<&str>) -> bool {
        let names: Vec<String> = match self.rows_of(CHAT_TOPICS_Q, &[("agent", Value::iri(self.me.as_str()))]) {
            Ok(rows) => rows
                .iter()
                .filter(|r| iri(r, "topic").as_deref() == Some(channel))
                .filter_map(|r| value(r, "pattern"))
                .filter(|p| no_wildcard(p))
                .collect(),
            Err(_) => return false,
        };
        let Some(name) = names.first() else { return false };
        let me = self.me.clone();
        let over = match self.over(&me) {
            Ok(over) => over,
            Err(_) => return false,
        };
        let Some(first) = over.first() else {
            return self.unshared(&me, "nothing is said on a chat's topic");
        };
        let payload = dumps(&serde_json::json!({"from": me, "text": text}));
        self.clients[*first].1.publish(name, payload.as_bytes(), false).is_ok()
    }

    fn writing_in(&mut self, _channel: &str) -> bool {
        false
    }
}

#[cfg(test)]
mod tests {
    //! The MQTT driver over a board on a bus and a stand-in client, held as `agent/transport/mqtt/tests/
    //! test_driver.py` holds it: what the agent subscribes to, whose a message is, where a command goes and as what,
    //! how a message becomes observations through sensing — and MQTT's own filter matching.

    use std::collections::BTreeMap;
    use std::path::{Path, PathBuf};

    use orexis::clock::seconds;
    use orexis::snapshots::{ME, now, stand_in, stand_in_with};

    use super::*;
    use std::sync::{Arc, Mutex};

    const TEST: &str = "http://example.org/test#";
    const OBSERVED: &str = "http://example.org/orexis/graph/observed/keeper/";
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

    fn plus(by: f64) -> DateTime {
        now().checked_add_day_time_duration(seconds(by)).unwrap()
    }

    fn results(store: &Store) -> Vec<(String, f64)> {
        store
            .rows(
                "SELECT ?s ?v WHERE { GRAPH ?g { ?o a sosa:Observation ; sosa:madeBySensor ?s ; sensing:rawResult ?v } } ORDER BY ?s",
                &[],
            )
            .unwrap()
            .iter()
            .map(|r| (local_of(&iri(r, "s").unwrap()), value(r, "v").unwrap().parse().unwrap()))
            .collect()
    }

    fn sent(topic: &str, payload: &str, retained: bool) -> (String, String, bool) {
        (topic.to_string(), payload.to_string(), retained)
    }

    #[test]
    fn the_driver_listens_where_the_agents_sensors_publish() {
        let store = stand_in(&world());
        let (mut driver, client) = bus(&store);
        assert_eq!(
            driver.open().unwrap(),
            ["sensors/board/reading"],
            "one board, one topic, two sensors"
        );
        assert_eq!(
            client.0.lock().unwrap().subscribed,
            ["sensors/board/reading"],
            "the lamp's is the neighbour's"
        );
    }

    #[test]
    fn a_command_goes_to_the_topic_the_board_listens_on_as_the_firmwares_document() {
        let store = stand_in(&world());
        let (mut driver, client) = bus(&store);
        assert!(driver.set_cadence(&t("thermo"), 60).unwrap());
        driver.sense_now(&t("hygro")).unwrap();
        assert_eq!(
            client.0.lock().unwrap().published,
            [
                sent("sensors/board/command", r#"{"sleep_s": 60}"#, true),
                sent("sensors/board/command", r#"{"sense": true}"#, false)
            ]
        );
    }

    #[test]
    fn a_board_is_asked_to_sense_where_its_readings_have_fallen_due() {
        let store = stand_in(&world());
        let (mut driver, client) = bus(&store);
        driver.handle("sensors/board/reading", BOARD_MESSAGE, now()).unwrap();
        driver.nudge(plus(60.0)).unwrap();
        assert!(client.0.lock().unwrap().published.is_empty());
        driver.nudge(plus(300.0)).unwrap();
        let published = client.0.lock().unwrap().published.clone();
        assert!(!published.is_empty());
        assert!(
            published
                .iter()
                .all(|p| *p == sent("sensors/board/command", r#"{"sense": true}"#, false))
        );
    }

    #[test]
    fn a_nudge_waits_for_the_next_reading_to_fall_due_and_asks_a_board_it_told_again_a_minute_on() {
        let store = stand_in(&world());
        let (mut driver, client) = bus(&store);
        assert_eq!(
            driver.nudge_until(now()).unwrap(),
            None,
            "nothing read, nothing falls due"
        );
        driver.handle("sensors/board/reading", BOARD_MESSAGE, now()).unwrap();
        let due = driver.nudge_until(plus(60.0)).unwrap().expect("a reading falls due");
        assert!(due > plus(60.0), "not yet");
        assert!(client.0.lock().unwrap().published.is_empty());
        let late = plus(300.0);
        assert!(due <= late);
        assert_eq!(
            driver.nudge_until(late).unwrap(),
            Some(
                late.checked_add_day_time_duration(orexis::clock::seconds(NUDGE_S))
                    .unwrap()
            ),
            "told to sense, and asked again a minute on"
        );
        assert!(!client.0.lock().unwrap().published.is_empty());
    }

    #[test]
    fn a_reading_followed_by_the_next_has_not_fallen_due() {
        let store = stand_in(&world());
        let (mut driver, client) = bus(&store);
        driver.handle("sensors/board/reading", BOARD_MESSAGE, now()).unwrap();
        driver
            .handle("sensors/board/reading", BOARD_MESSAGE, plus(180.0))
            .unwrap();
        driver.nudge(plus(300.0)).unwrap();
        assert!(client.0.lock().unwrap().published.is_empty());
    }

    #[test]
    fn a_sensor_whose_board_listens_nowhere_takes_no_command() {
        let store = stand_in(&world());
        let (mut driver, client) = bus(&store);
        assert!(!driver.set_cadence(&t("photometer"), 60).unwrap());
        driver.sense_now(&t("probe")).unwrap();
        assert!(client.0.lock().unwrap().published.is_empty());
    }

    #[test]
    fn one_message_on_the_boards_topic_is_two_observations() {
        let store = stand_in(&world());
        let (mut driver, _) = bus(&store);
        let written = driver.handle("sensors/board/reading", BOARD_MESSAGE, now()).unwrap();
        assert_eq!(
            written,
            [
                (Some(t("hygro")), format!("{OBSERVED}hygro_20260101T120000Z")),
                (Some(t("thermo")), format!("{OBSERVED}thermo_20260101T120000Z"))
            ]
        );
        assert_eq!(
            results(&store),
            [("hygro".to_string(), 0.61), ("thermo".to_string(), 21.5)]
        );
    }

    #[test]
    fn a_neighbours_message_on_the_same_broker_is_not_received() {
        let store = stand_in(&world());
        let (mut driver, _) = bus(&store);
        assert!(
            driver
                .handle("sensors/lamp/reading", br#"{"value": 300}"#, now())
                .unwrap()
                .is_empty()
        );
        assert!(
            driver
                .handle("sensors/nowhere", BOARD_MESSAGE, now())
                .unwrap()
                .is_empty()
        );
        assert!(results(&store).is_empty());
    }

    #[test]
    fn a_message_a_sensor_cannot_read_writes_nothing_for_it() {
        let store = stand_in(&world());
        let (mut driver, _) = bus(&store);
        let written = driver
            .handle("sensors/board/reading", br#"{"temperature": 21.5}"#, now())
            .unwrap();
        assert_eq!(
            written,
            [(Some(t("thermo")), format!("{OBSERVED}thermo_20260101T120000Z"))]
        );
    }

    fn env(pairs: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> + use<> {
        let map: BTreeMap<String, String> = pairs.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect();
        move |name| map.get(name).cloned()
    }

    #[test]
    fn the_environment_names_each_session_and_its_credential() {
        let broker = t("broker");
        let said = format!("{broker} mqtt://broker:1888");
        let by_password = env(&[
            ("MQTT_BROKERS", &said),
            ("MQTT_USERNAME", "keeper"),
            ("MQTT_PASSWORD", "s3cret"),
        ]);
        let found = sessions(ME, &by_password).unwrap();
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
        let tls = format!("{broker} mqtts://broker:8888");
        let by_certificate = env(&[
            ("MQTT_BROKERS", &tls),
            ("MQTT_USERNAME", "keeper"),
            ("MQTT_CA", "ca.pem"),
            ("MQTT_CERT", "keeper.pem"),
            ("MQTT_KEY", "keeper.key"),
        ]);
        let found = sessions(ME, &by_certificate).unwrap();
        assert_eq!(
            found[0].tls,
            Some(("ca.pem".into(), "keeper.pem".into(), "keeper.key".into()))
        );
        assert_eq!(found[0].port, 8888);
    }

    #[test]
    fn the_environment_is_refused_rather_than_a_broker_or_a_credential_guessed() {
        let broker = t("broker");
        let plain = format!("{broker} mqtt://broker:1888");
        let no_scheme = format!("{broker} broker:1888");
        let tls = format!("{broker} mqtts://broker:8888");
        for (pairs, refusal) in [
            (vec![("MQTT_USERNAME", "keeper")], "no MQTT_BROKERS"),
            (
                vec![("MQTT_BROKERS", broker.as_str()), ("MQTT_USERNAME", "keeper")],
                "no MQTT_BROKERS",
            ),
            (
                vec![("MQTT_BROKERS", no_scheme.as_str()), ("MQTT_USERNAME", "keeper")],
                "no mqtt:// or mqtts:// url",
            ),
            (
                vec![("MQTT_BROKERS", tls.as_str()), ("MQTT_USERNAME", "keeper")],
                "no MQTT_CA",
            ),
            (vec![("MQTT_BROKERS", plain.as_str())], "MQTT_USERNAME"),
        ] {
            let refused = sessions(ME, &env(&pairs)).unwrap_err().to_string();
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
        mqtt.open().unwrap();
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
        assert!(mqtt.open().unwrap().contains(&"agents/keeper/inbox".to_string()));
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
    fn a_document_on_the_agents_own_topic_is_heard_and_answered_with_no_sensor() {
        let more =
            format!("{PEERS}\nGRAPH :ontology {{ :NoteGraph rdfs:subClassOf orexis:BeliefGraph , orexis:Graph . }}");
        let store = stand_in_with(&world(), &more);
        let (mut mqtt, _) = bus(&store);
        let document =
            format!("<{TEST}note> {{ <{TEST}note> <{TEST}says> \"hello\" }}\n<{TEST}note> a <{TEST}NoteGraph> .");
        assert_eq!(
            mqtt.handle("agents/keeper/inbox", document.as_bytes(), now()).unwrap(),
            [(None, t("note"))]
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
    fn words_on_a_chats_topic_are_prose_and_nobodys_reading_and_prose_is_said_there_as_the_agents() {
        use orexis_speech::prose::Carrier;
        let store = chat();
        let (mut mqtt, client) = bus(&store);
        assert!(mqtt.open().unwrap().contains(&"chats/keeper_and_anna".to_string()));
        let before = store.len().unwrap();
        let anna = format!(r#"{{"from": "{}", "text": " hello "}}"#, t("anna"));
        assert!(
            mqtt.handle("chats/keeper_and_anna", anna.as_bytes(), now())
                .unwrap()
                .is_empty()
        );
        assert!(
            mqtt.handle("chats/keeper_and_anna", b"how is the fern?", now())
                .unwrap()
                .is_empty()
        );
        let mine = format!(r#"{{"from": "{ME}", "text": "mine"}}"#);
        assert!(
            mqtt.handle("chats/keeper_and_anna", mine.as_bytes(), now())
                .unwrap()
                .is_empty()
        );
        let heard: Vec<(String, Option<String>, String)> = mqtt
            .prose
            .iter()
            .map(|p| (p.channel.clone(), p.sender.clone(), p.text.clone()))
            .collect();
        assert_eq!(
            heard,
            [
                (t("anna_topic"), Some(t("anna")), "hello".to_string()),
                (t("anna_topic"), None, "how is the fern?".to_string())
            ]
        );
        assert_eq!(
            store.len().unwrap(),
            before,
            "no sensor's, so sensing is handed nothing"
        );
        assert!(mqtt.say_to(&t("anna_topic"), "the fern is dry", None));
        assert_eq!(
            client.0.lock().unwrap().published.last().unwrap(),
            &(
                "chats/keeper_and_anna".to_string(),
                format!(r#"{{"from": "{}", "text": "the fern is dry"}}"#, t("keeper")),
                false
            )
        );
        assert!(
            !mqtt.say_to(&t("board_readings"), "x", None),
            "a topic of no chat of the agent's is not said on"
        );
    }
}
