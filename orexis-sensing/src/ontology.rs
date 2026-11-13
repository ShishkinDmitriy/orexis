//! THE WORDS THE SENSING LAYER READS AND WRITES, as `agent/sensing/ontology.py` names them, and the names it spells
//! for eyes. Every other word of this layer is spoken by a query text, under its prefix.
//!
//! THE NAMES ARE FOR EYES: a percept's node and graph and a forecast's are spelled here for the writer, from the one
//! identifier a process is handed, the sensor and the instant of the reading; every reader asks the catalogue by
//! class and by pattern.

use std::collections::BTreeMap;
use std::sync::LazyLock;

use oxigraph::io::{RdfFormat, RdfParser};
use oxigraph::model::{NamedOrBlankNode, Quad, Term};
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::clock::isoformat;
use orexis::ontology::GRAPH_PREFIX;

pub const SENSING: &str = "http://example.org/orexis/sensing#";
/// The graph a percept is kept in.
pub const OBSERVATION_GRAPH: &str = "http://example.org/orexis/sensing#ObservationGraph";
/// The graph a percept sensing has done reading is filed in, and its revisions with it.
pub const PAST_OBSERVATION_GRAPH: &str = "http://example.org/orexis/sensing#PastObservationGraph";
/// Percepts said for belief to revise, and belief's words they are said in.
pub const PERCEIVED: &str = "http://example.org/orexis/sensing#Perceived";
pub const REVISES: &str = "http://example.org/orexis/belief#revises";
pub const INTO: &str = "http://example.org/orexis/belief#into";
/// What sensing does once a percept is revised, and what starts it: belief's revision pass, in belief's words.
pub const OBSERVING: &str = "http://example.org/orexis/sensing#Observing";
pub const OBSERVING_TRIGGER: &str = "http://example.org/orexis/sensing#ObservingTrigger";
pub const REVISED_SOURCE: &str = "http://example.org/orexis/belief#revised";
/// A time a sensor fell silent, kept for good.
pub const SILENCE_GRAPH: &str = "http://example.org/orexis/sensing#SilenceGraph";
/// An observer role's limits: cadences, and readings.
pub const SILENT_AFTER_TERM: &str = "http://example.org/orexis/sensing#silentAfter";
pub const STUCK_AFTER_TERM: &str = "http://example.org/orexis/sensing#stuckAfter";
/// The codec that ships.
pub const JSON_CODEC: &str = "http://example.org/orexis/sensing#Json";

/// THIS LAYER'S ONTOLOGY, where the observer shape states what holds of a limit no role states.
const ONTOLOGY: &str = include_str!("../ontology.ttl");

const SH: &str = "http://www.w3.org/ns/shacl#";

/// Every limit the observer shape states a default of, read off the ontology once.
static DEFAULTS: LazyLock<Result<BTreeMap<String, Vec<i64>>, String>> = LazyLock::new(defaults);

fn defaults() -> Result<BTreeMap<String, Vec<i64>>, String> {
    let quads: Vec<Quad> = RdfParser::from_format(RdfFormat::Turtle)
        .with_base_iri("file:///agent/sensing/ontology.ttl")
        .map_err(|e| e.to_string())?
        .for_slice(ONTOLOGY.as_bytes())
        .collect::<Result<_, _>>()
        .map_err(|e| e.to_string())?;
    let objects = |s: &NamedOrBlankNode, p: &str| -> Vec<Term> {
        quads
            .iter()
            .filter(|q| &q.subject == s && q.predicate.as_str() == p)
            .map(|q| q.object.clone())
            .collect()
    };
    let mut out: BTreeMap<String, Vec<i64>> = BTreeMap::new();
    let shapes = quads
        .iter()
        .filter(|q| {
            q.predicate.as_str() == format!("{SH}targetClass") && q.object.to_string() == format!("<{SENSING}Observer>")
        })
        .map(|q| q.subject.clone());
    for shape in shapes {
        for property in objects(&shape, &format!("{SH}property")) {
            let node: NamedOrBlankNode = match property {
                Term::NamedNode(n) => n.into(),
                Term::BlankNode(b) => b.into(),
                _ => continue,
            };
            for path in objects(&node, &format!("{SH}path")) {
                let Term::NamedNode(path) = path else { continue };
                for default in objects(&node, &format!("{SH}defaultValue")) {
                    if let Term::Literal(l) = default
                        && let Ok(n) = l.value().parse::<f64>()
                    {
                        out.entry(path.as_str().to_string()).or_default().push(n as i64);
                    }
                }
            }
        }
    }
    Ok(out)
}

/// What holds of `limit` — `sensing:silentAfter`, `sensing:stuckAfter` — where no observer role states it: the
/// observer shape's `sh:defaultValue`, read off this layer's ontology, the one place the figure lives. Refused where
/// the ontology states none or several, since a limit with no figure is a package shipped broken.
pub fn default_of(limit: &str) -> Result<i64, Error> {
    let found = DEFAULTS
        .as_ref()
        .map_err(|e| Error::Document(format!("sensing's ontology: {e}")))?;
    let mut figures = found.get(limit).cloned().unwrap_or_default();
    figures.sort();
    figures.dedup();
    match figures.as_slice() {
        [one] => Ok(*one),
        _ => Err(Error::Document(format!(
            "sensing's ontology states {} defaults for {limit}, and one is the limit",
            figures.len()
        ))),
    }
}

/// The local name of a term, safe to paste into an IRI.
pub fn slug(iri: &str) -> String {
    let trimmed = iri.trim_end_matches(['#', '/']);
    let local = trimmed.rsplit(['#', '/']).next().unwrap_or(trimmed);
    local
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() || c == '_' { c } else { '_' })
        .collect()
}

/// The date and time of `at`, as `strftime('%Y%m%dT%H%M%S')` spells it, and its microseconds.
fn parts(at: DateTime) -> (String, u32) {
    let iso = isoformat(at);
    let (date, time) = iso.split_once('T').unwrap_or((&iso, ""));
    let clock = &time[..8.min(time.len())];
    let micro = time
        .get(8..)
        .and_then(|rest| rest.strip_prefix('.'))
        .map(|rest| rest.chars().take_while(char::is_ascii_digit).collect::<String>())
        .and_then(|digits| digits.parse().ok())
        .unwrap_or(0);
    (format!("{}T{}", date.replace('-', ""), clock.replace(':', "")), micro)
}

/// An instant as a name's part: to the second, and to the microsecond where it has one.
fn stamp(at: DateTime) -> String {
    let (whole, micro) = parts(at);
    if micro > 0 {
        format!("{whole}{micro:06}Z")
    } else {
        format!("{whole}Z")
    }
}

fn nth(n: usize) -> String {
    if n > 1 { format!("_{n}") } else { String::new() }
}

/// The node of the reading `sensor` made at `at` — the `n`th of that instant — named off the sensor.
pub fn percept_of(sensor: &str, at: DateTime, n: usize) -> String {
    format!("{sensor}.{}{}", stamp(at), nth(n))
}

/// The node of the stretch of `sensor`'s forecast that starts at `starts`, named off the sensor as a percept is.
pub fn forecast_of(sensor: &str, starts: DateTime) -> String {
    format!("{sensor}.{}", stamp(starts))
}

/// Where the reading `sensor` made at `at` is kept — the `n`th of that instant.
pub fn percept_graph(agent: &str, sensor: &str, at: DateTime, n: usize) -> String {
    format!(
        "{GRAPH_PREFIX}observed/{agent}/{}_{}{}",
        slug(sensor),
        stamp(at),
        nth(n)
    )
}

/// Where one stretch of a sensor's forecast stands, named by the sensor and the stretch's start.
pub fn forecast_graph(agent: &str, sensor: &str, starts: DateTime) -> String {
    format!("{GRAPH_PREFIX}forecast/{agent}/{}_{}Z", slug(sensor), parts(starts).0)
}

/// Where the time `sensor` fell silent at `since` is kept, named by the sensor and that instant.
pub fn silence_graph(agent: &str, sensor: &str, since: DateTime) -> String {
    format!("{GRAPH_PREFIX}silence/{agent}/{}_{}", slug(sensor), stamp(since))
}

#[cfg(test)]
mod tests {
    use orexis::clock::instant;

    use super::*;

    #[test]
    fn the_observer_shape_states_one_default_of_each_limit() {
        assert_eq!(default_of(SILENT_AFTER_TERM).unwrap(), 3);
        assert_eq!(default_of(STUCK_AFTER_TERM).unwrap(), 6);
        assert!(default_of(&format!("{SENSING}nothing")).is_err());
    }

    #[test]
    fn a_name_is_the_sensor_and_the_instant_to_the_microsecond_where_it_has_one() {
        let at = instant("2026-01-01T11:59:35Z").unwrap();
        assert_eq!(percept_of("urn:t#probe", at, 1), "urn:t#probe.20260101T115935Z");
        assert_eq!(percept_of("urn:t#probe", at, 2), "urn:t#probe.20260101T115935Z_2");
        let fine = instant("2026-01-01T12:00:00.25Z").unwrap();
        assert_eq!(
            percept_graph("keeper", "http://example.org/test#probe", fine, 1),
            "http://example.org/orexis/graph/observed/keeper/probe_20260101T120000250000Z"
        );
        assert_eq!(
            forecast_graph("keeper", "http://example.org/test#weather", fine),
            "http://example.org/orexis/graph/forecast/keeper/weather_20260101T120000Z"
        );
    }
}
