//! THE ROAD AS A TEST PLAYS IT, closing the loop a replay left open: what `simulation/simulator.py` does of a world's
//! vans, read off the same words of the same documents, so the couriers' own drives decide the fixes they are told.
//!
//! A VAN IS A BODY THAT MOVES ON COMMAND: told `{"to": {"x": …, "y": …}}`, it is on that cell `sim:delayS` later where
//! the cell is a neighbour of the one it stands on, and it refuses anything else. Its position fix reports its
//! coordinates. A CONTACT IS PLAYED FROM THE TRUE POSITIONS: the vector from the carrying van to the peer it stands
//! for, or to the nearest thing no receiver of that van identifies, slots taking the nearest first, within the range
//! each of its two sensors declares, and one past the most of each beyond it. A thing with no instrument stands where
//! its model says. Every sensor rides in one message, each number at the pointer the world binds it to.
//!
//! AND IT KEEPS WHERE EVERY VAN STOOD at each step, which is what a walk is held to: nothing a courier believes, and
//! no instant a recording happened to have.
#![allow(dead_code)]

use std::collections::{BTreeMap, BTreeSet};

use oxsdatatypes::DateTime;
use serde_json::{Map, Value as Json, json};

use orexis::clock::seconds_of;
use orexis::ontology::BELIEF;
use orexis::store::{Store, Within, iri, value};

pub type Cell = (i64, i64);

const PREFIXES: &str = "PREFIX sim: <http://example.org/orexis/sim#>
PREFIX courier: <http://example.org/orexis/courier#>
PREFIX sensing: <http://example.org/orexis/sensing#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX ssn-system: <http://www.w3.org/ns/ssn/systems/>
PREFIX schema: <https://schema.org/>
";
const VANS_Q: &str = "SELECT ?van ?x ?y ?xp ?yp ?delay WHERE {
  ?van a courier:Van ; sim:simulatedBy ?model .
  ?column a sosa:Sensor ; sosa:isHostedBy ?van ; sosa:observes courier:Column ; sim:simulatedBy ?cm ; sensing:readingPointer ?xp .
  ?row a sosa:Sensor ; sosa:isHostedBy ?van ; sosa:observes courier:Row ; sim:simulatedBy ?rm ; sensing:readingPointer ?yp .
  ?cm sim:initialValue ?x . ?rm sim:initialValue ?y .
  OPTIONAL { ?model sim:delayS ?delay } } ORDER BY ?van";
const CONTACTS_Q: &str = "SELECT ?contact ?van ?peer ?xp ?yp ?xmost ?ymost WHERE {
  ?contact a sosa:Sample ; sosa:isHostedBy ?van .
  ?column a sosa:Sensor ; sosa:isHostedBy ?contact ; sosa:observes courier:RelativeColumn ; sensing:readingPointer ?xp .
  ?row a sosa:Sensor ; sosa:isHostedBy ?contact ; sosa:observes courier:RelativeRow ; sensing:readingPointer ?yp .
  OPTIONAL { ?contact sosa:isSampleOf ?peer }
  OPTIONAL { ?column ssn-system:hasSystemCapability/ssn-system:hasSystemProperty ?cr .
             ?cr a ssn-system:MeasurementRange ; schema:maxValue ?xmost }
  OPTIONAL { ?row ssn-system:hasSystemCapability/ssn-system:hasSystemProperty ?rr .
             ?rr a ssn-system:MeasurementRange ; schema:maxValue ?ymost } } ORDER BY ?contact";
const POSED_Q: &str = "SELECT ?thing ?x ?y WHERE { ?thing sim:simulatedBy ?model . ?model sim:x ?x ; sim:y ?y }";

struct Van {
    at: Cell,
    delay: f64,
    pointers: (String, String),
    /// The cell it is driving to, and the instant it is there.
    moving: Option<(DateTime, Cell)>,
}

struct Contact {
    van: String,
    peer: Option<String>,
    pointers: (String, String),
    most: (Option<i64>, Option<i64>),
}

/// The vans of a world, what stands on its road, and where each van stood at every step.
pub struct Road {
    vans: BTreeMap<String, Van>,
    posed: BTreeMap<String, Cell>,
    contacts: Vec<Contact>,
    /// Each step's instant and where every van stood then, by the van's local name.
    pub trail: Vec<(DateTime, BTreeMap<String, Cell>)>,
    /// What a van was told that it refused.
    pub refused: Vec<String>,
}

fn whole(row: &orexis::store::Row, variable: &str) -> Option<i64> {
    value(row, variable)?.parse::<f64>().ok().map(|n| n.round() as i64)
}

pub fn local(iri: &str) -> String {
    iri.rsplit('#').next().unwrap_or(iri).to_string()
}

fn put(document: &mut Json, pointer: &str, number: f64) {
    let mut at = document;
    let mut keys = pointer.trim_start_matches('/').split('/').peekable();
    while let Some(key) = keys.next() {
        let map = at.as_object_mut().unwrap();
        if keys.peek().is_none() {
            map.insert(key.to_string(), json!(number));
            return;
        }
        at = map.entry(key.to_string()).or_insert_with(|| Json::Object(Map::new()));
    }
}

impl Road {
    /// The road of the world `store` was booted from, as its documents pose it.
    pub fn of(store: &Store) -> Road {
        let graphs = store.graphs_of(&[BELIEF], &Within::common()).unwrap();
        let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
        let rows = |text: &str| store.rows(&format!("{PREFIXES}{text}"), &graphs).unwrap();
        let vans: BTreeMap<String, Van> = rows(VANS_Q)
            .iter()
            .map(|r| {
                (
                    iri(r, "van").unwrap(),
                    Van {
                        at: (whole(r, "x").unwrap(), whole(r, "y").unwrap()),
                        delay: value(r, "delay").and_then(|d| d.parse().ok()).unwrap_or(0.0),
                        pointers: (value(r, "xp").unwrap(), value(r, "yp").unwrap()),
                        moving: None,
                    },
                )
            })
            .collect();
        assert!(!vans.is_empty(), "the world poses no van the simulator plays");
        let contacts = rows(CONTACTS_Q)
            .iter()
            .map(|r| Contact {
                van: iri(r, "van").unwrap(),
                peer: iri(r, "peer"),
                pointers: (value(r, "xp").unwrap(), value(r, "yp").unwrap()),
                most: (whole(r, "xmost"), whole(r, "ymost")),
            })
            .collect();
        let posed = rows(POSED_Q)
            .iter()
            .map(|r| {
                (
                    iri(r, "thing").unwrap(),
                    (whole(r, "x").unwrap(), whole(r, "y").unwrap()),
                )
            })
            .collect();
        Road {
            vans,
            posed,
            contacts,
            trail: Vec::new(),
            refused: Vec::new(),
        }
    }

    /// A van told a cell at `at`, on the topic it listens to: `actuators/<van>/command`.
    pub fn command(&mut self, at: DateTime, topic: &str, payload: &Json) {
        let name = topic.split('/').nth(1).unwrap_or_default();
        let Some((_, van)) = self.vans.iter_mut().find(|(iri, _)| local(iri) == name) else {
            self.refused.push(format!("{topic}: no van listens there"));
            return;
        };
        let (Some(x), Some(y)) = (payload["to"]["x"].as_i64(), payload["to"]["y"].as_i64()) else {
            self.refused
                .push(format!("{name}: told {payload}, which names no cell"));
            return;
        };
        if (x - van.at.0).abs() + (y - van.at.1).abs() != 1 {
            self.refused.push(format!(
                "{name}: told ({x}, {y}) from {:?}, which is no neighbour",
                van.at
            ));
            return;
        }
        let there = at
            .checked_add_day_time_duration(orexis::clock::seconds(van.delay))
            .unwrap();
        van.moving = Some((there, (x, y)));
    }

    fn position(&self, thing: &str) -> Option<Cell> {
        self.vans
            .get(thing)
            .map(|v| v.at)
            .or_else(|| self.posed.get(thing).copied())
    }

    /// Advance to `now` and say every sensor's number, as the one message a board would publish.
    pub fn step(&mut self, now: DateTime) -> String {
        for van in self.vans.values_mut() {
            if let Some((there, to)) = van.moving
                && seconds_of(now.checked_sub(there).unwrap()) >= 0.0
            {
                van.at = to;
                van.moving = None;
            }
        }
        self.trail
            .push((now, self.vans.iter().map(|(iri, v)| (local(iri), v.at)).collect()));
        let mut document = Json::Object(Map::new());
        for van in self.vans.values() {
            put(&mut document, &van.pointers.0, van.at.0 as f64);
            put(&mut document, &van.pointers.1, van.at.1 as f64);
        }
        let identified: BTreeSet<(&str, &str)> = self
            .contacts
            .iter()
            .filter_map(|c| c.peer.as_deref().map(|p| (c.van.as_str(), p)))
            .collect();
        let mut taken: BTreeMap<&str, BTreeSet<&str>> = BTreeMap::new();
        for contact in &self.contacts {
            let Some(here) = self.position(&contact.van) else {
                continue;
            };
            let target = match &contact.peer {
                Some(peer) => self.position(peer),
                None => {
                    let mut things: Vec<(i64, &str, Cell)> = self
                        .vans
                        .keys()
                        .chain(self.posed.keys())
                        .map(String::as_str)
                        .filter(|name| {
                            *name != contact.van
                                && !identified.contains(&(contact.van.as_str(), *name))
                                && !taken.get(contact.van.as_str()).is_some_and(|t| t.contains(name))
                        })
                        .filter_map(|name| {
                            let p = self.position(name)?;
                            Some(((p.0 - here.0).abs() + (p.1 - here.1).abs(), name, p))
                        })
                        .collect();
                    things.sort();
                    things.first().map(|(_, name, p)| {
                        taken.entry(contact.van.as_str()).or_default().insert(name);
                        *p
                    })
                }
            };
            let within = |most: Option<i64>, d: i64| most.is_none_or(|m| d.abs() <= m);
            let vector = match target {
                Some(t) if within(contact.most.0, t.0 - here.0) && within(contact.most.1, t.1 - here.1) => {
                    (t.0 - here.0, t.1 - here.1)
                }
                _ => (
                    contact.most.0.map_or(1000, |m| m + 1),
                    contact.most.1.map_or(1000, |m| m + 1),
                ),
            };
            put(&mut document, &contact.pointers.0, vector.0 as f64);
            put(&mut document, &contact.pointers.1, vector.1 as f64);
        }
        document.to_string()
    }

    /// Whether any van is still on its way to a cell.
    pub fn moving(&self) -> bool {
        self.vans.values().any(|v| v.moving.is_some())
    }

    /// Where the van named `name` stands.
    pub fn at(&self, name: &str) -> Cell {
        self.vans.iter().find(|(iri, _)| local(iri) == name).unwrap().1.at
    }

    /// Every cell something with no instrument stands on.
    pub fn obstacles(&self) -> BTreeSet<Cell> {
        self.posed.values().copied().collect()
    }

    /// The first step at which the van named `name` stood on `cell`.
    pub fn first_on(&self, name: &str, cell: Cell) -> Option<DateTime> {
        self.trail
            .iter()
            .find(|(_, at)| at.get(name) == Some(&cell))
            .map(|(when, _)| *when)
    }
}
