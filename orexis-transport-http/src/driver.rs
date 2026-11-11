//! THE HTTP DRIVER, as `agent/transport/http/driver.py` keeps it: the agent's side of the web.
//!
//! **WHAT THE WORLD SAYS AND WHAT FOLLOWS.** A sensor is this member's when it is the agent's and a `td:Thing` with a
//! `td:hasForm`; it is read at the form's `hctl:hasTarget`, a URI template whose `{name}`s are filled from the literals
//! said of the `schema:geo` of what the sensor is hosted by, by local name. A template with a variable nothing fills is
//! not fetched, and says so: a world whose location is kept in its `secrets/` and was not given it still boots.
//!
//! **A RESPONSE BECOMES OBSERVATIONS THROUGH SENSING, AND THE MEMBER KNOWS NO CODEC.** `handle` hands the body to
//! sensing's `received`. A fetch runs on a thread of its own, one at a time per sensor, and the body waits in the
//! inbox for the one executing thread.

use std::collections::BTreeSet;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use oxsdatatypes::DateTime;
use regex::Regex;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{BELIEF, local_of};
use orexis::store::{Store, Within, iri, value};
use orexis::transport::Inbox;
use orexis_sensing::cadence::sensors as observed;
use orexis_sensing::received::received;

/// HOW LONG ONE FETCH MAY TAKE, in real seconds.
pub const TIMEOUT_S: u64 = 30;

const FORM_Q: &str = "ASK { $sensor td:hasForm ?form }";
const TARGET_Q: &str =
    "SELECT ?target WHERE { $sensor td:hasForm ?form . ?form hctl:hasTarget ?target } ORDER BY ?target";
const WHERE_Q: &str = "
SELECT ?property ?value WHERE {
  $sensor sosa:isHostedBy ?host . ?host schema:geo ?geo . ?geo ?property ?value . FILTER(isLiteral(?value)) }";

/// What fetches a URI's body, or says why not.
pub type Client = Arc<dyn Fn(&str) -> Result<Vec<u8>, String> + Send + Sync>;
/// What runs a fetch: on a thread of its own, or at once in a test.
pub type Spawn = Box<dyn Fn(Box<dyn FnOnce() + Send>) + Send + Sync>;

/// The URI a template names with its simple `{name}` variables filled from `values`, each percent-encoded; None where
/// one names a value that is not there.
pub fn fill(template: &str, values: &[(String, String)]) -> Option<String> {
    let variable = Regex::new(r"\{([A-Za-z_][A-Za-z0-9_]*)\}").expect("a pattern");
    let found = |name: &str| values.iter().find(|(n, _)| n == name).map(|(_, v)| v.clone());
    if variable.captures_iter(template).any(|c| found(&c[1]).is_none()) {
        return None;
    }
    Some(
        variable
            .replace_all(template, |c: &regex::Captures<'_>| {
                quote(&found(&c[1]).unwrap_or_default())
            })
            .into_owned(),
    )
}

/// `text` percent-encoded but for what a URI leaves as it is, as Python's `quote(text, safe="")` encodes it.
fn quote(text: &str) -> String {
    text.bytes()
        .map(|b| match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'_' | b'.' | b'-' | b'~' => (b as char).to_string(),
            _ => format!("%{b:02X}"),
        })
        .collect()
}

/// The web as a deployed agent reads it.
pub fn get() -> Client {
    let agent = ureq::AgentBuilder::new()
        .timeout(Duration::from_secs(TIMEOUT_S))
        .build();
    Arc::new(move |url| {
        let response = agent
            .get(url)
            .set("Accept", "application/json")
            .set("User-Agent", "orexis-agent")
            .call()
            .map_err(|e| e.to_string())?;
        let mut body = Vec::new();
        std::io::Read::read_to_end(&mut response.into_reader(), &mut body).map_err(|e| e.to_string())?;
        Ok(body)
    })
}

/// One agent's side of the web, answered from the world in the Thing Description's words.
pub struct Http {
    beliefs: Store,
    pub me: String,
    pub inbox: Inbox,
    pub client: Client,
    pub spawn: Spawn,
    fetching: Arc<Mutex<BTreeSet<String>>>,
}

fn common(store: &Store) -> Result<Vec<String>, Error> {
    store.graphs_of(&[BELIEF], &Within::common())
}

fn strs(names: &[String]) -> Vec<&str> {
    names.iter().map(String::as_str).collect()
}

impl Http {
    /// The member over `client`, each fetch on a thread of its own.
    pub fn new(beliefs: &Store, me: &str, client: Client) -> Self {
        Http {
            beliefs: beliefs.clone(),
            me: me.to_string(),
            inbox: Inbox::default(),
            client,
            spawn: Box::new(|work| {
                std::thread::spawn(work);
            }),
            fetching: Arc::default(),
        }
    }

    /// The store the member reads the world off.
    pub fn beliefs(&self) -> &Store {
        &self.beliefs
    }

    /// The sensors of the agent's this member reads.
    pub fn open(&self) -> Result<Vec<String>, Error> {
        let stated = common(&self.beliefs)?;
        let mut out = Vec::new();
        for sensor in observed(&self.beliefs)? {
            if self.beliefs.ask(
                &bind(FORM_Q, &[("sensor", Value::iri(sensor.as_str()))])?,
                &strs(&stated),
            )? {
                out.push(sensor);
            }
        }
        log::info!(
            "{} reads {} over HTTP",
            local_of(&self.me),
            if out.is_empty() {
                "nothing".to_string()
            } else {
                out.iter().map(|s| local_of(s)).collect::<Vec<_>>().join(", ")
            }
        );
        Ok(out)
    }

    /// Whether this member reaches `device`.
    pub fn reaches(&self, device: &str) -> Result<bool, Error> {
        let stated = common(&self.beliefs)?;
        self.beliefs.ask(
            &bind("ASK { $device td:hasForm ?form }", &[("device", Value::iri(device))])?,
            &strs(&stated),
        )
    }

    /// Fetch what `sensor` reads, on a thread of its own, unless it is being fetched already.
    pub fn sense_now(&self, sensor: &str) -> Result<(), Error> {
        if self.fetching.lock().unwrap().contains(sensor) {
            return Ok(());
        }
        let stated = common(&self.beliefs)?;
        let targets: Vec<String> = self
            .beliefs
            .rows(&bind(TARGET_Q, &[("sensor", Value::iri(sensor))])?, &strs(&stated))?
            .iter()
            .filter_map(|r| value(r, "target"))
            .collect();
        let values: Vec<(String, String)> = self
            .beliefs
            .rows(&bind(WHERE_Q, &[("sensor", Value::iri(sensor))])?, &strs(&stated))?
            .iter()
            .filter_map(|r| Some((local_of(&iri(r, "property")?), value(r, "value")?)))
            .collect();
        let Some(url) = targets.first().and_then(|t| fill(t, &values)) else {
            log::warn!(
                "{}: {} names what nothing here says — is the place's location in the world's secrets/?",
                local_of(sensor),
                targets.first().map_or("no target", String::as_str)
            );
            return Ok(());
        };
        self.fetching.lock().unwrap().insert(sensor.to_string());
        let (client, inbox, fetching, sensor) = (
            self.client.clone(),
            self.inbox.clone(),
            self.fetching.clone(),
            sensor.to_string(),
        );
        (self.spawn)(Box::new(move || {
            match client(&url) {
                Ok(body) => inbox.deliver(&sensor, &body, None),
                Err(e) => log::warn!(
                    "{}: {} would not answer: {e}",
                    local_of(&sensor),
                    url.split('?').next().unwrap_or(&url)
                ),
            }
            fetching.lock().unwrap().remove(&sensor);
        }));
        Ok(())
    }

    /// What `channel`, a sensor of this member's, read: handed to sensing's `received`, each graph written answered
    /// with the sensor.
    pub fn handle(&self, channel: &str, payload: &[u8], at: DateTime) -> Result<Vec<(String, String)>, Error> {
        Ok(received(&self.beliefs, &self.me, channel, payload, at)?
            .into_iter()
            .map(|graph| (channel.to_string(), graph))
            .collect())
    }
}

#[cfg(test)]
mod tests {
    //! The driver over a balcony and its weather service, held to `agent/transport/http/tests/test_driver.py`.

    use std::path::Path;

    use super::*;
    use orexis::snapshots::{now, stand_in};

    const TEST: &str = "http://example.org/test#";
    const BODY: &[u8] =
        br#"{"hourly": {"time": ["2026-01-01T13:00", "2026-01-01T14:00"], "precipitation": [0.4, 1.5]}}"#;

    fn balcony() -> Store {
        stand_in(&Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/worlds/a_forecast_for_a_balcony.trig"))
    }

    fn member(store: &Store) -> (Http, Arc<Mutex<Vec<String>>>) {
        let asked: Arc<Mutex<Vec<String>>> = Arc::default();
        let kept = asked.clone();
        let mut member = Http::new(
            store,
            &format!("{TEST}keeper"),
            Arc::new(move |url| {
                kept.lock().unwrap().push(url.to_string());
                Ok(BODY.to_vec())
            }),
        );
        member.spawn = Box::new(|work| work());
        (member, asked)
    }

    #[test]
    fn the_members_sensors_are_the_agents_things_with_a_form() {
        let store = balcony();
        let (member, _) = member(&store);
        assert_eq!(member.open().unwrap(), [format!("{TEST}weather")]);
        assert!(member.reaches(&format!("{TEST}weather")).unwrap());
        assert!(!member.reaches(&format!("{TEST}probe")).unwrap());
    }

    #[test]
    fn a_nudge_fetches_the_target_filled_from_the_place_and_the_body_becomes_forecast() {
        let store = balcony();
        let (member, asked) = member(&store);
        member.sense_now(&format!("{TEST}weather")).unwrap();
        assert_eq!(
            *asked.lock().unwrap(),
            ["https://forecast.example/v1?latitude=52.52&longitude=13.4&hourly=precipitation"]
        );
        let queued = member.inbox.take();
        assert_eq!(queued.len(), 1);
        let written = member.handle(&queued[0].topic, &queued[0].payload, now()).unwrap();
        assert_eq!(written.len(), 2, "one graph per hour still ahead: {written:?}");
    }

    #[test]
    fn a_sensor_being_fetched_is_not_fetched_again_until_it_answers() {
        let store = balcony();
        let (mut member, asked) = member(&store);
        type Held = Arc<Mutex<Vec<Box<dyn FnOnce() + Send>>>>;
        let held: Held = Arc::default();
        let into = held.clone();
        member.spawn = Box::new(move |work| into.lock().unwrap().push(work));
        member.sense_now(&format!("{TEST}weather")).unwrap();
        member.sense_now(&format!("{TEST}weather")).unwrap();
        assert_eq!(held.lock().unwrap().len(), 1);
        let first = held.lock().unwrap().pop().unwrap();
        first();
        member.spawn = Box::new(|work| work());
        member.sense_now(&format!("{TEST}weather")).unwrap();
        assert_eq!(asked.lock().unwrap().len(), 2);
    }

    #[test]
    fn with_no_location_nothing_is_fetched() {
        let store = balcony();
        store
            .update("PREFIX schema: <https://schema.org/> PREFIX : <http://example.org/test#> DELETE WHERE { GRAPH :world { :balcony schema:geo ?g } }")
            .unwrap();
        let (member, asked) = member(&store);
        member.sense_now(&format!("{TEST}weather")).unwrap();
        assert!(asked.lock().unwrap().is_empty());
    }

    #[test]
    fn a_service_that_does_not_answer_delivers_nothing() {
        let store = balcony();
        let (mut member, _) = member(&store);
        member.client = Arc::new(|_| Err("connection refused".into()));
        member.sense_now(&format!("{TEST}weather")).unwrap();
        assert!(member.inbox.take().is_empty());
    }

    #[test]
    fn a_template_is_filled_by_name_and_refused_where_a_name_is_missing() {
        let values = [
            ("a".to_string(), "1".to_string()),
            ("b".to_string(), "two words".to_string()),
        ];
        assert_eq!(
            fill("https://x/?a={a}&b={b}", &values).as_deref(),
            Some("https://x/?a=1&b=two%20words")
        );
        assert_eq!(fill("https://x/?a={a}", &[]), None);
    }
}
