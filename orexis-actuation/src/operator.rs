//! THE OPERATOR, the package's core: the agent's members, and what it does of a step's commands — each device's
//! settings made into the document it is sent, sent through the member that reaches it, and kept as the
//! `sosa:Actuation`s made.

use std::collections::BTreeMap;

use oxigraph::model::{GraphName, Literal, NamedNode, Quad, Term};
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::document::Document;
use orexis::ontology::{BELIEF, RECORDED, local_of};
use orexis::rdf::{RDF_TYPE, boolean, instant, mint};
use orexis::store::{Store, Within, value};
use orexis::task::{Heard, Turn};
use orexis_transport::{Exchange, Members};

use crate::encode::{document, json_of};

/// What the operator does as an activity, and the graph it keeps of what it made.
const ACTUATING: &str = "http://example.org/orexis/actuation#Actuating";
const NUDGING: &str = "http://example.org/orexis/actuation#Nudging";
/// What a nudge sets, and the sensors a reading due names, in sensing's words.
const SENSE_NOW: &str = "http://example.org/orexis/actuation#SenseNow";
const DUE: &str = "http://example.org/orexis/sensing#due";
/// The operator's jobs: a step's commands, and a reading due.
pub(crate) const ACTUATE: usize = 0;
pub(crate) const NUDGE: usize = 1;
const ACTUATION_GRAPH: &str = "http://example.org/orexis/actuation#ActuationGraph";
/// What a step's commands are kept as, in execution's words, which the operator reads.
const COMMANDS: &str = "http://example.org/orexis/execution#commands";
const ACTUATOR: &str = "http://example.org/orexis/execution#actuator";
const PROPERTY: &str = "http://example.org/orexis/execution#property";
const VALUE: &str = "http://example.org/orexis/execution#value";
/// An act made, in SOSA's words.
const ACTUATION: &str = "http://www.w3.org/ns/sosa/Actuation";
const MADE_BY_ACTUATOR: &str = "http://www.w3.org/ns/sosa/madeByActuator";
const ACTS_ON_PROPERTY: &str = "http://www.w3.org/ns/sosa/actsOnProperty";
const HAS_SIMPLE_RESULT: &str = "http://www.w3.org/ns/sosa/hasSimpleResult";
const RESULT_TIME: &str = "http://www.w3.org/ns/sosa/resultTime";

/// One row of a command graph: a property of an actuator, and the value it is set to.
#[derive(Clone)]
struct Setting {
    property: NamedNode,
    value: Literal,
}

/// THE OPERATOR THE SELF PLAYS: the agent's beliefs, where a step's commands are kept, the self whose acts it keeps,
/// and its members.
pub struct Operator {
    beliefs: Store,
    me: String,
    members: Members,
}

impl Operator {
    pub fn new(store: &Store, members: Members) -> Result<Self, Error> {
        let me = orexis::boot::selves(store)?.into_iter().next().unwrap_or_default();
        Ok(Operator {
            beliefs: store.clone(),
            me,
            members,
        })
    }

    /// What the operator's policy does of its triggers: a step's commands actuated, or the boards of the sensors
    /// whose readings are due nudged.
    pub fn heard_event(&mut self, tag: usize, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        match tag {
            NUDGE => self.nudge(event, pass),
            _ => self.actuate(event, pass),
        }
    }

    /// Each actuator the order the event names sets, sent the document its settings make through the member that
    /// reaches it as a channel it is sent on, and each setting sent kept as a `sosa:Actuation` in an
    /// `actuation:ActuationGraph`, the graph written. A setting whose property says no pointer, and an actuator no
    /// member reaches, are passed over, in the log.
    fn actuate(&mut self, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let Some(graph) = event.named(COMMANDS).cloned() else {
            return Ok(Vec::new());
        };
        let commands = settings_of(&self.beliefs, &graph)?;
        let activity = pass.begin(ACTUATING, std::slice::from_ref(&graph));
        let made = self.send(&commands);
        pass.end(activity);
        let made = made?;
        if made.is_empty() {
            return Ok(Vec::new());
        }
        Ok(vec![actuated(&self.beliefs, &self.me, &made, pass.now)?])
    }

    /// Each sensor the event says is due told to sense, `actuation:SenseNow` set true, through the member that reaches
    /// it; kept nowhere, a nudge being no step's act.
    fn nudge(&mut self, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let due: Vec<NamedNode> = event.all(DUE).into_iter().cloned().collect();
        if due.is_empty() {
            return Ok(Vec::new());
        }
        let nudges: BTreeMap<NamedNode, Vec<Setting>> = due
            .iter()
            .map(|sensor| {
                let sense = Setting {
                    property: NamedNode::new_unchecked(SENSE_NOW),
                    value: boolean(true),
                };
                (sensor.clone(), vec![sense])
            })
            .collect();
        let activity = pass.begin(NUDGING, &due);
        let sent = self.send(&nudges);
        pass.end(activity);
        sent?;
        Ok(Vec::new())
    }

    /// Each actuator's document sent; what was sent of each, the settings made.
    fn send(&self, commands: &BTreeMap<NamedNode, Vec<Setting>>) -> Result<Vec<(NamedNode, Setting)>, Error> {
        let mut made = Vec::new();
        for (actuator, settings) in commands {
            let mut pointed = Vec::new();
            let mut kept = Vec::new();
            for setting in settings {
                match pointer_of(&self.beliefs, &setting.property)? {
                    Some(pointer) => {
                        pointed.push((pointer, json_of(&setting.value)));
                        kept.push(setting);
                    }
                    None => log::warn!(
                        "{}: {} says no command pointer, so it is not set",
                        local_of(actuator.as_str()),
                        local_of(setting.property.as_str())
                    ),
                }
            }
            let Some(sent) = document(&pointed).filter(|_| !pointed.is_empty()) else {
                log::warn!(
                    "{}: its settings make no document, so it is told nothing",
                    local_of(actuator.as_str())
                );
                continue;
            };
            match self.members.reaching(actuator.as_str())? {
                Some((member, Exchange::Sent)) => {
                    member.send(actuator.as_str(), sent.as_bytes(), None)?;
                    made.extend(kept.into_iter().map(|s| (actuator.clone(), s.clone())));
                }
                _ => log::warn!(
                    "{}: no member of the agent's reaches it, so its command is not sent",
                    local_of(actuator.as_str())
                ),
            }
        }
        Ok(made)
    }
}

/// The settings a command graph keeps, by actuator.
fn settings_of(store: &Store, graph: &NamedNode) -> Result<BTreeMap<NamedNode, Vec<Setting>>, Error> {
    let engine = store.engine();
    let in_graph = Some(graph.as_ref().into());
    let mut out: BTreeMap<NamedNode, Vec<Setting>> = BTreeMap::new();
    for q in engine
        .quads_for_pattern(None, Some(NamedNode::new_unchecked(ACTUATOR).as_ref()), None, in_graph)
        .flatten()
    {
        let Term::NamedNode(actuator) = q.object else {
            continue;
        };
        let object = |predicate: &str| {
            engine
                .quads_for_pattern(
                    Some(q.subject.as_ref()),
                    Some(NamedNode::new_unchecked(predicate).as_ref()),
                    None,
                    in_graph,
                )
                .flatten()
                .next()
                .map(|p| p.object)
        };
        if let (Some(Term::NamedNode(property)), Some(Term::Literal(value))) = (object(PROPERTY), object(VALUE)) {
            out.entry(actuator).or_default().push(Setting { property, value });
        }
    }
    Ok(out)
}

/// Where in the document a device is sent a value of `property` is written: its `actuation:commandPointer`, as the
/// common beliefs say it.
fn pointer_of(store: &Store, property: &NamedNode) -> Result<Option<String>, Error> {
    const POINTER_Q: &str = "PREFIX actuation: <http://example.org/orexis/actuation#>
    SELECT ?pointer WHERE { $property actuation:commandPointer ?pointer }";
    let common = store.graphs_of(&[BELIEF], &Within::common())?;
    let graphs: Vec<&str> = common.iter().map(String::as_str).collect();
    let found = store.rows(
        &bind(POINTER_Q, &[("property", Value::iri(property.as_str()))])?,
        &graphs,
    )?;
    Ok(found.first().and_then(|r| value(r, "pointer")))
}

/// THE ACTS ONE ACTUATING MADE, kept as the agent's own: an `actuation:ActuationGraph` of a `sosa:Actuation` per
/// setting sent, the actuator that made it, the property it acted on, the value and the instant; the graph's name.
fn actuated(store: &Store, me: &str, made: &[(NamedNode, Setting)], now: DateTime) -> Result<String, Error> {
    let tail = |n: &NamedNode| {
        n.as_str()
            .rsplit(['/', ':', '#'])
            .next()
            .unwrap_or_default()
            .to_string()
    };
    let graph = NamedNode::new(format!(
        "http://example.org/orexis/graph/actuation/{}/{}",
        local_of(me),
        tail(&mint())
    ))
    .map_err(|e| Error::Evaluation(e.to_string()))?;
    let into = GraphName::NamedNode(graph.clone());
    let mut quads = vec![Quad::new(
        graph.clone(),
        NamedNode::new_unchecked(RDF_TYPE),
        NamedNode::new_unchecked(ACTUATION_GRAPH),
        GraphName::DefaultGraph,
    )];
    for (actuator, setting) in made {
        let act = NamedNode::new_unchecked(format!("{}#{}", graph.as_str(), tail(&mint())));
        let mut said = |predicate: &str, object: Term| {
            quads.push(Quad::new(
                act.clone(),
                NamedNode::new_unchecked(predicate),
                object,
                into.clone(),
            ));
        };
        said(RDF_TYPE, NamedNode::new_unchecked(ACTUATION).into());
        said(MADE_BY_ACTUATOR, actuator.clone().into());
        said(ACTS_ON_PROPERTY, setting.property.clone().into());
        said(HAS_SIMPLE_RESULT, setting.value.clone().into());
        said(RESULT_TIME, instant(now).into());
    }
    store.put_document(&Document::of_quads(quads), Some(me), None, Some(RECORDED), true)?;
    Ok(graph.as_str().to_string())
}
