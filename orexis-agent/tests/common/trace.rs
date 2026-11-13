//! WHAT EVERY AGENT OF A WALK DID, IN THE ORDER IT WAS SAID, for a walk being looked into: each activity a package
//! began with what triggered it, each event said while it was open, and whatever the test's bus carried. A trigger
//! that is an event is named by the line it was said on, so a cycle reads as a chain of line numbers; one that is a
//! graph is named by the graph.
#![allow(dead_code)]

use std::collections::BTreeMap;
use std::sync::{Arc, Mutex};

use orexis::activity::{Ended, Started};
use orexis::clock::{Clock, isoformat};
use orexis::events::{Event, as_of};
use orexis::task::Running;

#[derive(Default)]
struct Kept {
    lines: Vec<String>,
    /// The line each event was said on, by its node.
    said: BTreeMap<String, usize>,
    /// The activities each agent has open, innermost last.
    open: BTreeMap<String, Vec<String>>,
}

/// The trace of a walk, shared by every agent in it.
#[derive(Clone, Default)]
pub struct Trace(Arc<Mutex<Kept>>);

fn local(iri: &str) -> &str {
    iri.rsplit(['#', '/']).next().unwrap_or(iri)
}

impl Trace {
    /// Hear everything `running`, the agent `agent`, says from here on.
    pub fn watch(&self, agent: &'static str, running: &Running, clock: Arc<dyn Clock>) {
        let kept = self.0.clone();
        running.watch().connect(move |event: &dyn Event, node| {
            let mut kept = kept.lock().unwrap();
            let at = isoformat(event.at().unwrap_or_else(|| clock.now()));
            let depth = kept.open.get(agent).map_or(0, Vec::len);
            let pad = "  ".repeat(depth);
            let n = kept.lines.len();
            if let Some(started) = as_of::<Started>(event) {
                let triggers: Vec<String> = started
                    .triggers
                    .iter()
                    .map(|t| match kept.said.get(t.as_str()) {
                        Some(line) => format!("#{line}"),
                        None => local(t.as_str()).chars().take(48).collect(),
                    })
                    .collect();
                kept.lines.push(format!(
                    "{n:5} {} {agent} {pad}> {} <- [{}]",
                    &at[11..],
                    local(started.kind),
                    triggers.join(" ")
                ));
                kept.open
                    .entry(agent.to_string())
                    .or_default()
                    .push(started.activity.as_str().to_string());
            } else if let Some(ended) = as_of::<Ended>(event) {
                let open = kept.open.entry(agent.to_string()).or_default();
                open.retain(|a| a != ended.activity.as_str());
                kept.lines.push(format!(
                    "{n:5} {} {agent} {pad}< {} {:.3}s",
                    &at[11..],
                    local(ended.kind),
                    ended.duration_s
                ));
            } else {
                let kind = event.kind().or(event.metric()).unwrap_or("?");
                let about: Vec<String> = event
                    .about()
                    .iter()
                    .map(|(p, t)| {
                        let t = t.to_string();
                        format!(
                            "{}={}",
                            local(p),
                            local(t.trim_matches(['<', '>'])).chars().take(40).collect::<String>()
                        )
                    })
                    .collect();
                let marks: Vec<String> = event
                    .marks()
                    .iter()
                    .map(|(name, mark)| format!("{name}={mark:?}"))
                    .collect();
                kept.lines.push(format!(
                    "{n:5} {} {agent} {pad}. {} {} {}",
                    &at[11..],
                    local(kind),
                    about.join(" "),
                    marks.join(" ")
                ));
                kept.said.insert(node.as_str().to_string(), n);
            }
        });
    }

    /// Something the test itself saw: a document on the bus, a drive, a step of the road.
    pub fn note(&self, at: &str, text: &str) {
        let mut kept = self.0.lock().unwrap();
        let n = kept.lines.len();
        let at = if at.len() > 11 { &at[11..] } else { at };
        kept.lines.push(format!("{n:5} {at} {text}"));
    }

    /// Every line, in the order said.
    pub fn lines(&self) -> Vec<String> {
        self.0.lock().unwrap().lines.clone()
    }
}
