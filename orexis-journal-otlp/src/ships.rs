//! WHAT IS SHIPPED AND WHERE: the journal handed on, the tracer's endpoint and how often; each batch of spans read off
//! the journal, posted, and marked once the tracer accepted it.

use std::collections::{BTreeMap, BTreeSet};
use std::sync::Arc;
use std::time::Duration;

use oxigraph::model::{Literal, NamedNode};
use serde_json::{Value, json};

use orexis::rdf::triple;
use orexis_journal::journal::{ACTIVITY, Journal};

/// An activity shipped says to which cold store, so two may each have their own.
pub const SHIPPED_TO: &str = "http://example.org/orexis#shippedTo";

/// How a batch of spans reaches the tracer: the body of one POST, and whether it was accepted.
pub type Send = Arc<dyn Fn(String) -> Sending + std::marker::Send + Sync>;
/// A body under way to the tracer: whether it was accepted.
pub type Sending = std::pin::Pin<Box<dyn std::future::Future<Output = bool> + std::marker::Send>>;

/// What is shipped and where: made by this package from the journal handed on and the tracer the world names, or
/// provided by a test that ships to an endpoint of its own.
pub struct Ships {
    pub journal: Arc<Journal>,
    pub endpoint: String,
    pub every_s: f64,
}

fn rows(journal: &Journal, text: &str) -> Vec<BTreeMap<String, String>> {
    let Ok((_, body)) = orexis_journal::journal::answer(&journal.store, text) else {
        return Vec::new();
    };
    let Ok(value) = serde_json::from_slice::<Value>(&body) else {
        return Vec::new();
    };
    value["results"]["bindings"]
        .as_array()
        .map(|bindings| {
            bindings
                .iter()
                .map(|b| {
                    b.as_object()
                        .map(|o| {
                            o.iter()
                                .filter_map(|(k, v)| Some((k.clone(), v["value"].as_str()?.to_string())))
                                .collect()
                        })
                        .unwrap_or_default()
                })
                .collect()
        })
        .unwrap_or_default()
}

/// The hex of a UUID's URN, its last `n` digits.
fn hex(node: &str, n: usize) -> String {
    let digits: String = node.chars().filter(|c| c.is_ascii_hexdigit()).collect();
    format!("{:0>n$}", &digits[digits.len().saturating_sub(n)..])
}

/// The local name of an IRI: what follows its last `#` or `/`.
fn local(iri: &str) -> &str {
    iri.rsplit(['#', '/']).next().unwrap_or(iri)
}

/// What a span or a link says started the activity: the class of each trigger.
pub const TRIGGER: &str = "orexis.trigger";
/// The name of an event, on its mark and on the link of what it caused.
pub const ENTITY: &str = "prov.entity";
/// The link from a turn's activity to the activity that lasts it is part of.
pub const PART_OF: &str = "orexis.partOf";

fn text(key: &str, value: &str) -> Value {
    json!({"key": key, "value": {"stringValue": value}})
}

/// An instant as OTLP says it: nanoseconds of the Unix epoch.
fn nanos(at: &str) -> u128 {
    at.parse::<oxsdatatypes::DateTime>()
        .ok()
        .and_then(|t| t.checked_sub("1970-01-01T00:00:00Z".parse::<oxsdatatypes::DateTime>().ok()?))
        .map(|d| (orexis::clock::seconds_of(d).max(0.0) * 1e9) as u128)
        .unwrap_or(0)
}

/// EVERY ACTIVITY THE JOURNAL HOLDS THAT `endpoint` WAS NOT SENT, as one OTLP body, and the activities in it; None
/// where there is none.
pub fn batch(journal: &Journal, agent: &str, endpoint: &str) -> Option<(String, Vec<String>)> {
    let unshipped = rows(
        journal,
        &format!(
            "PREFIX orexis: <http://example.org/orexis#>
             PREFIX prov: <http://www.w3.org/ns/prov#>
             SELECT ?a ?kind ?start ?took WHERE {{ GRAPH ?a {{ ?a a <{ACTIVITY}> , ?kind ; \
             prov:startedAtTime ?start ; orexis:tookS ?took . \
             FILTER(?kind != <{ACTIVITY}>) FILTER NOT EXISTS {{ ?a <{SHIPPED_TO}> \"{endpoint}\" }} }} }} ORDER BY ?start ?a"
        ),
    );
    if unshipped.is_empty() {
        return None;
    }
    //  WHAT EACH ACTIVITY WAS BEGUN INSIDE, over everything the journal holds: a trace is named for its root.
    //  AN ACTIVITY THAT LASTS IS NO PARENT OF WHAT A TURN DID WITHIN IT: a perceiving is part of a listening of a
    //  season and a planning of its package's running, and drawn as their children every activity of a run was one
    //  trace that never ended. What lasts is told by its end having a name (`prov:qualifiedEnd`), or by not having
    //  ended; a turn's activity inside one begins a trace of its own and LINKS to it, and what lasts nests in what
    //  lasts, the lifecycle one trace.
    let lasting: BTreeSet<String> = rows(
        journal,
        &format!(
            "PREFIX orexis: <http://example.org/orexis#>
             PREFIX prov: <http://www.w3.org/ns/prov#>
             SELECT ?a WHERE {{ GRAPH ?a {{ ?a a <{ACTIVITY}> .              FILTER(EXISTS {{ ?a prov:qualifiedEnd ?e }} || NOT EXISTS {{ ?a orexis:tookS ?t }}) }} }}"
        ),
    )
    .into_iter()
    .filter_map(|r| r.get("a").cloned())
    .collect();
    let part_of: BTreeMap<String, String> = rows(
        journal,
        "PREFIX dcterms: <http://purl.org/dc/terms/> SELECT ?a ?p WHERE { GRAPH ?a { ?a dcterms:isPartOf ?p } }",
    )
    .into_iter()
    .filter_map(|r| Some((r.get("a")?.clone(), r.get("p")?.clone())))
    .collect();
    let mut triggers: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for r in rows(
        journal,
        "PREFIX prov: <http://www.w3.org/ns/prov#> SELECT ?a ?x WHERE { GRAPH ?a { ?a prov:wasStartedBy ?x } } ORDER BY ?a ?x",
    ) {
        if let (Some(a), Some(x)) = (r.get("a"), r.get("x")) {
            triggers.entry(a.clone()).or_default().push(x.clone());
        }
    }
    //  WHAT GENERATED EACH THING, the class an event said it is and the instant it was said at.
    let mut generated: BTreeMap<String, String> = BTreeMap::new();
    let mut kinds: BTreeMap<String, String> = BTreeMap::new();
    let mut said: BTreeMap<String, Vec<(String, String, Option<String>)>> = BTreeMap::new();
    for r in rows(
        journal,
        "PREFIX prov: <http://www.w3.org/ns/prov#>
         SELECT ?x ?c ?k ?t WHERE { GRAPH ?c { ?x prov:wasGeneratedBy ?c \
         OPTIONAL { ?x a ?k } OPTIONAL { ?x prov:generatedAtTime ?t } } } ORDER BY ?c ?t ?x",
    ) {
        if let (Some(x), Some(c)) = (r.get("x"), r.get("c")) {
            generated.insert(x.clone(), c.clone());
            if let Some(kind) = r.get("k") {
                kinds.insert(x.clone(), kind.clone());
                said.entry(c.clone())
                    .or_default()
                    .push((x.clone(), local(kind).to_string(), r.get("t").cloned()));
            }
        }
    }
    let mut parents: BTreeMap<String, String> = part_of
        .iter()
        .filter(|(a, p)| lasting.contains(*a) || !lasting.contains(*p))
        .map(|(a, p)| (a.clone(), p.clone()))
        .collect();
    //  WHAT CAUSED A TURN'S ACTIVITY IS ITS PARENT where it is inside no other of its turn: the activity that
    //  generated the first of its triggers one generated, so a reading perceived, the revision of it, the planning
    //  and the walk it began are one trace, read down as what caused what. What lasts is caused into no trace, and
    //  causes none: a running begun by a booting's end stays in the lifecycle's.
    for (a, started_by) in &triggers {
        if lasting.contains(a) || parents.contains_key(a) {
            continue;
        }
        let cause = started_by
            .iter()
            .filter_map(|x| generated.get(x))
            .find(|cause| *cause != a && !lasting.contains(*cause));
        if let Some(cause) = cause {
            parents.insert(a.clone(), cause.clone());
        }
    }
    let root = |a: &str| -> String {
        let (mut at, mut seen) = (a.to_string(), BTreeSet::new());
        while let Some(parent) = parents.get(&at) {
            if !seen.insert(at.clone()) {
                break;
            }
            at = parent.clone();
        }
        at
    };
    //  WHAT A TRIGGER IS CALLED: the class it said it is, or its own name where it said none, as a graph says none.
    let called = |x: &str| {
        kinds
            .get(x)
            .map_or_else(|| local(x).to_string(), |k| local(k).to_string())
    };
    let mut spans = Vec::new();
    let mut shipped = Vec::new();
    for r in &unshipped {
        let (Some(a), Some(kind), Some(start), Some(took)) = (r.get("a"), r.get("kind"), r.get("start"), r.get("took"))
        else {
            continue;
        };
        let begins = nanos(start);
        let ends = begins + (took.parse::<f64>().unwrap_or(0.0).max(0.0) * 1e9) as u128;
        let started_by = triggers.get(a).cloned().unwrap_or_default();
        let mut attributes = vec![text("orexis.agent", agent)];
        if !started_by.is_empty() {
            //  ONE ATTRIBUTE, since a span's keys are unique: every trigger's class, in the order of their names.
            let named: Vec<String> = started_by.iter().map(|x| called(x)).collect();
            attributes.push(text(TRIGGER, &named.join(" ")));
        }
        //  A LINK PER TRIGGER AN ACTIVITY THAT IS NOT ITS PARENT GENERATED, saying which: its class and its name, the
        //  name the mark on the causing span carries.
        let mut links: Vec<Value> = started_by
            .iter()
            .filter_map(|x| Some((x, generated.get(x)?)))
            .filter(|(_, cause)| *cause != a && parents.get(a) != Some(*cause))
            .map(|(x, cause)| {
                json!({
                    "traceId": hex(&root(cause), 32),
                    "spanId": hex(cause, 16),
                    "attributes": [text(TRIGGER, &called(x)), text(ENTITY, x)],
                })
            })
            .collect();
        //  WHAT LASTS THAT IT IS PART OF, a link and no parent: the listening a perceiving was of.
        if let Some(whole) = part_of.get(a).filter(|whole| parents.get(a) != Some(*whole)) {
            links.push(json!({
                "traceId": hex(&root(whole), 32),
                "spanId": hex(whole, 16),
                "attributes": [text(PART_OF, whole)],
            }));
        }
        let events: Vec<Value> = said
            .get(a)
            .map(|events| {
                events
                    .iter()
                    .map(|(x, kind, at)| {
                        let at = at.as_deref().map_or(begins, nanos);
                        json!({"timeUnixNano": at.to_string(), "name": kind, "attributes": [text(ENTITY, x)]})
                    })
                    .collect()
            })
            .unwrap_or_default();
        spans.push(json!({
            "traceId": hex(&root(a), 32),
            "spanId": hex(a, 16),
            "parentSpanId": parents.get(a).map(|p| hex(p, 16)).unwrap_or_default(),
            "name": local(kind),
            "kind": 1,
            "startTimeUnixNano": begins.to_string(),
            "endTimeUnixNano": ends.to_string(),
            "attributes": attributes,
            "events": events,
            "links": links,
        }));
        shipped.push(a.clone());
    }
    let body = json!({"resourceSpans": [{
        "resource": {"attributes": [text("service.name", agent)]},
        "scopeSpans": [{"scope": {"name": "orexis"}, "spans": spans}],
    }]});
    Some((body.to_string(), shipped))
}

/// Say of each of `activities` that `endpoint` was sent it.
pub fn mark(journal: &Journal, activities: &[String], endpoint: &str) {
    for activity in activities {
        let Ok(node) = NamedNode::new(activity.as_str()) else {
            continue;
        };
        let said = triple(node.clone(), SHIPPED_TO, Literal::new_simple_literal(endpoint));
        if let Err(e) = journal.add(&node, vec![said]) {
            log::warn!("the journal refused to say an activity was shipped: {e}");
        }
    }
}

/// Ship what the journal holds unshipped, by `send`, and mark what was accepted; how many activities went.
pub async fn ship(journal: &Journal, agent: &str, endpoint: &str, send: &Send) -> usize {
    let Some((body, activities)) = batch(journal, agent, endpoint) else {
        return 0;
    };
    if !send(body).await {
        return 0;
    }
    mark(journal, &activities, endpoint);
    activities.len()
}

/// POST each body to `endpoint`'s traces, awaited on the runtime, and say whether it was accepted.
pub fn post(endpoint: &str) -> Send {
    let url = format!("{endpoint}/v1/traces");
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(2))
        .user_agent("orexis-agent")
        .build()
        .map_err(|e| e.to_string());
    let refused = Arc::new(std::sync::atomic::AtomicBool::new(false));
    Arc::new(move |body: String| -> Sending {
        let (url, refused) = (url.clone(), refused.clone());
        let asked = client
            .as_ref()
            .map(|client| client.post(&url).header("Content-Type", "application/json").body(body))
            .map_err(String::clone);
        Box::pin(async move {
            let sent = match asked {
                Ok(asked) => asked
                    .send()
                    .await
                    .and_then(reqwest::Response::error_for_status)
                    .map(|_| ())
                    .map_err(|e| e.to_string()),
                Err(e) => Err(format!("no client: {e}")),
            };
            match sent {
                Ok(()) => {
                    refused.store(false, std::sync::atomic::Ordering::Relaxed);
                    true
                }
                Err(e) => {
                    if !refused.swap(true, std::sync::atomic::Ordering::Relaxed) {
                        log::warn!("the tracer at {url} refused the agent's spans, and they stay unshipped: {e}");
                    }
                    false
                }
            }
        })
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    use orexis::rdf::{double, instant, mint, typed};
    use oxigraph::model::Triple;

    const PLANNING: &str = "http://example.org/orexis/planning#Planning";
    const SEARCHING: &str = "http://example.org/test#Searching";
    const REVISING: &str = "http://example.org/orexis/belief#Revising";
    const REVISED: &str = "http://example.org/orexis/belief#Revised";
    const TRACER: &str = "http://127.0.0.1:4318";

    fn at(text: &str) -> oxsdatatypes::DateTime {
        text.parse().unwrap()
    }

    fn journal() -> Arc<Journal> {
        Arc::new(Journal::new(600.0, Arc::new(|| at("2026-11-10T12:00:00Z"))).unwrap())
    }

    /// An activity as `orexis-journal/` keeps it.
    fn kept(journal: &Journal, kind: &str, started_by: &[&NamedNode], inside: Option<&NamedNode>) -> NamedNode {
        let a = mint();
        let mut triples: Vec<Triple> = vec![
            typed(a.clone(), kind),
            typed(a.clone(), ACTIVITY),
            triple(
                a.clone(),
                "http://www.w3.org/ns/prov#startedAtTime",
                instant(at("2026-11-10T12:00:00Z")),
            ),
            triple(a.clone(), "http://example.org/orexis#tookS", double(0.5)),
        ];
        for x in started_by {
            triples.push(triple(
                a.clone(),
                "http://www.w3.org/ns/prov#wasStartedBy",
                (*x).clone(),
            ));
        }
        if let Some(parent) = inside {
            triples.push(triple(a.clone(), "http://purl.org/dc/terms/isPartOf", parent.clone()));
        }
        journal
            .record(&a, triples, Some(at("2026-11-10T12:00:00Z")), false)
            .unwrap();
        a
    }

    fn generated(journal: &Journal, by: &NamedNode, kind: &str) -> NamedNode {
        let x = mint();
        journal
            .add(
                by,
                vec![
                    triple(x.clone(), "http://www.w3.org/ns/prov#wasGeneratedBy", by.clone()),
                    typed(x.clone(), kind),
                    triple(
                        x.clone(),
                        "http://www.w3.org/ns/prov#generatedAtTime",
                        instant(at("2026-11-10T12:00:00.25Z")),
                    ),
                ],
            )
            .unwrap();
        x
    }

    fn spans(body: &str) -> Vec<Value> {
        let body: Value = serde_json::from_str(body).unwrap();
        body["resourceSpans"][0]["scopeSpans"][0]["spans"]
            .as_array()
            .unwrap()
            .clone()
    }

    /// What the journal keeps is what is shipped: an activity a span, one begun inside another its child in one
    /// trace, an event said in it an event on the span at its own instant, and what caused it its parent: the
    /// activity that generated what started it, so what caused what is one trace.
    #[test]
    fn what_the_journal_keeps_is_shipped_as_spans_with_their_children_and_their_causes() {
        let journal = journal();
        let revising = kept(&journal, REVISING, &[], None);
        let revised = generated(&journal, &revising, REVISED);
        let planning = kept(&journal, PLANNING, &[&revised], None);
        let searching = kept(&journal, SEARCHING, &[], Some(&planning));
        let (body, shipped) = batch(&journal, "fern", TRACER).unwrap();
        assert_eq!(shipped.len(), 3);
        let spans = spans(&body);
        let by = |name: &str| spans.iter().find(|s| s["name"] == name).unwrap().clone();
        let (r, p, s) = (by("Revising"), by("Planning"), by("Searching"));
        assert_eq!(p["spanId"], json!(hex(planning.as_str(), 16)));
        assert_eq!(s["parentSpanId"], p["spanId"], "begun inside the planning");
        assert_eq!(p["parentSpanId"], r["spanId"], "which the revising caused");
        assert_eq!(r["parentSpanId"], "", "and nothing the journal knows caused that");
        assert_eq!(r["traceId"], json!(hex(revising.as_str(), 32)), "so the trace is its");
        assert_eq!(p["traceId"], r["traceId"]);
        assert_eq!(s["traceId"], r["traceId"]);
        assert_eq!(p["links"], json!([]), "a parent is not linked to as well");
        let mark = &r["events"][0];
        assert_eq!(mark["name"], "Revised");
        assert_eq!(
            mark["attributes"],
            json!([text(ENTITY, revised.as_str())]),
            "and the mark on the revising carries the same name"
        );
        let after = mark["timeUnixNano"].as_str().unwrap().parse::<u128>().unwrap()
            - r["startTimeUnixNano"].as_str().unwrap().parse::<u128>().unwrap();
        assert!(
            after.abs_diff(250_000_000) < 1_000,
            "at the instant it was said, not the span's start: {after}"
        );
        assert_eq!(p["traceId"].as_str().unwrap().len(), 32);
        assert_eq!(p["spanId"].as_str().unwrap().len(), 16);
        let took = p["endTimeUnixNano"].as_str().unwrap().parse::<u128>().unwrap()
            - p["startTimeUnixNano"].as_str().unwrap().parse::<u128>().unwrap();
        assert_eq!(took, 500_000_000, "as long as it really took");
        let triggers: Vec<&Value> = p["attributes"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|a| a["key"] == TRIGGER)
            .collect();
        assert_eq!(
            triggers,
            [&text(TRIGGER, "Revised")],
            "one attribute, the trigger's class"
        );
        let _ = searching;
    }

    /// What a turn did inside an activity that lasts is a trace of its own, linked to it: a perceiving is no child of
    /// the listening it is part of, which has not ended, nor a planning of its package's running; and what lasts
    /// nests in what lasts, one trace.
    #[test]
    fn what_a_turn_did_within_an_activity_that_lasts_is_a_trace_of_its_own_linked_to_it() {
        const RUNNING: &str = "http://example.org/orexis#PackageRunning";
        const LISTENING: &str = "http://example.org/orexis/sensing#Listening";
        const PERCEIVING: &str = "http://example.org/orexis/sensing#Perceiving";
        let journal = journal();
        let ended = mint();
        let running = kept(&journal, RUNNING, &[], None);
        journal
            .add(
                &running,
                vec![triple(running.clone(), "http://www.w3.org/ns/prov#qualifiedEnd", ended)],
            )
            .unwrap();
        let listening = kept(&journal, LISTENING, &[], Some(&running));
        journal
            .add(
                &listening,
                vec![triple(
                    listening.clone(),
                    "http://www.w3.org/ns/prov#qualifiedEnd",
                    mint(),
                )],
            )
            .unwrap();
        let perceiving = kept(&journal, PERCEIVING, &[], Some(&listening));
        let (body, _) = batch(&journal, "fern", TRACER).unwrap();
        let spans = spans(&body);
        let by = |name: &str| spans.iter().find(|s| s["name"] == name).unwrap().clone();
        let (r, l, p) = (by("PackageRunning"), by("Listening"), by("Perceiving"));
        assert_eq!(l["parentSpanId"], r["spanId"], "what lasts nests in what lasts");
        assert_eq!(l["traceId"], r["traceId"]);
        assert_eq!(p["parentSpanId"], "", "a turn's activity is the root of its trace");
        assert_eq!(p["traceId"], json!(hex(perceiving.as_str(), 32)));
        assert_eq!(
            p["links"],
            json!([{
                "traceId": r["traceId"],
                "spanId": l["spanId"],
                "attributes": [text(PART_OF, listening.as_str())],
            }]),
            "and links to the listening it is part of"
        );
    }

    /// An activity two others caused is the child of the first and links to the second, saying which event of it;
    /// and what an activity that lasts caused is no child of it.
    #[test]
    fn of_two_causes_one_is_the_parent_and_the_other_a_link_and_what_lasts_is_neither() {
        const RUNNING: &str = "http://example.org/orexis#PackageRunning";
        let journal = journal();
        let revising = kept(&journal, REVISING, &[], None);
        let searching = kept(&journal, SEARCHING, &[], None);
        let (one, two) = (
            generated(&journal, &revising, REVISED),
            generated(&journal, &searching, REVISED),
        );
        let planning = kept(&journal, PLANNING, &[&one, &two], None);
        let running = kept(&journal, RUNNING, &[], None);
        journal
            .add(
                &running,
                vec![triple(
                    running.clone(),
                    "http://www.w3.org/ns/prov#qualifiedEnd",
                    mint(),
                )],
            )
            .unwrap();
        let said = generated(&journal, &running, REVISED);
        let alone = kept(&journal, "http://example.org/test#Alone", &[&said], None);
        let (body, _) = batch(&journal, "fern", TRACER).unwrap();
        let spans = spans(&body);
        let id = |a: &NamedNode| json!(hex(a.as_str(), 16));
        let p = spans.iter().find(|s| s["spanId"] == id(&planning)).unwrap();
        let parent = p["parentSpanId"].clone();
        let (cause, other) = if parent == id(&revising) {
            (&revising, &searching)
        } else {
            (&searching, &revising)
        };
        assert_eq!(parent, id(cause), "one of the two is its parent");
        assert_eq!(p["traceId"], json!(hex(cause.as_str(), 32)));
        assert_eq!(p["links"].as_array().unwrap().len(), 1, "and the other a link");
        assert_eq!(p["links"][0]["spanId"], id(other));
        assert_eq!(p["links"][0]["traceId"], json!(hex(other.as_str(), 32)));
        let a = spans.iter().find(|s| s["spanId"] == id(&alone)).unwrap();
        assert_eq!(a["parentSpanId"], "", "what lasts is no span parent of what it caused");
        assert_eq!(a["links"][0]["spanId"], id(&running), "and is linked to");
    }

    /// An activity is marked shipped only where the tracer accepted it, and is not shipped twice; what a tracer
    /// refused stays in the journal for the next time.
    #[tokio::test]
    async fn an_activity_is_shipped_once_and_stays_unshipped_where_the_tracer_refused() {
        let journal = journal();
        kept(&journal, PLANNING, &[], None);
        let sent: Arc<Mutex<Vec<String>>> = Arc::default();
        let refusing: Send = Arc::new(|_| Box::pin(async { false }));
        assert_eq!(ship(&journal, "fern", TRACER, &refusing).await, 0);
        let got = sent.clone();
        let accepting: Send = Arc::new(move |body| {
            got.lock().unwrap().push(body);
            Box::pin(async { true })
        });
        assert_eq!(
            ship(&journal, "fern", TRACER, &accepting).await,
            1,
            "refused before, shipped now"
        );
        assert_eq!(ship(&journal, "fern", TRACER, &accepting).await, 0, "and not again");
        assert_eq!(sent.lock().unwrap().len(), 1);
        kept(&journal, SEARCHING, &[], None);
        assert_eq!(
            ship(&journal, "fern", TRACER, &accepting).await,
            1,
            "only what came since"
        );
        assert_eq!(
            ship(&journal, "fern", "http://another:4318", &accepting).await,
            2,
            "another cold store has its own"
        );
    }
}
