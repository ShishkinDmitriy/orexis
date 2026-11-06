//! WHAT MOVES FROM A GROUND, as `agent/prediction/foresee.py` integrates it: the flows integrated from each ground as
//! the planner lays them, every key of the agent advancing together, and a crossing of a range bound answered as the
//! place the next ground is laid (a-flow-is-integrated-where-the-ground-is-laid, #1000).
//!
//! **THE FLOWS ARE INTEGRATED FROM EACH GROUND**: every `prediction:Flow` that moves a key's property answers a RATE
//! for the subject at an instant, and the flows ADD. What a flow reads is the ground the planner hands, every graph
//! holding at the instant asked beside it, and the keys' current numbers, kept in a working graph of this package's
//! own (`NUMBERS`), and `$value`, its own key's number. Between two grounds the rates are asked at every HAPPENING
//! and held for at most `SEGMENT_S` between; within a segment the value is a straight line, and a crossing of a
//! bound is placed exactly, by division. **EVERY KEY ADVANCES TOGETHER**: soil reading air and air reading soil are
//! two coupled flows, not a cycle. **A RATE KNOWN AS A RANGE GIVES A CORRIDOR**: two trajectories, the low and the
//! high, and the side of an instant is the corridor's worst.
//!
//! **WHAT IS ANSWERED IS THE NEXT KNOT, WITH THE PREDICTED OBSERVATION TO LAY THERE**, or the hour's end where a key
//! the caller lays has moved; this package writes no forecast and no state (#944). **THE KEYS ARE READ OFF THE
//! BELIEF BASE ONCE**: each sensor's latest percept with what the rules concluded of it, and the flows moving its
//! property, off the flow graphs alone; a key no flow moves is foreseen nothing (#989).
//!
//! Every float is computed in the order the Python computes it, so the two agents place a crossing alike.

use oxigraph::model::vocab::xsd;
use oxigraph::model::{GraphName, Literal, NamedNode, Quad, Term, Triple};
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{instant as parse_instant, isoformat, microseconds, seconds_of};
use orexis::foresight::{Foresight as Integration, GraphsAt, Placed};
use orexis::hash::py_float_repr;
use orexis::ontology::{FLOW_GRAPH, local_of};
use orexis::stance::stance;
use orexis::store::{Store, Within, instant, iri, value};

use crate::ontology::{
    FEATURE, FLOW, HORIZON_TERM, MOVES, OBSERVATION_GRAPH, PROPERTY, RATE, RESULT, SOSA, predicted_of,
};
use crate::ranges::{ranges_of, side};

/// HOW FAR PAST THE OBSERVATION THE AGENT LOOKS, where its self graph states no `prediction:horizonS`: a day.
pub const HORIZON_S: f64 = 86400.0;

/// THE LONGEST A RATE IS HELD before the flows are asked again: an hour.
pub const SEGMENT_S: f64 = 3600.0;

/// WHERE A STRETCH'S NUMBER IS READ when its end lies across a bound: this long before the end, or half the stretch.
const EDGE_S: f64 = 60.0;

/// How many places a number the agent writes is rounded to.
const PLACES: i32 = 6;

/// THE KEYS' CURRENT NUMBERS, as the flows read them: a working graph of this package's own in the store the grounds
/// are laid in, classified as nothing, rewritten at every instant the flows are asked at.
pub const NUMBERS: &str = "http://example.org/orexis/graph/ground/foreseen-numbers";

const RDF_TYPE: &str = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";

/// EVERY SENSOR WITH A PERCEPT IN HAND, by sensing's kind and SOSA's pattern.
const SENSORS_Q: &str = "
SELECT DISTINCT ?sensor WHERE {
  GRAPH $cat { ?g a sensing:ObservationGraph }
  GRAPH ?g { ?o sosa:madeBySensor ?sensor } }
ORDER BY ?sensor";

/// THE OBSERVATION IN HAND: the percept begun last, and of two begun at once the one still holding.
const OBSERVATION_Q: &str = "
SELECT ?graph ?node ?taken ?from WHERE {
  GRAPH $cat { ?graph a sensing:ObservationGraph ; dcterms:temporal ?p . ?p orexis:start ?from .
               OPTIONAL { ?p orexis:end ?until } }
  GRAPH ?graph { ?node sosa:madeBySensor $sensor . OPTIONAL { ?node sosa:resultTime ?taken } } }
ORDER BY DESC(?from) ASC(BOUND(?until)) DESC(?until) LIMIT 1";

const KEY_Q: &str = "
SELECT ?feature ?property ?value WHERE {
  $node sosa:hasFeatureOfInterest ?feature ; sosa:observedProperty ?property ; sosa:hasSimpleResult ?value } LIMIT 1";

/// EVERY FLOW MOVING THE PROPERTY, off the graphs of flows alone.
const FLOWS_Q: &str = "SELECT ?flow ?rate WHERE { ?flow a $flow ; $moves $property ; $rate_of ?rate } ORDER BY ?flow";

/// THE HAPPENINGS: every instant inside a stretch at which a belief begins or stops holding.
const HAPPENINGS_Q: &str = "
SELECT DISTINCT ?t WHERE {
  GRAPH $cat { ?g a orexis:BeliefGraph ; dcterms:temporal ?p . { ?p orexis:start ?t } UNION { ?p orexis:end ?t } }
  FILTER(?t > $from && ?t < $to) }";

/// One flow moving a key: its name, and the select answering its rate.
#[derive(Clone, Debug)]
struct Flow {
    flow: String,
    rate: String,
}

/// A knot of a stretch integrated: seconds past the origin, and the low and the high trajectory there.
type Knot = (f64, f64, f64);

/// One key's segment ahead: the low trajectory's rate and stops, and the high one's.
type Plan = (f64, Vec<f64>, f64, Vec<f64>);

/// One contribution a flow answers: its lowest rate, its highest, and the value it stops at.
type Said = (f64, f64, Option<f64>);

/// One key the agent foresees: the sensor, what it observes, the corridor as it stands and the knots of the last
/// stretch integrated, in seconds past the integration's origin.
#[derive(Clone, Debug)]
pub struct Key {
    pub sensor: String,
    pub feature: String,
    pub property: String,
    /// When the reading in hand was taken, seconds past the origin.
    taken: f64,
    /// How far this key is looked at, seconds past the origin.
    horizon: f64,
    ranges: Vec<(f64, f64)>,
    flows: Vec<Flow>,
    /// Whether a crossing of this key is the caller's to lay.
    pub laid: bool,
    pub lo: f64,
    pub hi: f64,
    knots: Vec<Knot>,
}

/// The integration of every key of the agent, carried from ground to ground: `advance` to the next boundary,
/// answering the earliest crossing, and `finish` when the grounds are laid. Made by `foresee` and nothing else.
pub struct Foresight {
    origin: DateTime,
    pub keys: Vec<Key>,
    /// Where the integration stands, past the origin.
    t: Option<f64>,
}

fn round_to(x: f64, places: i32) -> f64 {
    if !x.is_finite() {
        return x;
    }
    format!("{x:.prec$}", prec = places as usize).parse().unwrap_or(x)
}

fn ceil(x: f64) -> f64 {
    x.ceil()
}

impl Foresight {
    /// The last instant any key is looked at.
    pub fn horizon(&self) -> DateTime {
        let furthest = self.keys.iter().map(|k| k.horizon).fold(f64::NEG_INFINITY, f64::max);
        self.instant(furthest)
    }

    fn instant(&self, t: f64) -> DateTime {
        let by = microseconds(t);
        self.origin.checked_add_day_time_duration(by).unwrap_or(self.origin)
    }

    fn s(&self, at: DateTime) -> f64 {
        at.checked_sub(self.origin).map_or(0.0, seconds_of)
    }

    /// Integrate every key from `at` towards `until`, reading `graphs_at` — and answer the earliest instant in
    /// `(at, until]` at which a key the caller lays crosses a range bound, with the predicted observation of each key
    /// crossing there; or the hour's end, where a key the caller lays has moved by then, with the number each such key
    /// then stands at; or None where neither comes before `until`. THE INTEGRATION STOPS AT THE FIRST KNOT, and runs
    /// on only as far as the knot's number needs.
    pub fn advance(
        &mut self,
        store: &Store,
        at: DateTime,
        until: DateTime,
        graphs_at: &mut GraphsAt<'_>,
    ) -> Result<Option<(DateTime, Vec<Triple>)>, Error> {
        let horizon = self.horizon();
        let t0 = self.s(at);
        let t1 = self.s(if until < horizon { until } else { horizon });
        if self.t.is_none() {
            self.catch_up(store, t0, graphs_at)?;
        }
        let standing = self.t.unwrap_or(t0);
        if t1 <= standing + 1e-9 || !self.keys.iter().any(|k| k.laid) {
            self.t = Some(standing.max(t1));
            return Ok(None);
        }
        let t0 = standing;
        let cap = t0 + SEGMENT_S;
        let marks = self.marks(store, t0, t1, cap)?;
        for key in &mut self.keys {
            key.knots = vec![(t0, key.lo, key.hi)];
        }
        let (mut t, mut first, mut far) = (t0, None::<f64>, None::<f64>);
        let mut crossing: Vec<String> = Vec::new();
        'marks: for mark in marks {
            while t < mark - 1e-9 {
                t = self.step(store, t, mark, graphs_at)?;
                match first {
                    None => {
                        let found: Vec<(String, Vec<f64>)> = self
                            .keys
                            .iter()
                            .filter(|k| k.laid)
                            .map(|k| {
                                let pair = &k.knots[k.knots.len().saturating_sub(2)..];
                                (k.sensor.clone(), crossings(pair, &k.ranges, t0, t, k.knots.len() == 2))
                            })
                            .collect();
                        let firsts: Vec<(&String, f64)> = found
                            .iter()
                            .filter(|(_, cs)| !cs.is_empty())
                            .map(|(s, cs)| (s, cs[0]))
                            .collect();
                        if !firsts.is_empty() {
                            let earliest = firsts.iter().map(|(_, c)| *c).fold(f64::INFINITY, f64::min);
                            first = Some(earliest);
                            crossing = firsts
                                .iter()
                                .filter(|(_, c)| (c - earliest).abs() < 1e-9)
                                .map(|(s, _)| (*s).clone())
                                .collect();
                            let mut bound = (earliest + SEGMENT_S).min(t1);
                            for (sensor, cs) in &found {
                                if crossing.contains(sensor) {
                                    for c in cs.iter().filter(|c| **c > earliest + 1e-9) {
                                        bound = bound.min(*c);
                                    }
                                }
                            }
                            far = Some(bound);
                        } else if t >= cap - 1e-9 {
                            //  THE HOUR'S END: a state held past its bound by a margin this package does not read
                            //  is judged again within the hour, for every key the caller lays that has moved.
                            let moved: Vec<usize> = (0..self.keys.len())
                                .filter(|&i| {
                                    let k = &self.keys[i];
                                    k.laid && (k.lo, k.hi) != (k.knots[0].1, k.knots[0].2)
                                })
                                .collect();
                            if !moved.is_empty() {
                                self.stand_at(store, t)?;
                                let when = self.instant(t);
                                let mut said = Vec::new();
                                for i in moved {
                                    let key = &self.keys[i];
                                    said.extend(observation(key, worst(key), when));
                                }
                                return Ok(Some((when, said)));
                            }
                        }
                    }
                    Some(earliest) => {
                        let mut bound = far.unwrap_or(t1);
                        for key in self.keys.iter().filter(|k| crossing.contains(&k.sensor)) {
                            let pair = &key.knots[key.knots.len().saturating_sub(2)..];
                            for c in crossings(pair, &key.ranges, earliest, t, true) {
                                if c > earliest + 1e-9 {
                                    bound = bound.min(c);
                                }
                            }
                        }
                        far = Some(bound);
                    }
                }
                if let (Some(_), Some(far)) = (first, far)
                    && t >= far - 1e-9
                {
                    break 'marks;
                }
            }
        }
        let Some(first) = first else {
            self.stand_at(store, t1)?;
            return Ok(None);
        };
        let far = far.unwrap_or(t1);
        let mut arrival = Vec::new();
        for key in self.keys.iter().filter(|k| crossing.contains(&k.sensor)) {
            //  THE NUMBER LAID AT A CROSSING IS READ AT THE FAR END OF THE STRETCH IT OPENS.
            let (when, value) = number_on_its_side(&key.knots, &key.ranges, first, far);
            arrival.extend(observation(key, value, self.instant(when)));
        }
        self.stand_at(store, first)?;
        Ok(Some((self.instant(first), arrival)))
    }

    /// Take the working graph away: the grounds are laid, and nothing reads the numbers after.
    pub fn finish(&mut self, store: &Store) -> Result<(), Error> {
        store.clear_graph(NUMBERS)
    }

    // --- the integration ------------------------------------------------------------------------------------------

    /// Carry each key from the instant its reading was taken to `t0`, reading what holds at `t0`.
    fn catch_up(&mut self, store: &Store, t0: f64, graphs_at: &mut GraphsAt<'_>) -> Result<(), Error> {
        for i in 0..self.keys.len() {
            let mut t = self.keys[i].taken;
            while t < t0 - 1e-9 {
                self.numbers(store, t)?;
                let mut graphs = vec![NUMBERS.to_string()];
                graphs.extend(graphs_at(self.instant(t0))?);
                let (lo, hi) = (self.keys[i].lo, self.keys[i].hi);
                let (r_lo, stops_lo) = net(&self.rates(store, &self.keys[i], lo, t, &graphs)?, lo, 0);
                let (r_hi, stops_hi) = net(&self.rates(store, &self.keys[i], hi, t, &graphs)?, hi, 1);
                let step = (t0 - t)
                    .min(SEGMENT_S)
                    .min(reach(lo, r_lo, &stops_lo))
                    .min(reach(hi, r_hi, &stops_hi));
                let (a, b) = (shift(lo, r_lo, step, &stops_lo), shift(hi, r_hi, step, &stops_hi));
                let key = &mut self.keys[i];
                (key.lo, key.hi) = if a <= b { (a, b) } else { (b, a) };
                t += step;
            }
        }
        self.t = Some(t0);
        Ok(())
    }

    /// The instants between `t0` and `t1` a segment must end at: every happening, each key's horizon, the hour's end
    /// and `t1`.
    fn marks(&self, store: &Store, t0: f64, t1: f64, cap: f64) -> Result<Vec<f64>, Error> {
        let mut out: Vec<f64> = vec![t1];
        if let Some(cat) = store.catalogue()? {
            let text = bind(
                HAPPENINGS_Q,
                &[
                    ("cat", Value::iri(cat)),
                    ("from", instant(self.instant(t0))),
                    ("to", instant(self.instant(t1))),
                ],
            )?;
            for row in store.rows(&text, &[])? {
                if let Some(t) = value(&row, "t") {
                    out.push(self.s(parse_instant(&t)?));
                }
            }
        }
        out.extend(self.keys.iter().map(|k| k.horizon).filter(|h| t0 < *h && *h < t1));
        if t0 < cap && cap < t1 {
            out.push(cap);
        }
        out.sort_by(f64::total_cmp);
        out.dedup();
        Ok(out)
    }

    /// One segment from `t`, every key together: every key's flows asked at `t` over the same graphs and numbers,
    /// and every key moved by its own sum to `mark`, the hour's end or the nearest stop; each key's knot appended.
    fn step(&mut self, store: &Store, t: f64, mark: f64, graphs_at: &mut GraphsAt<'_>) -> Result<f64, Error> {
        self.numbers(store, t)?;
        let mut graphs = vec![NUMBERS.to_string()];
        graphs.extend(graphs_at(self.instant(t))?);
        let mut plans: Vec<Option<Plan>> = Vec::new();
        for key in &self.keys {
            if t >= key.horizon - 1e-9 {
                plans.push(None);
                continue;
            }
            let said_lo = self.rates(store, key, key.lo, t, &graphs)?;
            let said_hi = if key.hi == key.lo {
                said_lo.clone()
            } else {
                self.rates(store, key, key.hi, t, &graphs)?
            };
            let (r_lo, stops_lo) = net(&said_lo, key.lo, 0);
            let (r_hi, stops_hi) = net(&said_hi, key.hi, 1);
            plans.push(Some((r_lo, stops_lo, r_hi, stops_hi)));
        }
        let mut step = (mark - t).min(SEGMENT_S);
        for (key, plan) in self.keys.iter().zip(&plans) {
            if let Some((r_lo, stops_lo, r_hi, stops_hi)) = plan {
                step = step
                    .min(reach(key.lo, *r_lo, stops_lo))
                    .min(reach(key.hi, *r_hi, stops_hi));
            }
        }
        for (key, plan) in self.keys.iter_mut().zip(&plans) {
            if let Some((r_lo, stops_lo, r_hi, stops_hi)) = plan {
                let (a, b) = (
                    shift(key.lo, *r_lo, step, stops_lo),
                    shift(key.hi, *r_hi, step, stops_hi),
                );
                (key.lo, key.hi) = if a <= b { (a, b) } else { (b, a) };
            }
            key.knots.push((t + step, key.lo, key.hi));
        }
        Ok(t + step)
    }

    /// Every contribution the key's flows answer at `t` for the subject holding `value`.
    fn rates(&self, store: &Store, key: &Key, value_now: f64, t: f64, graphs: &[String]) -> Result<Vec<Said>, Error> {
        let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
        let number = Literal::new_typed_literal(py_float_repr(value_now), xsd::DOUBLE);
        let mut said = Vec::new();
        for flow in &key.flows {
            let answered = bind(
                &flow.rate,
                &[
                    ("feature", Value::iri(key.feature.as_str())),
                    ("at", instant(self.instant(t))),
                    ("value", Value::Term(number.clone().into())),
                ],
            )
            .and_then(|text| store.rows(&text, &graphs));
            let answered = match answered {
                Ok(rows) => rows,
                Err(e) => {
                    log::error!("flow {} would not run for a prediction: {e}", local_of(&flow.flow));
                    continue;
                }
            };
            for row in answered {
                let number = |name: &str| value(&row, name).and_then(|v| v.parse::<f64>().ok());
                let (Some(low), Some(high)) = (number("low").or(number("rate")), number("high").or(number("rate")))
                else {
                    continue;
                };
                said.push((low.min(high), low.max(high), number("until")));
            }
        }
        Ok(said)
    }

    /// Every key as it stands at `t`, read off its knots, and the numbers rewritten there — rounded past any float's
    /// error, so a knot laid at the whole second after a crossing stands on the bound or past it.
    fn stand_at(&mut self, store: &Store, t: f64) -> Result<(), Error> {
        for key in &mut self.keys {
            let (lo, hi) = at_of(&key.knots, t);
            (key.lo, key.hi) = (round_to(lo, 12), round_to(hi, 12));
        }
        self.t = Some(t);
        self.numbers(store, t)
    }

    /// The working graph rewritten with every key's number at `t`.
    fn numbers(&self, store: &Store, t: f64) -> Result<(), Error> {
        store.clear_graph(NUMBERS)?;
        let at = self.instant(t);
        let graph = GraphName::NamedNode(NamedNode::new_unchecked(NUMBERS));
        let quads: Vec<Quad> = self
            .keys
            .iter()
            .flat_map(|key| observation(key, worst(key), at))
            .map(|tr| Quad::new(tr.subject, tr.predicate, tr.object, graph.clone()))
            .collect();
        store.add(quads)
    }
}

impl Integration for Foresight {
    fn horizon(&self) -> DateTime {
        Foresight::horizon(self)
    }

    fn advance(
        &mut self,
        store: &Store,
        at: DateTime,
        until: DateTime,
        graphs_at: &mut GraphsAt<'_>,
    ) -> Result<Option<(DateTime, Vec<Triple>)>, Error> {
        Foresight::advance(self, store, at, until, graphs_at)
    }

    fn finish(&mut self, store: &Store) -> Result<(), Error> {
        Foresight::finish(self, store)
    }
}

/// The agent's foresight from `now`: every key some flow moves, read off the belief base — each sensor's latest
/// percept with what the rules concluded of it, the flows moving its property, the ranges that apply to it and the
/// horizon the agent looks to. None where no key is moved by any flow. `placed` says, of a key's feature and
/// property, whether a crossing of it is the caller's to lay; None lays every key.
pub fn foresee(beliefs: &Store, now: DateTime, placed: Option<&Placed<'_>>) -> Result<Option<Foresight>, Error> {
    let Some(cat) = beliefs.catalogue()? else {
        return Ok(None);
    };
    let horizon = stance(beliefs, HORIZON_TERM)?.unwrap_or(HORIZON_S);
    let flow_graphs = beliefs.graphs_of(&[FLOW_GRAPH], &Within::default())?;
    let flow_graphs: Vec<&str> = flow_graphs.iter().map(String::as_str).collect();
    let sensors: Vec<String> = beliefs
        .rows(&bind(SENSORS_Q, &[("cat", Value::iri(cat.as_str()))])?, &[])?
        .iter()
        .filter_map(|r| iri(r, "sensor"))
        .collect();
    let mut keys = Vec::new();
    for sensor in sensors {
        let text = bind(
            OBSERVATION_Q,
            &[
                ("cat", Value::iri(cat.as_str())),
                ("sensor", Value::iri(sensor.as_str())),
            ],
        )?;
        let Some(found) = beliefs.rows(&text, &[])?.into_iter().next() else {
            continue;
        };
        let (Some(graph), Some(node)) = (iri(&found, "graph"), iri(&found, "node")) else {
            continue;
        };
        let mut believed = vec![graph.clone()];
        believed.extend(beliefs.revisions_of(&[&graph], OBSERVATION_GRAPH)?);
        let believed: Vec<&str> = believed.iter().map(String::as_str).collect();
        let key = beliefs
            .rows(&bind(KEY_Q, &[("node", Value::iri(node.as_str()))])?, &believed)?
            .into_iter()
            .next();
        let Some(key) = key else {
            log::debug!(
                "{}'s observation is of nothing the rules concluded: foreseen nothing",
                local_of(&sensor)
            );
            continue;
        };
        let (Some(feature), Some(property), Some(reading)) = (
            iri(&key, "feature"),
            iri(&key, "property"),
            value(&key, "value").and_then(|v| v.parse::<f64>().ok()),
        ) else {
            continue;
        };
        let text = bind(
            FLOWS_Q,
            &[
                ("flow", Value::iri(FLOW)),
                ("moves", Value::iri(MOVES)),
                ("rate_of", Value::iri(RATE)),
                ("property", Value::iri(property.as_str())),
            ],
        )?;
        let flows: Vec<Flow> = beliefs
            .rows(&text, &flow_graphs)?
            .iter()
            .filter_map(|r| {
                Some(Flow {
                    flow: iri(r, "flow")?,
                    rate: value(r, "rate")?,
                })
            })
            .collect();
        if flows.is_empty() {
            log::debug!(
                "no flow moves {} of {}: foreseen nothing",
                local_of(&property),
                local_of(&feature)
            );
            continue;
        }
        let taken = parse_instant(
            &value(&found, "taken")
                .or_else(|| value(&found, "from"))
                .unwrap_or_default(),
        )?;
        let looked = taken
            .checked_add_day_time_duration(microseconds(horizon))
            .unwrap_or(taken);
        if looked <= now {
            continue;
        }
        let since = taken.checked_sub(now).map_or(0.0, seconds_of);
        let ranges = ranges_of(beliefs, &sensor, &property)?;
        let laid = placed.is_none_or(|placed| placed(&feature, &property));
        keys.push(Key {
            sensor,
            feature,
            property,
            taken: since,
            horizon: since + horizon,
            ranges,
            flows,
            laid,
            lo: reading,
            hi: reading,
            knots: Vec::new(),
        });
    }
    //  THE KEYS THE CALLER LAYS, AND THE KEYS THEIR FLOWS READ.
    let laid: Vec<Key> = keys.iter().filter(|k| k.laid).cloned().collect();
    if laid.is_empty() {
        return Ok(None);
    }
    let keys: Vec<Key> = keys
        .into_iter()
        .filter(|k| {
            k.laid
                || laid
                    .iter()
                    .any(|l| l.flows.iter().any(|f| f.rate.contains(&k.property)))
        })
        .collect();
    log::debug!(
        "foreseeing {} key(s): {}",
        keys.len(),
        keys.iter().map(|k| local_of(&k.sensor)).collect::<Vec<_>>().join(", ")
    );
    Ok(Some(Foresight {
        origin: now,
        keys,
        t: None,
    }))
}

// --- the arithmetic, on knots ----------------------------------------------------------------------------------------

/// The summed rate of one trajectory — every contribution's lowest (`end` 0) or highest (`end` 1) — and the stops
/// ahead of it: a contribution at or past its `until` in the direction it pushes adds nothing.
fn net(said: &[Said], value: f64, end: usize) -> (f64, Vec<f64>) {
    let (mut total, mut stops) = (0.0, Vec::new());
    for (low, high, until) in said {
        let rate = if end == 0 { *low } else { *high };
        if let Some(until) = until
            && ((rate < 0.0 && value <= *until) || (rate > 0.0 && value >= *until))
        {
            continue;
        }
        total += rate;
        if let Some(until) = until
            && rate != 0.0
        {
            stops.push(*until);
        }
    }
    (total, stops)
}

/// How long until the value, moving at `rate`, reaches the nearest stop ahead of it.
fn reach(value: f64, rate: f64, stops: &[f64]) -> f64 {
    stops
        .iter()
        .filter(|_| rate != 0.0)
        .map(|s| (s - value) / rate)
        .filter(|d| *d > 1e-9)
        .fold(f64::INFINITY, f64::min)
}

/// The value `step` seconds on at `rate`, held at a stop it would pass.
fn shift(value: f64, rate: f64, step: f64, stops: &[f64]) -> f64 {
    let mut moved = value + rate * step;
    for s in stops {
        if (rate > 0.0 && value < *s && *s < moved)
            || (rate < 0.0 && moved < *s && *s < value)
            || (moved - s).abs() < 1e-12
        {
            moved = *s;
        }
    }
    moved
}

/// Every instant in `(after, before]` at which the corridor's low trajectory crosses a floor or its high one a
/// ceiling, earliest first, each to the whole second after it; `opening` says the first pair of knots opens a stretch.
fn crossings(knots: &[Knot], ranges: &[(f64, f64)], after: f64, before: f64, opening: bool) -> Vec<f64> {
    let mut out: Vec<f64> = Vec::new();
    for (n, pair) in knots.windows(2).enumerate() {
        let ((t0, lo0, hi0), (t1, lo1, hi1)) = (pair[0], pair[1]);
        for c in crossed((t0, lo0, hi0), (t1, lo1, hi1), ranges, opening && n == 0) {
            if after < c && c <= before {
                out.push(c);
            }
        }
    }
    out.sort_by(f64::total_cmp);
    out.dedup();
    out
}

/// Every instant in one straight segment at which the low trajectory crosses a floor or the high one a ceiling, to
/// the whole second after it. In the segment OPENING a stretch, a trajectory standing on the bound has crossed it.
fn crossed(from: Knot, to: Knot, ranges: &[(f64, f64)], opening: bool) -> Vec<f64> {
    let ((t0, lo0, hi0), (t1, lo1, hi1)) = (from, to);
    let mut out = Vec::new();
    for (low, high) in ranges {
        let (low, high) = (*low, *high);
        if lo1 != lo0 && (if opening { lo0 <= low } else { lo0 < low }) != (lo1 < low) {
            out.push(ceil(t0 + (low - lo0) / (lo1 - lo0) * (t1 - t0)));
        }
        if hi1 != hi0 && (if opening { hi0 >= high } else { hi0 > high }) != (hi1 > high) {
            out.push(ceil(t0 + (high - hi0) / (hi1 - hi0) * (t1 - t0)));
        }
    }
    out
}

/// The number laid for the stretch from `begins` to `closes`, and the instant it is read at: the last instant of the
/// stretch whose number, as written, lies on the stretch's side.
fn number_on_its_side(knots: &[Knot], ranges: &[(f64, f64)], begins: f64, closes: f64) -> (f64, f64) {
    let sides = sides_of(knots, ranges, (begins + closes) / 2.0);
    let (mut at, mut number) = (closes, 0.0);
    for candidate in [
        closes,
        closes - EDGE_S.min((closes - begins) / 2.0),
        (begins + closes) / 2.0,
    ] {
        at = candidate;
        let (lo, hi) = at_of(knots, at);
        number = round_to(
            if sides.contains(&1) && !sides.contains(&-1) {
                hi
            } else {
                lo
            },
            PLACES,
        );
        let read: Vec<i32> = ranges.iter().map(|(low, high)| side(*low, *high, number)).collect();
        if read == sides {
            break;
        }
    }
    (at, number)
}

/// The corridor's worst side of every range at `elapsed`.
fn sides_of(knots: &[Knot], ranges: &[(f64, f64)], elapsed: f64) -> Vec<i32> {
    let (lo, hi) = at_of(knots, elapsed);
    ranges
        .iter()
        .map(|(low, high)| {
            if side(*low, *high, lo) < 0 {
                -1
            } else if side(*low, *high, hi) > 0 {
                1
            } else {
                0
            }
        })
        .collect()
}

/// The two trajectories at `elapsed`, straight between the knots.
fn at_of(knots: &[Knot], elapsed: f64) -> (f64, f64) {
    for pair in knots.windows(2) {
        let ((t0, lo0, hi0), (t1, lo1, hi1)) = (pair[0], pair[1]);
        if t0 <= elapsed && elapsed <= t1 {
            let f = if t1 == t0 { 0.0 } else { (elapsed - t0) / (t1 - t0) };
            return (lo0 + (lo1 - lo0) * f, hi0 + (hi1 - hi0) * f);
        }
    }
    knots.last().map_or((0.0, 0.0), |k| (k.1, k.2))
}

/// The number a key stands at for the flows: the trajectory its worst side is read from, or the corridor's middle.
fn worst(key: &Key) -> f64 {
    let sides: Vec<i32> = key
        .ranges
        .iter()
        .map(|(low, high)| {
            if side(*low, *high, key.lo) < 0 {
                -1
            } else if side(*low, *high, key.hi) > 0 {
                1
            } else {
                0
            }
        })
        .collect();
    if sides.contains(&-1) {
        key.lo
    } else if sides.contains(&1) {
        key.hi
    } else {
        (key.lo + key.hi) / 2.0
    }
}

/// A number as the Python writer spells it: six places, trailing noughts cut, a whole number keeping one.
fn spelled(value: f64) -> String {
    let fixed = format!("{:.prec$}", round_to(value, PLACES) + 0.0, prec = PLACES as usize);
    let cut = fixed.trim_end_matches('0');
    if cut.ends_with('.') {
        format!("{cut}0")
    } else {
        cut.to_string()
    }
}

/// The predicted observation of `key`: a node of its own, one per key as a fluent is, with the key's feature,
/// property and sensor, the `value` and the instant — never the percept (#944).
fn observation(key: &Key, value: f64, at: DateTime) -> Vec<Triple> {
    let subject = NamedNode::new_unchecked(predicted_of(&key.feature, &key.property));
    let node = |iri: &str| NamedNode::new_unchecked(iri);
    let term = |iri: &str| -> Term { node(iri).into() };
    vec![
        Triple::new(subject.clone(), node(RDF_TYPE), term(&format!("{SOSA}Observation"))),
        Triple::new(subject.clone(), node(FEATURE), term(&key.feature)),
        Triple::new(subject.clone(), node(PROPERTY), term(&key.property)),
        Triple::new(subject.clone(), node(&format!("{SOSA}madeBySensor")), term(&key.sensor)),
        Triple::new(
            subject.clone(),
            node(RESULT),
            Literal::new_typed_literal(spelled(value), xsd::DECIMAL),
        ),
        Triple::new(
            subject,
            node(&format!("{SOSA}resultTime")),
            Literal::new_typed_literal(isoformat(at), xsd::DATE_TIME),
        ),
    ]
}

#[cfg(test)]
mod tests {
    //! `foresee`, one case per file, held as `agent/prediction/tests/test_foresee.py` holds it to the knots the
    //! integration answers: advanced from noon to the horizon as the planner advances it, reading the case's beliefs
    //! holding at each instant — every crossing of a range bound with the number laid on the new side, and the hour's
    //! end where the key moved. No forecast is written (#1000).

    use std::path::{Path, PathBuf};

    use orexis::clock::seconds;
    use orexis::ontology::{BELIEF, FORECAST, RECORD};
    use orexis::snapshots::{ME, cases_in, now, stand_in};

    use super::*;

    const PROBE: &str = "http://example.org/test#probe";
    const MOISTURE: &str = "http://example.org/test#moisture";

    fn cases() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/foresee")
    }

    /// WHERE THE PROBE'S KEY CROSSES A BOUND, in minutes past noon, with the minutes a crossing may be placed within.
    fn expected(case: &str) -> Option<Vec<(f64, f64)>> {
        Some(match case {
            "a_slow_dryer_crosses_the_floor_after_seven_hours" => vec![(432.0, 0.02), (662.4, 0.02)],
            "a_fast_dryer_crosses_both_floors_within_two_hours" => vec![(54.0, 0.02), (82.8, 0.02)],
            "a_reading_already_below_crosses_only_the_survival_floor" => vec![(86.4, 0.02)],
            "a_key_no_flow_moves_is_predicted_nothing" => return None,
            "two_flows_moving_one_property_add" => vec![(36.0, 0.02), (55.2, 0.02)],
            "a_forecast_shower_lifts_the_reading_back_inside" => {
                vec![(28.8, 0.02), (144.0, 0.02), (316.8, 0.02), (432.0, 0.02)]
            }
            "a_forecast_range_opens_a_corridor_on_its_dry_side" => vec![(28.8, 0.02), (144.0, 0.02)],
            "a_committed_dose_lifts_the_reading_over_its_window" => vec![(61.2, 0.02), (90.0, 0.02)],
            "a_key_is_predicted_from_another_keys_prediction" => vec![(54.0, 0.02)],
            other => panic!("{other}: no crossings are said for it"),
        })
    }

    fn known(store: &Store, at: DateTime) -> Result<Vec<String>, Error> {
        store.graphs_of(
            &[BELIEF, RECORD],
            &Within {
                at: Some(at),
                until: Some(at),
                ..Within::default()
            },
        )
    }

    /// The number laid per sensor in a knot's predicted observations.
    fn result_of(arrival: &[Triple]) -> Vec<(String, f64)> {
        let mut out = Vec::new();
        for t in arrival
            .iter()
            .filter(|t| t.predicate.as_str().ends_with("madeBySensor"))
        {
            let sensor = match &t.object {
                Term::NamedNode(n) => n.as_str().to_string(),
                _ => continue,
            };
            let number = arrival
                .iter()
                .find(|r| r.subject == t.subject && r.predicate.as_str().ends_with("hasSimpleResult"))
                .and_then(|r| match &r.object {
                    Term::Literal(l) => l.value().parse().ok(),
                    _ => None,
                });
            if let Some(number) = number {
                out.push((sensor, number));
            }
        }
        out
    }

    /// Every knot the integration answers from `now` to its horizon, as (minutes past `now`, the number laid per
    /// sensor), advanced as the planner advances it.
    fn every_knot(store: &Store, foresight: &mut Foresight, from: DateTime) -> Vec<(f64, Vec<(String, f64)>)> {
        let mut out = Vec::new();
        let mut t = from;
        let until = foresight.horizon();
        let mut graphs_at = |at: DateTime| known(store, at);
        while let Some((when, arrival)) = foresight.advance(store, t, until, &mut graphs_at).unwrap() {
            let minutes = when.checked_sub(from).map_or(0.0, seconds_of) / 60.0;
            out.push((minutes, result_of(&arrival)));
            t = when;
        }
        out
    }

    fn sides(ranges: &[(f64, f64)], number: f64) -> Vec<i32> {
        ranges.iter().map(|(low, high)| side(*low, *high, number)).collect()
    }

    fn reading(store: &Store) -> f64 {
        let percepts = store.graphs_of(&[OBSERVATION_GRAPH], &Within::default()).unwrap();
        let percepts: Vec<&str> = percepts.iter().map(String::as_str).collect();
        let found = store
            .rows(
                &format!("SELECT ?v WHERE {{ ?o sosa:madeBySensor <{PROBE}> ; sosa:hasSimpleResult ?v }}"),
                &percepts,
            )
            .unwrap();
        assert_eq!(found.len(), 1);
        value(&found[0], "v").unwrap().parse().unwrap()
    }

    #[test]
    fn foresee_answers_the_crossings_the_case_says_and_a_knot_an_hour_at_most_apart() {
        let all = cases_in(&cases());
        assert!(all.len() >= 3);
        for case in all {
            let stem = case.file_stem().unwrap().to_string_lossy().into_owned();
            let store = stand_in(&case);
            let foresight = foresee(&store, now(), None).unwrap();
            let Some(table) = expected(&stem) else {
                if let Some(mut foresight) = foresight {
                    assert!(every_knot(&store, &mut foresight, now()).is_empty(), "{stem}");
                }
                continue;
            };
            let mut foresight = foresight.unwrap_or_else(|| panic!("{stem}: nothing foreseen"));
            let every = every_knot(&store, &mut foresight, now());
            let knots: Vec<(f64, f64)> = every
                .iter()
                .filter_map(|(m, laid)| laid.iter().find(|(s, _)| s == PROBE).map(|(_, n)| (*m, *n)))
                .collect();
            let ranges = ranges_of(&store, PROBE, MOISTURE).unwrap();
            let mut said = vec![sides(&ranges, reading(&store))];
            said.extend(knots.iter().map(|(_, n)| sides(&ranges, *n)));
            let crossings: Vec<f64> = knots
                .iter()
                .zip(said.windows(2))
                .filter(|(_, pair)| pair[0] != pair[1])
                .map(|((m, _), _)| *m)
                .collect();
            assert_eq!(crossings.len(), table.len(), "{stem}: {knots:?} {crossings:?}");
            for (got, (minute, within)) in crossings.iter().zip(&table) {
                assert!(
                    (got - minute).abs() <= within + 1e-9,
                    "{stem}: {crossings:?} against {table:?}"
                );
            }
            for pair in every.windows(2) {
                assert!(pair[1].0 - pair[0].0 <= SEGMENT_S / 60.0 + 1e-9, "{stem}: {every:?}");
            }
            foresight.finish(&store).unwrap();
            assert!(
                store.quads(NUMBERS).unwrap().is_empty(),
                "{stem}: the numbers go with the integration"
            );
        }
    }

    #[test]
    fn two_keys_advance_together_and_one_reads_the_other_as_it_stands() {
        let store = stand_in(&cases().join("a_key_is_predicted_from_another_keys_prediction.trig"));
        let mut foresight = foresee(&store, now(), None).unwrap().unwrap();
        let mut sensors: Vec<String> = foresight.keys.iter().map(|k| local_of(&k.sensor)).collect();
        sensors.sort();
        assert_eq!(sensors, ["hygrometer", "probe"]);
        let horizon = foresight.horizon();
        let mut graphs_at = |at: DateTime| known(&store, at);
        let first = foresight
            .advance(&store, now(), horizon, &mut graphs_at)
            .unwrap()
            .unwrap();
        let minutes = first.0.checked_sub(now()).map_or(0.0, seconds_of);
        assert!((minutes - 54.0 * 60.0).abs() <= 1.0, "{minutes}");
        let second = foresight
            .advance(&store, first.0, horizon, &mut graphs_at)
            .unwrap()
            .unwrap();
        let at = second.0.checked_sub(now()).map_or(0.0, seconds_of);
        assert!((at - 3601.0).abs() <= 1.0, "the air at its ceiling: {at}");
        let numbers = result_of(&second.1);
        assert_eq!(numbers.len(), 1);
        assert!(numbers[0].1 >= 0.9, "{numbers:?}");
        assert!(
            store.graphs_of(&[FORECAST], &Within::default()).unwrap().is_empty(),
            "nothing is written"
        );
    }

    #[test]
    fn the_horizon_is_the_agents_stance_where_its_self_graph_states_one() {
        let store = stand_in(&cases().join("a_slow_dryer_crosses_the_floor_after_seven_hours.trig"));
        let cat = store.catalogue().unwrap().unwrap();
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <urn:test:self> {{ <{ME}> a orexis:Self ; prediction:horizonS 28800 }}
               GRAPH <{cat}> {{ <urn:test:self> a orexis:SelfGraph , orexis:BeliefGraph , orexis:Graph ;
                                orexis:ownedBy <{ME}> }} }}"
            ))
            .unwrap();
        let mut foresight = foresee(&store, now(), None).unwrap().unwrap();
        assert_eq!(
            foresight.horizon(),
            now().checked_add_day_time_duration(seconds(8.0 * 3600.0)).unwrap()
        );
        let knots: Vec<f64> = every_knot(&store, &mut foresight, now())
            .into_iter()
            .filter(|(_, laid)| laid.iter().any(|(s, _)| s == PROBE))
            .map(|(m, _)| m)
            .collect();
        assert!(!knots.is_empty() && knots.iter().all(|m| *m <= 480.0), "{knots:?}");
        assert!(knots.iter().any(|m| (m - 432.0).abs() <= 0.02), "{knots:?}");
        assert!(
            !knots.iter().any(|m| (m - 662.4).abs() <= 0.02),
            "the survival floor lies past the horizon"
        );
    }
}
