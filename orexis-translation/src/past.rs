//! WHAT HAPPENED TO THE AGENT, as `agent/translation/past.py` reads it for a chat that reads `orexis:Event`: its
//! journal's entries, its series' points and its metrics' windows — and the three tools that read them, `journal`,
//! `series` and `metrics` (knowledge/domain/translation/translator.md).
//!
//! **WHAT HOLDS NOW AND WHAT HAPPENED ARE TWO READS**: the store is the present, the journal and the series are the
//! record. **READ IN PLACE, NEVER COPIED**: a SELECT or an ASK runs over the journal where it is, refused where it holds
//! a `SERVICE` or a `FROM`; the series and the metrics are asked in Flux the tool writes from the fields the model
//! fills, every field checked before it is written into the text — the model writes no Flux.

use std::collections::BTreeMap;

use oxigraph::store::Store as Engine;
use regex::Regex;
use serde_json::{Value as Json, json};

use orexis::clock::{instant, isoformat};
use orexis::series::Reader;

use crate::readable::{Prefixes, ROWS, refusal, run};

pub const JOURNAL: &str = "journal";
pub const SERIES: &str = "series";
pub const METRICS: &str = "metrics";
/// HOW FAR BACK THE SERIES IS READ where the model says nothing, and how far a listing looks for the latest points.
pub const SINCE: &str = "-24h";
pub const LISTED_SINCE: &str = "-30d";
const FNS: [&str; 6] = ["mean", "min", "max", "last", "sum", "count"];
const TAGS: [&str; 3] = ["sensor", "feature", "defective"];
const FIELDS: [&str; 6] = ["measurement", "sensor", "start", "stop", "every", "fn"];
const METRIC_FIELDS: [&str; 7] = ["measurement", "field", "by", "start", "stop", "every", "fn"];

/// What happened to one agent, as a chat may read it: its journal's store, its history and metrics readers, each
/// absent where the agent keeps none, and the prefixes the chat's rows are written with.
#[derive(Clone)]
pub struct Past {
    pub journal: Option<Engine>,
    pub history: Option<Reader>,
    pub metrics: Option<Reader>,
    pub prefixes: Prefixes,
}

fn duration(text: &str) -> bool {
    Regex::new(r"^-?[0-9]+(?:ns|us|ms|s|m|h|d|w|mo|y)$")
        .expect("a pattern")
        .is_match(text)
}

fn name(text: &str) -> bool {
    Regex::new(r"^[A-Za-z_][A-Za-z0-9_]*$")
        .expect("a pattern")
        .is_match(text)
}

/// A string as Python's `json.dumps` writes it: quoted, escaped, every character past ASCII as `\uXXXX`.
pub fn dumps(text: &str) -> String {
    let mut out = String::from("\"");
    for unit in text.encode_utf16() {
        match unit {
            0x22 => out.push_str("\\\""),
            0x5C => out.push_str("\\\\"),
            0x0A => out.push_str("\\n"),
            0x0D => out.push_str("\\r"),
            0x09 => out.push_str("\\t"),
            0x08 => out.push_str("\\b"),
            0x0C => out.push_str("\\f"),
            u if !(0x20..0x7F).contains(&u) => out.push_str(&format!("\\u{u:04x}")),
            u => out.push(char::from(u as u8)),
        }
    }
    out.push('"');
    out
}

/// A stretch's end as Flux says it: a duration back from now, or an ISO instant.
fn flux_instant(text: &str) -> Result<String, String> {
    if duration(text) {
        return Ok(if text.starts_with('-') {
            text.to_string()
        } else {
            format!("-{text}")
        });
    }
    match instant(&text.replace('Z', "+00:00")) {
        Ok(at) => Ok(format!("time(v: {})", dumps(&isoformat(at)))),
        Err(_) => Err(format!(
            "a stretch's end is a duration, such as -24h, or an ISO instant: '{text}'"
        )),
    }
}

fn checked(fname: &str, every: Option<&str>) -> Result<(), String> {
    if !FNS.contains(&fname) {
        return Err(format!("fn is one of {}", FNS.join(", ")));
    }
    if let Some(every) = every
        && !duration(every.trim_start_matches('-'))
    {
        return Err(format!("every is a duration, such as 1h: '{every}'"));
    }
    Ok(())
}

/// The one read of the series the fields describe, every field checked before it is written into the text.
pub fn flux(
    bucket: &str,
    measurement: Option<&str>,
    sensor: Option<&str>,
    start: &str,
    stop: Option<&str>,
    every: Option<&str>,
    fname: &str,
) -> Result<String, String> {
    checked(fname, every)?;
    let stretch = format!(
        "start: {}{}",
        flux_instant(start)?,
        stop.map(|s| flux_instant(s).map(|v| format!(", stop: {v}")))
            .transpose()?
            .unwrap_or_default()
    );
    let head = format!("from(bucket: {})\n  |> range({stretch})\n", dumps(bucket));
    let Some(measurement) = measurement else {
        return Ok(head
            + "  |> filter(fn: (r) => r._field == \"value\")\n  |> group(columns: [\"_measurement\", \"sensor\"])\n  |> last()\n  |> group()\n"
            + &format!("  |> limit(n: {ROWS})"));
    };
    let mut text = head
        + &format!(
            "  |> filter(fn: (r) => r._measurement == {} and r._field == \"value\")\n",
            dumps(measurement)
        );
    if let Some(sensor) = sensor {
        text += &format!("  |> filter(fn: (r) => r.sensor == {})\n", dumps(sensor));
    }
    if let Some(every) = every {
        text += &format!(
            "  |> aggregateWindow(every: {}, fn: {fname}, createEmpty: false)\n",
            every.trim_start_matches('-')
        );
    }
    Ok(text
        + &format!("  |> group()\n  |> sort(columns: [\"_time\"], desc: true)\n  |> limit(n: {ROWS})\n")
        + "  |> sort(columns: [\"_time\"])")
}

/// The one read of the metrics the fields describe, every field checked before it is written into the text.
#[allow(clippy::too_many_arguments)]
pub fn metric_flux(
    bucket: &str,
    measurement: Option<&str>,
    field: Option<&str>,
    by: Option<&str>,
    start: &str,
    stop: Option<&str>,
    every: Option<&str>,
    fname: &str,
) -> Result<String, String> {
    checked(fname, every)?;
    for (what, n) in [("field", field), ("by", by)] {
        if let Some(n) = n
            && !name(n)
        {
            return Err(format!("{what} is a name, such as output_tokens_sum: '{n}'"));
        }
    }
    let stretch = format!(
        "start: {}{}",
        flux_instant(start)?,
        stop.map(|s| flux_instant(s).map(|v| format!(", stop: {v}")))
            .transpose()?
            .unwrap_or_default()
    );
    let head = format!("from(bucket: {})\n  |> range({stretch})\n", dumps(bucket));
    let Some(measurement) = measurement else {
        return Ok(head
            + "  |> keep(columns: [\"_measurement\", \"_field\"])\n  |> group(columns: [\"_measurement\"])\n"
            + "  |> distinct(column: \"_field\")\n"
            + "  |> reduce(identity: {fields: \"\"}, fn: (r, accumulator) => ({fields: accumulator.fields + \" \" + r._value}))\n"
            + &format!("  |> group()\n  |> limit(n: {ROWS})"));
    };
    let Some(field) = field else {
        return Err(
            "name the field to aggregate, count or a `<value>_sum`; leave the measurement out to list them".into(),
        );
    };
    let groups = match by {
        Some(by) => format!("[{}]", dumps(by)),
        None => "[]".into(),
    };
    let text = head
        + &format!(
            "  |> filter(fn: (r) => r._measurement == {} and r._field == {})\n  |> group(columns: {groups})\n",
            dumps(measurement),
            dumps(field)
        );
    Ok(match every {
        None => text + &format!("  |> {fname}()\n  |> limit(n: {ROWS})"),
        Some(every) => {
            text + &format!(
                "  |> aggregateWindow(every: {}, fn: {fname}, createEmpty: false)\n  |> sort(columns: [\"_time\"], desc: true)\n  |> limit(n: {ROWS})\n  |> sort(columns: [\"_time\"])",
                every.trim_start_matches('-')
            )
        }
    })
}

/// The fields the model filled that a tool reads, each as text, none where it filled nothing.
fn filled<'j>(inputs: &'j Json, names: &[&str]) -> BTreeMap<&'j str, String> {
    let mut out = BTreeMap::new();
    if let Json::Object(map) = inputs {
        for (k, v) in map {
            if !names.contains(&k.as_str()) {
                continue;
            }
            let text = match v {
                Json::Null => continue,
                Json::String(s) if s.is_empty() => continue,
                Json::String(s) => s.clone(),
                other => other.to_string(),
            };
            out.insert(k.as_str(), text);
        }
    }
    out
}

impl Past {
    /// The tools what happened is read with, each answered by `call`: one per record the agent keeps.
    pub fn tools(&self) -> Vec<Json> {
        let mut out = Vec::new();
        if self.journal.is_some() {
            out.push(json!({"name": JOURNAL, "description": format!("What happened to the agent, as its journal kept it: a \
SPARQL SELECT or ASK over its entries. Each is an event at its prov:atTime — `?e a ?class ; prov:atTime ?t`, its class \
its package's and its fields in that package's words — or a line of its log, orexis:LogRecord with orexis:logger, \
orexis:level and orexis:message, kept for the last minutes and for good before an incident, which says `a \
orexis:Incident`. Ask the newest first, ORDER BY DESC(?t) with a LIMIT. The query tool's prefixes are declared. Write no \
SERVICE or FROM. At most {ROWS} rows come back."),
                "input_schema": {"type": "object", "properties": {"sparql": {"type": "string"}}, "required": ["sparql"]}}));
        }
        if self.history.is_some() {
            out.push(json!({"name": SERIES, "description": format!("How the agent's readings went over time, from its own series: \
the points of one measurement, the observed property's local name (SoilMoisture, AirTemperature), of one sensor where \
named, its local name. Leave the measurement out to list each measurement and sensor with its latest point over the last \
{}. A stretch starts and stops at a duration back from now (-24h, -7d) or an ISO instant, {SINCE} where none is given; \
`every` and `fn` aggregate it per window (1h, mean). The newest {ROWS} points come back, oldest first.",
                LISTED_SINCE.trim_start_matches('-')),
                "input_schema": {"type": "object", "properties": {
                    "measurement": {"type": "string"}, "sensor": {"type": "string"},
                    "start": {"type": "string"}, "stop": {"type": "string"},
                    "every": {"type": "string"}, "fn": {"type": "string", "enum": FNS}}}}));
        }
        if self.metrics.is_some() {
            out.push(json!({"name": METRICS, "description": format!("How the agent itself has been doing, from its own metrics: a \
window a minute per measurement and tags, each field `count` (how many happened), `<value>_sum`, `<value>_mean` and \
`<value>_max`. `translated` is each use of its model, tagged act, outcome and model, its tokens by the API's names \
(input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens) and its requests and duration_s; \
`pass`, `planner`, `revise` and `received` are its own work. Leave the measurement out to list each one with its fields \
over the last {}. Name a measurement and a field to aggregate it with fn (sum where none is given) over a stretch, {SINCE} \
where none is given — one figure, or one per `every` window (1h, 1d), and one per value of the tag `by` names. A total is \
the sum of a `_sum` field or of `count`, never of a mean or a max.", LISTED_SINCE.trim_start_matches('-')),
                "input_schema": {"type": "object", "properties": {
                    "measurement": {"type": "string"}, "field": {"type": "string"}, "by": {"type": "string"},
                    "start": {"type": "string"}, "stop": {"type": "string"},
                    "every": {"type": "string"}, "fn": {"type": "string", "enum": FNS}}}}));
        }
        out
    }

    /// What one of the tools answers, or None where `name` is neither.
    pub fn call(&self, tool: &str, inputs: &Json) -> Option<String> {
        match tool {
            JOURNAL => self
                .journal
                .as_ref()
                .map(|j| self.journaled(j, inputs.get("sparql").and_then(Json::as_str).unwrap_or_default())),
            SERIES => self.history.as_ref().map(|h| self.points(h, &filled(inputs, &FIELDS))),
            METRICS => self
                .metrics
                .as_ref()
                .map(|m| self.windows(m, &filled(inputs, &METRIC_FIELDS))),
            _ => None,
        }
    }

    /// The model's SELECT or ASK over the journal's entries, their union; the reason, where it is refused.
    fn journaled(&self, journal: &Engine, text: &str) -> String {
        if let Some(why) = refusal(text, &self.prefixes) {
            return format!("refused: {why}");
        }
        match run(journal, text, &self.prefixes, None, None) {
            Ok(answer) => answer,
            Err(e) => format!("the engine would not run it: {e}"),
        }
    }

    /// The series' points the fields ask for, a line each; the reason, where a field will not do.
    fn points(&self, history: &Reader, f: &BTreeMap<&str, String>) -> String {
        let measurement = f.get("measurement").map(String::as_str);
        let start = f
            .get("start")
            .cloned()
            .unwrap_or_else(|| (if measurement.is_some() { SINCE } else { LISTED_SINCE }).into());
        let text = match flux(
            &history.bucket,
            measurement,
            f.get("sensor").map(String::as_str),
            &start,
            f.get("stop").map(String::as_str),
            f.get("every").map(String::as_str),
            f.get("fn").map_or("mean", String::as_str),
        ) {
            Ok(t) => t,
            Err(why) => return format!("refused: {why}"),
        };
        let found = match history.read(&text) {
            Ok(found) => found,
            Err(why) => return why,
        };
        let keys: Vec<&str> = ["_measurement"]
            .into_iter()
            .chain(TAGS)
            .chain(["_time", "_value"])
            .collect();
        let lines: Vec<String> = found
            .iter()
            .map(|r| {
                keys.iter()
                    .filter_map(|k| {
                        r.get(*k)
                            .filter(|v| !v.is_empty())
                            .map(|v| format!("{}: {v}", k.trim_start_matches('_')))
                    })
                    .collect::<Vec<_>>()
                    .join(", ")
            })
            .collect();
        if lines.is_empty() {
            "(no points)".into()
        } else {
            lines.join("\n")
        }
    }

    /// The metrics the fields ask for, a line each; the reason, where a field will not do.
    fn windows(&self, metrics: &Reader, f: &BTreeMap<&str, String>) -> String {
        let measurement = f.get("measurement").map(String::as_str);
        let by = f.get("by").map(String::as_str);
        let start = f
            .get("start")
            .cloned()
            .unwrap_or_else(|| (if measurement.is_some() { SINCE } else { LISTED_SINCE }).into());
        let text = match metric_flux(
            &metrics.bucket,
            measurement,
            f.get("field").map(String::as_str),
            by,
            &start,
            f.get("stop").map(String::as_str),
            f.get("every").map(String::as_str),
            f.get("fn").map_or("sum", String::as_str),
        ) {
            Ok(t) => t,
            Err(why) => return format!("refused: {why}"),
        };
        let found = match metrics.read(&text) {
            Ok(found) => found,
            Err(why) => return why,
        };
        let mut shown: Vec<&str> = vec!["_measurement", "fields", "_field"];
        shown.extend(by);
        shown.extend(["_start", "_stop", "_time", "_value"]);
        let lines: Vec<String> = found
            .iter()
            .map(|r| {
                shown
                    .iter()
                    .filter(|k| !(matches!(**k, "_start" | "_stop") && r.contains_key("_time")))
                    .filter_map(|k| {
                        r.get(*k)
                            .filter(|v| !v.is_empty())
                            .map(|v| format!("{}: {v}", k.trim_start_matches('_')))
                    })
                    .collect::<Vec<_>>()
                    .join(", ")
            })
            .collect();
        if lines.is_empty() {
            "(no windows)".into()
        } else {
            lines.join("\n")
        }
    }
}

#[cfg(test)]
mod tests {
    //! Held to `agent/translation/tests/test_past.py`.

    use std::sync::{Arc, Mutex};

    use oxigraph::model::NamedNode;

    use super::*;
    use orexis::events::typed;
    use orexis::journal::Journal;

    fn prefixes() -> Prefixes {
        [
            ("prov", "http://www.w3.org/ns/prov#"),
            ("sensing", "http://example.org/orexis/sensing#"),
            ("orexis", "http://example.org/orexis#"),
        ]
        .iter()
        .map(|(a, b)| (a.to_string(), b.to_string()))
        .collect()
    }

    type Asked = Arc<Mutex<Vec<String>>>;

    fn reader(purpose: &'static str, bucket: &str, rows: Vec<BTreeMap<String, String>>) -> (Reader, Asked) {
        let asked: Asked = Arc::default();
        let kept = asked.clone();
        let read: orexis::series::Read = Arc::new(move |flux| {
            kept.lock().unwrap().push(flux.to_string());
            Ok(rows.clone())
        });
        (Reader::new(purpose, bucket, Some(read)), asked)
    }

    fn row(pairs: &[(&str, &str)]) -> BTreeMap<String, String> {
        pairs.iter().map(|(a, b)| (a.to_string(), b.to_string())).collect()
    }

    #[test]
    fn the_journal_is_read_where_it_is_and_newest_first() {
        let at = instant("2026-11-02T21:00:00+00:00").unwrap();
        let journal = Journal::new(None, 600.0, Arc::new(move || at)).unwrap();
        let entry = NamedNode::new_unchecked("urn:uuid:one");
        journal
            .record(
                &entry,
                vec![typed(entry.clone(), "http://example.org/orexis/sensing#Observed")],
                Some(at),
                false,
            )
            .unwrap();
        let past = Past {
            journal: Some(journal.store.clone()),
            history: None,
            metrics: None,
            prefixes: prefixes(),
        };
        let names: Vec<String> = past
            .tools()
            .iter()
            .map(|t| t["name"].as_str().unwrap().to_string())
            .collect();
        assert_eq!(names, [JOURNAL], "no series where the agent keeps none");
        let found = past
            .call(
                JOURNAL,
                &json!({"sparql": "SELECT ?c ?t WHERE { ?e a ?c ; prov:atTime ?t } ORDER BY DESC(?t)"}),
            )
            .unwrap();
        assert!(
            found.contains("c: sensing:Observed, t: 2026-11-02T21:00:00Z"),
            "{found}"
        );
        assert!(
            past.call(
                JOURNAL,
                &json!({"sparql": "SELECT * WHERE { SERVICE <http://x.example/> { ?s ?p ?o } }"})
            )
            .unwrap()
            .starts_with("refused: it holds a SERVICE clause")
        );
        assert!(past.call(SERIES, &json!({})).is_none() && past.call("query", &json!({})).is_none());
    }

    #[test]
    fn the_series_is_read_by_the_fields_and_the_tool_writes_the_flux() {
        let (history, asked) = reader(
            "HISTORY",
            "terrace-terrace",
            vec![row(&[
                ("_measurement", "SoilMoisture"),
                ("sensor", "moisture_sensor_terrace"),
                ("_time", "2026-10-16T08:38:00+00:00"),
                ("_value", "0.427"),
            ])],
        );
        let past = Past {
            journal: None,
            history: Some(history),
            metrics: None,
            prefixes: prefixes(),
        };
        let found = past
            .call(
                SERIES,
                &json!({"measurement": "SoilMoisture", "sensor": "moisture_sensor_terrace", "start": "-7d",
                        "every": "1h", "fn": "max", "flux": "drop everything"}),
            )
            .unwrap();
        assert_eq!(
            found,
            "measurement: SoilMoisture, sensor: moisture_sensor_terrace, time: 2026-10-16T08:38:00+00:00, value: 0.427"
        );
        let flux = asked.lock().unwrap()[0].clone();
        assert!(flux.contains("from(bucket: \"terrace-terrace\")") && flux.contains("range(start: -7d)"));
        assert!(
            flux.contains("r._measurement == \"SoilMoisture\"")
                && flux.contains("r.sensor == \"moisture_sensor_terrace\"")
        );
        assert!(flux.contains("aggregateWindow(every: 1h, fn: max") && flux.contains(&format!("limit(n: {ROWS})")));
        past.call(SERIES, &json!({"start": "2026-10-16T00:00:00Z"}));
        let last = asked.lock().unwrap().last().unwrap().clone();
        assert!(last.contains("group(columns: [\"_measurement\", \"sensor\"])"));
        assert!(last.contains("time(v: \"2026-10-16T00:00:00+00:00\")"), "{last}");
    }

    #[test]
    fn a_field_that_is_no_stretch_window_aggregate_or_name_is_refused_before_anything_is_read() {
        let (history, asked) = reader("HISTORY", "b", Vec::new());
        let past = Past {
            journal: None,
            history: Some(history),
            metrics: None,
            prefixes: prefixes(),
        };
        for (fields, why) in [
            (
                json!({"measurement": "SoilMoisture", "start": "yesterday"}),
                "refused: a stretch's end is a duration",
            ),
            (
                json!({"measurement": "SoilMoisture", "every": "1h) |> drop()"}),
                "refused: every is a duration",
            ),
            (
                json!({"measurement": "SoilMoisture", "fn": "exec"}),
                "refused: fn is one of",
            ),
        ] {
            assert!(past.call(SERIES, &fields).unwrap().starts_with(why), "{fields}");
        }
        assert!(asked.lock().unwrap().is_empty());
        past.call(
            SERIES,
            &json!({"measurement": "x\") |> drop(columns: [\"_value\"]) //"}),
        );
        assert!(asked.lock().unwrap()[0].contains(r#"r._measurement == "x\") |> drop(columns: [\"_value\"]) //""#));
    }

    #[test]
    fn a_store_that_reads_nothing_or_refuses_says_so() {
        let unread = Past {
            journal: None,
            history: Some(Reader::new("HISTORY", "b", None)),
            metrics: None,
            prefixes: prefixes(),
        };
        assert_eq!(
            unread.call(SERIES, &json!({})).unwrap(),
            "the history store is written here and never read"
        );
        let refuse: orexis::series::Read = Arc::new(|_| Err("unauthorized".into()));
        let refused = Past {
            history: Some(Reader::new("HISTORY", "b", Some(refuse))),
            ..unread
        };
        assert_eq!(
            refused.call(SERIES, &json!({})).unwrap(),
            "the history store would not answer: unauthorized"
        );
    }

    #[test]
    fn the_metrics_are_aggregated_by_the_fields_and_a_total_is_one_figure() {
        let (metrics, asked) = reader(
            "METRICS",
            "terrace-terrace-metrics",
            vec![row(&[
                ("outcome", "said"),
                ("_start", "2026-11-02T21:00:00+00:00"),
                ("_stop", "2026-11-02T21:00:00+00:00"),
                ("_value", "605.0"),
            ])],
        );
        let past = Past {
            journal: None,
            history: None,
            metrics: Some(metrics),
            prefixes: prefixes(),
        };
        let found = past
            .call(
                METRICS,
                &json!({"measurement": "translated", "field": "output_tokens_sum", "by": "outcome", "start": "-7d"}),
            )
            .unwrap();
        assert_eq!(
            found,
            "outcome: said, start: 2026-11-02T21:00:00+00:00, stop: 2026-11-02T21:00:00+00:00, value: 605.0"
        );
        let flux = asked.lock().unwrap()[0].clone();
        assert!(flux.contains("from(bucket: \"terrace-terrace-metrics\")") && flux.contains("range(start: -7d)"));
        assert!(flux.contains("r._measurement == \"translated\" and r._field == \"output_tokens_sum\""));
        assert!(
            flux.contains("group(columns: [\"outcome\"])") && flux.contains("|> sum()"),
            "sum where no fn is given"
        );
        past.call(
            METRICS,
            &json!({"measurement": "translated", "field": "count", "every": "1d", "fn": "sum"}),
        );
        let last = asked.lock().unwrap().last().unwrap().clone();
        assert!(last.contains("aggregateWindow(every: 1d, fn: sum") && last.contains("group(columns: [])"));
        past.call(METRICS, &json!({}));
        assert!(
            asked
                .lock()
                .unwrap()
                .last()
                .unwrap()
                .contains("distinct(column: \"_field\")")
        );
        for (fields, why) in [
            (json!({"measurement": "translated"}), "refused: name the field"),
            (
                json!({"measurement": "translated", "field": "x\") |> drop()"}),
                "refused: field is a name",
            ),
            (
                json!({"measurement": "translated", "field": "count", "by": "a b"}),
                "refused: by is a name",
            ),
            (
                json!({"measurement": "translated", "field": "count", "fn": "exec"}),
                "refused: fn is one of",
            ),
        ] {
            assert!(past.call(METRICS, &fields).unwrap().starts_with(why), "{fields}");
        }
    }
}
