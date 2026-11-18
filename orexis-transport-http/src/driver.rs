//! THE HTTP DRIVER, as `agent/transport/http/driver.py` keeps it: the agent's side of the web.
//!
//! **WHAT THE WORLD SAYS AND WHAT FOLLOWS.** A sensor is this member's when it is the agent's and a `td:Thing` with a
//! `td:hasForm`; it is read at the form's `hctl:hasTarget`, a URI template whose `{name}`s are filled from the literals
//! said of the `schema:geo` of what the sensor is hosted by, by local name. A template with a variable nothing fills is
//! not fetched, and says so: a world whose location is kept in its `secrets/` and was not given it still boots.
//!
//! **A SENSOR IS A CHANNEL THIS MEMBER IS ASKED ON, AND WHAT THE BODY MEANS IS NOT ITS OWN.** It reaches a `td:Thing`
//! with a form as a channel it is sent on and answers (`Exchange::Requested`); a request is one fetch, awaited as a
//! Tokio task, one at a time per channel, and the body is left in the inbox the requester handed. Who asks, and how
//! often, is the row above's: sensing, on the sensor's cadence (the-transport-is-the-bottom-layer-and-the-row-above-owns-the-loop).

use std::collections::BTreeSet;
use std::future::Future;
use std::pin::Pin;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use regex::Regex;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{BELIEF, local_of};
use orexis::store::{Store, Within, iri, value};
use orexis_transport::{Exchange, Inbox, Member};

/// HOW LONG ONE FETCH MAY TAKE, in real seconds: a figure a role states.
pub const FETCHED_WITHIN_S: &str = "http://example.org/orexis/http#fetchedWithinS";

/// A fetch under way: the body, or why there is none.
pub type Fetched = Pin<Box<dyn Future<Output = Result<Vec<u8>, String>> + Send>>;
/// What fetches a URI's body.
pub type Client = Arc<dyn Fn(String) -> Fetched + Send + Sync>;

/// A client that answers each URI at once with what `answer` says of it: a test's web.
pub fn answering(answer: impl Fn(&str) -> Result<Vec<u8>, String> + Send + Sync + 'static) -> Client {
    Arc::new(move |url: String| {
        let answered = answer(&url);
        Box::pin(async move { answered })
    })
}

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

/// The web as a deployed agent reads it, over rustls, a fetch given up after `within_s` real seconds.
pub fn get(within_s: f64) -> Result<Client, Error> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs_f64(within_s))
        .user_agent("orexis-agent")
        .build()
        .map_err(|e| Error::Evaluation(format!("no web client: {e}")))?;
    Ok(Arc::new(move |url: String| {
        let client = client.clone();
        Box::pin(async move {
            let response = client
                .get(&url)
                .header(reqwest::header::ACCEPT, "application/json")
                .send()
                .await
                .and_then(reqwest::Response::error_for_status)
                .map_err(|e| e.to_string())?;
            Ok(response.bytes().await.map_err(|e| e.to_string())?.to_vec())
        })
    }))
}

/// One agent's side of the web, answered from the world in the Thing Description's words.
pub struct Http {
    beliefs: Store,
    pub me: String,
    pub client: Client,
    fetching: Arc<Mutex<BTreeSet<String>>>,
}

fn common(store: &Store) -> Result<Vec<String>, Error> {
    store.graphs_of(&[BELIEF], &Within::common())
}

fn strs(names: &[String]) -> Vec<&str> {
    names.iter().map(String::as_str).collect()
}

impl Http {
    /// The member over `client`.
    pub fn new(beliefs: &Store, me: &str, client: Client) -> Self {
        Http {
            beliefs: beliefs.clone(),
            me: me.to_string(),
            client,
            fetching: Arc::default(),
        }
    }

    /// The store the member reads the world off.
    pub fn beliefs(&self) -> &Store {
        &self.beliefs
    }

    /// Whether this member reaches `device`.
    pub fn reaches(&self, device: &str) -> Result<bool, Error> {
        let stated = common(&self.beliefs)?;
        self.beliefs.ask(
            &bind(
                "PREFIX td: <https://www.w3.org/2019/wot/td#> ASK { $device td:hasForm ?form }",
                &[("device", Value::iri(device))],
            )?,
            &strs(&stated),
        )
    }

    /// Fetch what `sensor` reads, as a task of its own, its body left in `reply` — unless it is being fetched already.
    pub fn fetch(&self, sensor: &str, reply: Inbox) -> Result<(), Error> {
        const TARGET_Q: &str = "PREFIX hctl: <https://www.w3.org/2019/wot/hypermedia#>
            PREFIX td: <https://www.w3.org/2019/wot/td#>
            SELECT ?target WHERE { $sensor td:hasForm ?form . ?form hctl:hasTarget ?target } ORDER BY ?target";
        const WHERE_Q: &str = "PREFIX schema: <https://schema.org/>
        PREFIX sosa: <http://www.w3.org/ns/sosa/>
        SELECT ?property ?value WHERE {
          $sensor sosa:isHostedBy ?host . ?host schema:geo ?geo . ?geo ?property ?value . FILTER(isLiteral(?value)) }";
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
        let (fetched, fetching, sensor) = ((self.client)(url.clone()), self.fetching.clone(), sensor.to_string());
        tokio::spawn(async move {
            match fetched.await {
                Ok(body) => reply.deliver(&sensor, &body, None),
                Err(e) => log::warn!(
                    "{}: {} would not answer: {e}",
                    local_of(&sensor),
                    url.split('?').next().unwrap_or(&url)
                ),
            }
            fetching.lock().unwrap().remove(&sensor);
        });
        Ok(())
    }
}

impl Member for Http {
    /// A thing with a form is a channel this member is asked on.
    fn reaches(&self, channel: &str, exchange: Exchange) -> Result<bool, Error> {
        Ok(exchange == Exchange::Requested && Http::reaches(self, channel)?)
    }

    /// The web is asked, never listened to.
    fn listen(&self, channel: &str, _inbox: Inbox) -> Result<(), Error> {
        Err(Error::Evaluation(format!(
            "{channel} is read over HTTP by asking, and nothing listens to it"
        )))
    }

    /// A request: what the thing reads, fetched once; the payload is nothing a fetch sends.
    fn send(&self, channel: &str, _payload: &[u8], reply: Option<Inbox>) -> Result<(), Error> {
        match reply {
            Some(reply) => self.fetch(channel, reply),
            None => Ok(()),
        }
    }
}

#[cfg(test)]
mod tests {
    //! The driver over a balcony and its weather service, held to `agent/transport/http/tests/test_driver.py`: what it
    //! reaches, and what one request fetches.

    use std::path::Path;

    use super::*;
    use orexis::snapshots::stand_in;

    const TEST: &str = "http://example.org/test#";
    const BODY: &[u8] =
        br#"{"hourly": {"time": ["2026-01-01T13:00", "2026-01-01T14:00"], "precipitation": [0.4, 1.5]}}"#;

    fn balcony() -> Store {
        stand_in(&Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/worlds/a_forecast_for_a_balcony.trig"))
    }

    fn member(store: &Store) -> (Http, Arc<Mutex<Vec<String>>>) {
        let asked: Arc<Mutex<Vec<String>>> = Arc::default();
        let kept = asked.clone();
        let member = Http::new(
            store,
            &format!("{TEST}keeper"),
            answering(move |url| {
                kept.lock().unwrap().push(url.to_string());
                Ok(BODY.to_vec())
            }),
        );
        (member, asked)
    }

    /// Every task spawned so far run as far as it goes.
    async fn settled() {
        for _ in 0..8 {
            tokio::task::yield_now().await;
        }
    }

    #[test]
    fn a_thing_with_a_form_is_a_channel_the_member_is_asked_on() {
        let store = balcony();
        let (member, _) = member(&store);
        assert!(Member::reaches(&member, &format!("{TEST}weather"), Exchange::Requested).unwrap());
        assert!(
            !Member::reaches(&member, &format!("{TEST}weather"), Exchange::Listened).unwrap(),
            "asked, never listened to"
        );
        assert!(!Member::reaches(&member, &format!("{TEST}probe"), Exchange::Requested).unwrap());
        assert!(member.listen(&format!("{TEST}weather"), Inbox::default()).is_err());
    }

    #[tokio::test]
    async fn a_request_fetches_the_target_filled_from_the_place_and_leaves_the_body_where_it_was_asked() {
        let store = balcony();
        let (member, asked) = member(&store);
        let reply = Inbox::default();
        member
            .send(&format!("{TEST}weather"), b"", Some(reply.clone()))
            .unwrap();
        settled().await;
        assert_eq!(
            *asked.lock().unwrap(),
            ["https://forecast.example/v1?latitude=52.52&longitude=13.4&hourly=precipitation"]
        );
        let answered = reply.take();
        assert_eq!(answered.len(), 1);
        assert_eq!(answered[0].topic, format!("{TEST}weather"));
        assert_eq!(answered[0].payload, BODY);
    }

    #[tokio::test]
    async fn a_sensor_being_fetched_is_not_fetched_again_until_it_answers() {
        let store = balcony();
        let asked: Arc<Mutex<usize>> = Arc::default();
        let open = Arc::new(tokio::sync::Notify::new());
        let (counted, waited) = (asked.clone(), open.clone());
        let mut member = Http::new(&store, &format!("{TEST}keeper"), answering(|_| Ok(Vec::new())));
        member.client = Arc::new(move |_url: String| {
            *counted.lock().unwrap() += 1;
            let waited = waited.clone();
            Box::pin(async move {
                waited.notified().await;
                Ok(BODY.to_vec())
            })
        });
        let reply = Inbox::default();
        let weather = format!("{TEST}weather");
        member.send(&weather, b"", Some(reply.clone())).unwrap();
        member.send(&weather, b"", Some(reply.clone())).unwrap();
        settled().await;
        assert_eq!(*asked.lock().unwrap(), 1);
        open.notify_waiters();
        settled().await;
        assert_eq!(reply.take().len(), 1);
        member.send(&weather, b"", Some(reply.clone())).unwrap();
        assert_eq!(*asked.lock().unwrap(), 2);
    }

    #[tokio::test]
    async fn with_no_location_nothing_is_fetched() {
        let store = balcony();
        store
            .update(
                "PREFIX schema: <https://schema.org/>
                PREFIX : <http://example.org/test#>
                DELETE WHERE { GRAPH :world { :balcony schema:geo ?g } }",
            )
            .unwrap();
        let (member, asked) = member(&store);
        member
            .send(&format!("{TEST}weather"), b"", Some(Inbox::default()))
            .unwrap();
        settled().await;
        assert!(asked.lock().unwrap().is_empty());
    }

    #[tokio::test]
    async fn a_service_that_does_not_answer_leaves_nothing() {
        let store = balcony();
        let (mut member, _) = member(&store);
        member.client = answering(|_| Err("connection refused".into()));
        let reply = Inbox::default();
        member
            .send(&format!("{TEST}weather"), b"", Some(reply.clone()))
            .unwrap();
        settled().await;
        assert!(reply.take().is_empty());
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
