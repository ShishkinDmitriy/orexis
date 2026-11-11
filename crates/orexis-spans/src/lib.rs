//! SPANS: what the agent did, as a tracer draws it (packages-meet-by-events-policies-and-activities, #1119). Every
//! activity's `prov:Start` and `prov:End` the watch hears is a span; an activity begun inside another is its child, by
//! the activities open when it began; every other event said while one is open is an event of the innermost; and each
//! runtime pass is a trace, its root the pass itself, ended where the runtime says the pass.
//!
//! OTLP'S JSON OVER HTTP, written here rather than by the OpenTelemetry SDK: a pass is one POST of a documented shape
//! to `$OTLP_ENDPOINT/v1/traces`, and the SDK would bring a tree of crates to every agent's image for it. The POST is
//! made on a thread of its own, so a tracer slow or away never holds the mind; one that refuses is said in the log once
//! until it answers again. A start's triggers are entities, so they are the span's attributes, not its links: a link
//! wants the span that generated the entity, which no event says yet.

use std::sync::{Arc, Mutex, mpsc};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use oxigraph::model::NamedNode;
use serde_json::{Value, json};

use orexis::activity::{Ended, Started};
use orexis::events::{Event, Watch, as_of, mint};
use orexis::runtime::Passed;

/// Where the tracer is, told as environment: OTLP's HTTP endpoint, `/v1/traces` beneath it.
pub const ENDPOINT: &str = "OTLP_ENDPOINT";

/// How a pass's spans reach the tracer: the body of one POST.
pub type Send = Box<dyn Fn(String) + std::marker::Send + Sync>;

/// An activity begun and not ended.
struct Open {
    activity: NamedNode,
    span: String,
    name: String,
    parent: Option<String>,
    start: u128,
    attributes: Vec<Value>,
    events: Vec<Value>,
}

/// The spans of the pass in progress.
struct Tracer {
    agent: String,
    open: Vec<Open>,
    done: Vec<Value>,
    send: Send,
}

fn now_ns() -> u128 {
    SystemTime::now().duration_since(UNIX_EPOCH).map_or(0, |d| d.as_nanos())
}

/// The hex of a UUID's URN, its last `n` digits.
fn hex(node: &NamedNode, n: usize) -> String {
    let digits: String = node.as_str().chars().filter(|c| c.is_ascii_hexdigit()).collect();
    digits[digits.len().saturating_sub(n)..].to_string()
}

/// The local name of an IRI: what follows its last `#` or `/`.
fn local(iri: &str) -> &str {
    iri.rsplit(['#', '/']).next().unwrap_or(iri)
}

fn text(key: &str, value: &str) -> Value {
    json!({"key": key, "value": {"stringValue": value}})
}

impl Tracer {
    fn heard(&mut self, event: &dyn Event) {
        if let Some(started) = as_of::<Started>(event) {
            let mut attributes = vec![
                text("orexis.activity", started.activity.as_str()),
                text("orexis.kind", started.kind),
                text("orexis.at", &started.at.to_string()),
            ];
            if !started.triggers.is_empty() {
                let triggers: Vec<&str> = started.triggers.iter().map(NamedNode::as_str).collect();
                attributes.push(text("prov.entity", &triggers.join(" ")));
            }
            self.open.push(Open {
                activity: started.activity.clone(),
                span: hex(&started.activity, 16),
                name: local(started.kind).to_string(),
                parent: self.open.last().map(|o| o.span.clone()),
                start: now_ns(),
                attributes,
                events: Vec::new(),
            });
        } else if let Some(ended) = as_of::<Ended>(event) {
            if let Some(i) = self.open.iter().rposition(|o| o.activity == ended.activity) {
                let open = self.open.remove(i);
                self.done.push(json!({
                    "spanId": open.span,
                    "parentSpanId": open.parent.unwrap_or_default(),
                    "name": open.name,
                    "kind": 1,
                    "startTimeUnixNano": open.start.to_string(),
                    "endTimeUnixNano": now_ns().to_string(),
                    "attributes": open.attributes,
                    "events": open.events,
                }));
            }
        } else if let Some(passed) = as_of::<Passed>(event) {
            self.pass(passed);
        } else if let Some(open) = self.open.last_mut()
            && let Some(name) = event.kind().map(local).or_else(|| event.metric())
        {
            open.events
                .push(json!({"timeUnixNano": now_ns().to_string(), "name": name}));
        }
    }

    /// The pass is said: its spans are one trace beneath it, sent.
    fn pass(&mut self, passed: &Passed) {
        if self.done.is_empty() {
            return;
        }
        let end = now_ns();
        let start = end.saturating_sub((passed.duration_s * 1e9) as u128);
        let trace = hex(&mint(), 32);
        let root = hex(&mint(), 16);
        let mut spans: Vec<Value> = std::mem::take(&mut self.done);
        for span in &mut spans {
            span["traceId"] = json!(trace);
            if span["parentSpanId"] == json!("") {
                span["parentSpanId"] = json!(root);
            }
        }
        spans.push(json!({
            "traceId": trace,
            "spanId": root,
            "name": "pass",
            "kind": 1,
            "startTimeUnixNano": start.to_string(),
            "endTimeUnixNano": end.to_string(),
            "attributes": [text("orexis.agent", &self.agent)],
        }));
        let body = json!({"resourceSpans": [{
            "resource": {"attributes": [text("service.name", &self.agent)]},
            "scopeSpans": [{"scope": {"name": "orexis"}, "spans": spans}],
        }]});
        (self.send)(body.to_string());
    }
}

/// Trace every activity `watch` hears said, for the agent `agent`, each pass's spans handed to `send`.
pub fn connect(watch: &Watch, agent: &str, send: Send) {
    let tracer = Arc::new(Mutex::new(Tracer {
        agent: agent.to_string(),
        open: Vec::new(),
        done: Vec::new(),
        send,
    }));
    watch.connect(move |event, _| tracer.lock().unwrap().heard(event));
}

/// What the environment says of the tracer: its endpoint, or None where it names none.
pub fn from_environment(env: &dyn Fn(&str) -> Option<String>) -> Option<String> {
    env(ENDPOINT)
        .map(|e| e.trim_end_matches('/').to_string())
        .filter(|e| !e.is_empty())
}

/// POST each body to `endpoint`'s traces, on a thread of its own.
pub fn post(endpoint: &str) -> Send {
    let url = format!("{endpoint}/v1/traces");
    let (tx, rx) = mpsc::channel::<String>();
    std::thread::Builder::new()
        .name("orexis-spans".into())
        .spawn(move || {
            let agent = ureq::AgentBuilder::new().timeout(Duration::from_secs(2)).build();
            let mut refused = false;
            for body in rx {
                match agent
                    .post(&url)
                    .set("Content-Type", "application/json")
                    .send_string(&body)
                {
                    Ok(_) => refused = false,
                    Err(e) if !refused => {
                        log::warn!(
                            "the tracer at {url} refused a pass's spans, and is told none until it answers: {e}"
                        );
                        refused = true;
                    }
                    Err(_) => {}
                }
            }
        })
        .expect("a thread for the spans");
    Box::new(move |body| {
        let _ = tx.send(body);
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use orexis::activity::Activity;

    const PLANNING: &str = "http://example.org/orexis/planning#Planning";
    const SEARCHING: &str = "http://example.org/test#Searching";
    const TRIGGER: &str = "http://example.org/test#belief";

    fn at() -> oxsdatatypes::DateTime {
        "2026-11-10T12:00:00Z".parse().unwrap()
    }

    fn started(a: &Activity, triggers: &[&str]) -> Started {
        Started {
            activity: a.node.clone(),
            kind: a.kind,
            triggers: triggers.iter().map(|t| NamedNode::new_unchecked(*t)).collect(),
            at: at(),
        }
    }

    fn ended(a: &Activity) -> Ended {
        Ended {
            activity: a.node.clone(),
            kind: a.kind,
            at: at(),
            duration_s: 0.0,
        }
    }

    #[test]
    fn a_pass_is_one_trace_and_an_activity_begun_inside_another_is_its_child() {
        let watch = Watch::default();
        let sent: Arc<Mutex<Vec<String>>> = Arc::default();
        let kept = sent.clone();
        connect(&watch, "fern", Box::new(move |b| kept.lock().unwrap().push(b)));
        let (planning, searching) = (Activity::begin(PLANNING), Activity::begin(SEARCHING));
        watch.emit(&started(&planning, &[TRIGGER]));
        watch.emit(&started(&searching, &[]));
        watch.emit(&ended(&searching));
        watch.emit(&ended(&planning));
        watch.emit(&Passed {
            duration_s: 0.5,
            laps: Vec::new(),
            quads: None,
            uptime_s: 1.0,
        });
        let sent = sent.lock().unwrap();
        assert_eq!(sent.len(), 1, "one POST for the pass");
        let body: Value = serde_json::from_str(&sent[0]).unwrap();
        let spans = body["resourceSpans"][0]["scopeSpans"][0]["spans"].as_array().unwrap();
        let by = |name: &str| spans.iter().find(|s| s["name"] == name).unwrap();
        let (pass, plan, search) = (by("pass"), by("Planning"), by("Searching"));
        assert_eq!(spans.len(), 3);
        assert!(spans.iter().all(|s| s["traceId"] == pass["traceId"]), "one trace");
        assert_eq!(plan["parentSpanId"], pass["spanId"]);
        assert_eq!(search["parentSpanId"], plan["spanId"]);
        assert_eq!(pass["traceId"].as_str().unwrap().len(), 32);
        assert_eq!(plan["spanId"].as_str().unwrap().len(), 16);
        assert!(
            plan["attributes"]
                .as_array()
                .unwrap()
                .iter()
                .any(|a| a["key"] == "prov.entity")
        );
    }

    #[test]
    fn a_pass_that_began_no_activity_sends_nothing() {
        let watch = Watch::default();
        let sent: Arc<Mutex<Vec<String>>> = Arc::default();
        let kept = sent.clone();
        connect(&watch, "fern", Box::new(move |b| kept.lock().unwrap().push(b)));
        watch.emit(&Passed {
            duration_s: 0.1,
            laps: Vec::new(),
            quads: None,
            uptime_s: 1.0,
        });
        assert!(sent.lock().unwrap().is_empty());
    }

    #[test]
    fn the_endpoint_is_the_environments_and_none_where_it_names_none() {
        let env = |k: &str| (k == ENDPOINT).then(|| "http://127.0.0.1:4318/".to_string());
        assert_eq!(from_environment(&env).as_deref(), Some("http://127.0.0.1:4318"));
        assert_eq!(from_environment(&|_| None), None);
    }
}
