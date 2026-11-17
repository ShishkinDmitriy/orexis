//! THE SERIES SINK: points a package's events answer, written to the store the world says serves their purpose — and
//! nothing about what the points are. A SERIES IS WATCHED AND NEVER BELIEVED.
//!
//! TWO PURPOSES: HISTORY, what happened, and METRICS, how the agent is doing. WHERE A PURPOSE'S STORE ANSWERS IS THE
//! WORLD'S TO SAY: its deployment graph names an `orexis:SeriesStore` that `orexis:serves` the purpose, with its
//! `schema:url` and its `orexis:organisation` (`store`). WHAT OPENS IT IS THE AGENT'S OWN SECRET, never in a
//! document: its bucket and the token that opens only it, `INFLUX_<PURPOSE>_BUCKET` and `_TOKEN`, from the
//! credential file mounted into its container alone. A purpose the world names no store for has no sink, and one
//! named without its credential is none either, said in the log. A store that refuses a point is said in the log and
//! costs the agent nothing.
//!
//! A PACKAGE MAKES ITS OWN SINK (`Sink::deployed`), where the agent is deployed and it was handed none: what
//! archives sensing's readings, the metrics, and a chat that reads the past.

use std::collections::BTreeMap;
use std::sync::Arc;

use oxsdatatypes::DateTime;

use crate::events::{Field, Point};

pub const HISTORY: &str = "HISTORY";
pub const METRICS: &str = "METRICS";
pub const PURPOSES: [&str; 2] = [HISTORY, METRICS];
const KEYS: [&str; 2] = ["BUCKET", "TOKEN"];

/// A purpose as the world's deployment graph names it.
fn purpose_iri(purpose: &str) -> Option<&'static str> {
    match purpose {
        HISTORY => Some("http://example.org/orexis#History"),
        METRICS => Some("http://example.org/orexis#Metrics"),
        _ => None,
    }
}

/// Where a purpose's store answers, as the world's deployment graph states it.
#[derive(Debug, Clone, PartialEq)]
pub struct Served {
    pub url: String,
    pub organisation: String,
}

/// THE STORE THE WORLD SAYS SERVES `purpose`, or None where its deployment graph names none.
pub fn store(store: &crate::store::Store, purpose: &str) -> Result<Option<Served>, crate::Error> {
    const SERVED_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
    PREFIX schema: <https://schema.org/>
    SELECT ?url ?organisation WHERE { \
    ?store a orexis:SeriesStore ; orexis:serves $purpose ; schema:url ?url ; orexis:organisation ?organisation } \
    ORDER BY ?url";
    let Some(iri) = purpose_iri(purpose) else {
        return Ok(None);
    };
    let graphs = store.graphs_of(&[crate::ontology::DEPLOYMENT], &crate::store::Within::common())?;
    let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
    if graphs.is_empty() {
        return Ok(None);
    }
    let text = crate::bind::bind(SERVED_Q, &[("purpose", crate::bind::Value::iri(iri))])?;
    Ok(store.rows(&text, &graphs)?.first().and_then(|row| {
        Some(Served {
            url: crate::store::value(row, "url")?,
            organisation: crate::store::value(row, "organisation")?,
        })
    }))
}

/// How a batch of points reaches a bucket: the client's own call, refused with why.
pub type Write = Box<dyn Fn(&str, &[Point]) -> Result<(), String> + Send + Sync>;
/// How a Flux query of the bucket is answered: each record as its columns, each value as Python's client reads it and
/// `str` says it, or why not. Shared with the model's thread, which reads the past off it.
pub type Read = Arc<dyn Fn(&str) -> Result<Vec<BTreeMap<String, String>>, String> + Send + Sync>;

/// One purpose's bucket as a chat reads it: what a Flux query of it answers, off any thread.
#[derive(Clone)]
pub struct Reader {
    pub purpose: &'static str,
    pub bucket: String,
    read: Option<Read>,
}

impl Reader {
    /// A reader of `bucket` through `read`, or of nothing where `read` is none.
    pub fn new(purpose: &'static str, bucket: &str, read: Option<Read>) -> Self {
        Reader {
            purpose,
            bucket: bucket.to_string(),
            read,
        }
    }

    /// The records a Flux query of this bucket answers; why not, where the store refuses or the sink reads nothing.
    pub fn read(&self, flux: &str) -> Result<Vec<BTreeMap<String, String>>, String> {
        match &self.read {
            None => Err(format!(
                "the {} store is written here and never read",
                self.purpose.to_lowercase()
            )),
            Some(read) => {
                read(flux).map_err(|e| format!("the {} store would not answer: {e}", self.purpose.to_lowercase()))
            }
        }
    }
}

/// One purpose's bucket, and how a point reaches it.
pub struct Sink {
    pub purpose: &'static str,
    pub bucket: String,
    write: Write,
    read: Option<Read>,
}

impl Sink {
    /// A sink writing through `write`, reading nothing.
    pub fn new(purpose: &'static str, bucket: &str, write: Write) -> Self {
        Sink {
            purpose,
            bucket: bucket.to_string(),
            write,
            read: None,
        }
    }

    /// THE SINK OF `purpose` FOR AN AGENT DEPLOYED IN THE WORLD `store` HOLDS: the store the world says serves it,
    /// opened by the bucket and the token the agent's own credential names in `env`. None where the world names no
    /// store for the purpose, and where the credential is missing or named in part — said in the log.
    pub fn deployed(
        store: &crate::store::Store,
        purpose: &'static str,
        env: &dyn Fn(&str) -> Option<String>,
    ) -> Result<Option<(Self, Served)>, crate::Error> {
        let Some(served) = self::store(store, purpose)? else {
            return Ok(None);
        };
        let named: Vec<(&str, Option<String>)> = KEYS
            .iter()
            .map(|k| (*k, env(&format!("INFLUX_{purpose}_{k}")).filter(|v| !v.is_empty())))
            .collect();
        let missing: Vec<String> = named
            .iter()
            .filter(|(_, v)| v.is_none())
            .map(|(k, _)| format!("INFLUX_{purpose}_{k}"))
            .collect();
        if !missing.is_empty() {
            log::warn!(
                "the world names a {} store and the agent's credential names no {} — nothing is written for it",
                purpose.to_lowercase(),
                missing.join(", ")
            );
            return Ok(None);
        }
        let value = |key: &str| {
            named
                .iter()
                .find(|(k, _)| *k == key)
                .and_then(|(_, v)| v.clone())
                .unwrap_or_default()
        };
        let sink = Self::influx(
            purpose,
            &served.url,
            &served.organisation,
            &value("BUCKET"),
            &value("TOKEN"),
        );
        Ok(Some((sink, served)))
    }

    #[cfg(feature = "series")]
    fn influx(purpose: &'static str, url: &str, org: &str, bucket: &str, token: &str) -> Self {
        let agent = ureq::AgentBuilder::new()
            .timeout(std::time::Duration::from_secs(10))
            .build();
        let (url, org, token) = (
            url.trim_end_matches('/').to_string(),
            org.to_string(),
            token.to_string(),
        );
        let (reading, read_url, read_org, read_token) = (agent.clone(), url.clone(), org.clone(), token.clone());
        let read: Read = Arc::new(move |flux| {
            let body = reading
                .post(&format!("{read_url}/api/v2/query"))
                .query("org", &read_org)
                .set("Authorization", &format!("Token {read_token}"))
                .set("Content-Type", "application/vnd.flux")
                .set("Accept", "application/csv")
                .send_string(flux)
                .map_err(|e| e.to_string())?
                .into_string()
                .map_err(|e| e.to_string())?;
            Ok(records(&body))
        });
        let write: Write = Box::new(move |bucket, points| {
            let body: Vec<String> = points.iter().map(line).collect();
            agent
                .post(&format!("{url}/api/v2/write"))
                .query("org", &org)
                .query("bucket", bucket)
                .query("precision", "ns")
                .set("Authorization", &format!("Token {token}"))
                .set("Content-Type", "text/plain; charset=utf-8")
                .send_string(&body.join("\n"))
                .map(|_| ())
                .map_err(|e| e.to_string())
        });
        Sink {
            read: Some(read),
            ..Sink::new(purpose, bucket, write)
        }
    }

    #[cfg(not(feature = "series"))]
    fn influx(purpose: &'static str, _url: &str, _org: &str, bucket: &str, _token: &str) -> Self {
        log::warn!(
            "a {} store is named and this binary was built without the series: nothing is written",
            purpose.to_lowercase()
        );
        Sink::new(purpose, bucket, Box::new(|_, _| Err("built without the series".into())))
    }

    /// Write `points`; how many. A store that refuses is said in the log, never raised.
    pub fn write(&self, points: &[Point]) -> usize {
        if points.is_empty() {
            return 0;
        }
        match (self.write)(&self.bucket, points) {
            Ok(()) => points.len(),
            Err(e) => {
                log::warn!(
                    "the {} store refused {} point(s): {e}",
                    self.purpose.to_lowercase(),
                    points.len()
                );
                0
            }
        }
    }

    /// The records a Flux query of this sink's bucket answers; why not, where the store refuses or reads nothing.
    pub fn read(&self, flux: &str) -> Result<Vec<BTreeMap<String, String>>, String> {
        self.reader().read(flux)
    }

    /// The bucket as a chat reads it, off any thread.
    pub fn reader(&self) -> Reader {
        Reader::new(self.purpose, &self.bucket, self.read.clone())
    }
}

/// The records InfluxDB's annotated CSV holds, each column's value as Python's client reads it and `str` says it: an
/// instant as `isoformat` to the second, a double as its `repr`, an integer as itself, a text as it is.
pub fn records(csv: &str) -> Vec<BTreeMap<String, String>> {
    let mut out = Vec::new();
    let (mut types, mut header): (Vec<String>, Vec<String>) = (Vec::new(), Vec::new());
    for line in csv.lines() {
        let line = line.trim_end_matches('\r');
        if line.trim().is_empty() {
            header.clear();
            continue;
        }
        let cells = cells(line);
        if cells.first().is_some_and(|c| c == "#datatype") {
            types = cells;
            continue;
        }
        if cells.first().is_some_and(|c| c.starts_with('#')) {
            continue;
        }
        if header.is_empty() {
            header = cells;
            continue;
        }
        let mut record = BTreeMap::new();
        for (i, name) in header.iter().enumerate().skip(1) {
            let Some(cell) = cells.get(i) else { continue };
            if name.is_empty() || name == "result" || name == "table" {
                continue;
            }
            let kind = types.get(i).map(String::as_str).unwrap_or("string");
            record.insert(name.clone(), said(cell, kind));
        }
        out.push(record);
    }
    out
}

/// One cell as Python's client reads its type and `str` says it.
fn said(cell: &str, kind: &str) -> String {
    match kind {
        "double" => cell.parse::<f64>().map_or(cell.to_string(), crate::rdf::repr),
        k if k.starts_with("dateTime") => match crate::clock::instant(cell) {
            Ok(at) => {
                let iso = crate::clock::isoformat(at);
                match iso.find('.') {
                    Some(dot) => format!(
                        "{}{}",
                        &iso[..dot],
                        &iso[iso[dot..].find(['+', '-', 'Z']).map_or(iso.len(), |o| dot + o)..]
                    ),
                    None => iso,
                }
            }
            Err(_) => cell.to_string(),
        },
        "boolean" => {
            if cell == "true" {
                "True".into()
            } else {
                "False".into()
            }
        }
        _ => cell.split_whitespace().collect::<Vec<_>>().join(" "),
    }
}

/// The cells of one CSV line, a quoted one unquoted.
fn cells(line: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut cell = String::new();
    let mut quoted = false;
    let mut chars = line.chars().peekable();
    while let Some(c) = chars.next() {
        match c {
            '"' if quoted && chars.peek() == Some(&'"') => {
                cell.push('"');
                chars.next();
            }
            '"' => quoted = !quoted,
            ',' if !quoted => out.push(std::mem::take(&mut cell)),
            other => cell.push(other),
        }
    }
    out.push(cell);
    out
}

/// The process's environment, as a package asks it for the agent's own credential.
pub fn environment(key: &str) -> Option<String> {
    std::env::var(key).ok()
}

fn escaped(text: &str, also: &[char]) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.chars() {
        if c == ',' || c == ' ' || also.contains(&c) {
            out.push('\\');
        }
        out.push(c);
    }
    out
}

/// The nanoseconds since the epoch `at` is, read off its decimal seconds so nothing is lost to a float.
pub fn nanos(at: DateTime) -> Option<i128> {
    let epoch: DateTime = "1970-01-01T00:00:00Z".parse().ok()?;
    let since = at.checked_sub(epoch)?.as_seconds().to_string();
    let (whole, fraction) = since.split_once('.').unwrap_or((&since, ""));
    let negative = whole.starts_with('-');
    let whole: i128 = whole.parse().ok()?;
    let mut digits: String = fraction.chars().take(9).collect();
    while digits.len() < 9 {
        digits.push('0');
    }
    let fraction: i128 = digits.parse().ok()?;
    Some(whole * 1_000_000_000 + if negative { -fraction } else { fraction })
}

/// A point in InfluxDB's line protocol: the measurement, its tags sorted, its fields, and its instant in nanoseconds.
pub fn line(point: &Point) -> String {
    let mut out = escaped(&point.measurement, &[]);
    for (k, v) in &point.tags {
        out.push_str(&format!(",{}={}", escaped(k, &['=']), escaped(v, &['='])));
    }
    let fields: Vec<String> = point
        .fields
        .iter()
        .map(|(k, v)| {
            let value = match v {
                Field::Float(f) => crate::rdf::repr(*f),
                Field::Int(i) => format!("{i}i"),
                Field::Bool(b) => b.to_string(),
                Field::Text(t) => format!("\"{}\"", t.replace('\\', "\\\\").replace('"', "\\\"")),
            };
            format!("{}={value}", escaped(k, &['=']))
        })
        .collect();
    out.push(' ');
    out.push_str(&fields.join(","));
    if let Some(ns) = point.time.and_then(nanos) {
        out.push_str(&format!(" {ns}"));
    }
    out
}

/// WHAT THE AGENT KEEPS OF WHAT HAPPENED, as a chat reads it: its journal where it lies, and its two series. Each
/// package that keeps any of it says so as it makes its core (`Provided::alter`), the journal's where it lies
/// and each series' package the sink it writes, and a reader reads it once every core is made.
#[derive(Clone, Default)]
pub struct Reads {
    pub journal: crate::task::Journaled,
    pub history: Option<Reader>,
    pub metrics: Option<Reader>,
}

#[cfg(test)]
mod tests {
    //! The sink, held to what `agent/tests/test_series.py` holds the Python one to.

    use super::*;
    use crate::clock::instant;
    use std::sync::Mutex;

    fn point() -> Point {
        Point {
            measurement: "anything".into(),
            tags: BTreeMap::new(),
            fields: BTreeMap::from([("x".to_string(), Field::Float(1.0))]),
            time: None,
        }
    }

    #[test]
    fn a_sink_writes_what_it_is_handed_to_its_bucket_and_nothing_handed_is_nothing_written() {
        let written = Arc::new(Mutex::new(Vec::new()));
        let kept = written.clone();
        let sink = Sink::new(
            HISTORY,
            "b",
            Box::new(move |bucket, points| {
                kept.lock().unwrap().push((bucket.to_string(), points.to_vec()));
                Ok(())
            }),
        );
        assert_eq!(sink.write(&[point()]), 1);
        assert_eq!(sink.write(&[]), 0);
        assert_eq!(*written.lock().unwrap(), [("b".to_string(), vec![point()])]);
    }

    #[test]
    fn a_store_that_refuses_costs_the_agent_nothing() {
        let sink = Sink::new(HISTORY, "b", Box::new(|_, _| Err("down".into())));
        assert_eq!(sink.write(&[point()]), 0);
    }

    #[test]
    fn a_query_is_read_off_the_annotated_csv_each_value_as_python_says_it() {
        let csv = "#group,false,false,true,false,false\r\n#datatype,string,long,string,dateTime:RFC3339,double\r\n\
                   #default,_result,,,,\r\n,result,table,_measurement,_time,_value\r\n\
                   ,,0,SoilMoisture,2026-10-16T08:38:00Z,0.427\r\n,,0,\"a, b\",2026-10-16T09:00:00.5Z,605\r\n\r\n";
        let found = records(csv);
        assert_eq!(found.len(), 2);
        assert_eq!(found[0]["_measurement"], "SoilMoisture");
        assert_eq!(found[0]["_time"], "2026-10-16T08:38:00+00:00");
        assert_eq!(
            (found[0]["_value"].as_str(), found[1]["_value"].as_str()),
            ("0.427", "605.0")
        );
        assert_eq!(
            (found[1]["_measurement"].as_str(), found[1]["_time"].as_str()),
            ("a, b", "2026-10-16T09:00:00+00:00")
        );
    }

    #[test]
    fn a_point_is_written_in_line_protocol_its_instant_in_nanoseconds() {
        let p = Point {
            measurement: "Soil Moisture".into(),
            tags: BTreeMap::from([
                ("sensor".to_string(), "probe,1".to_string()),
                ("feature".to_string(), "bed".to_string()),
            ]),
            fields: BTreeMap::from([
                ("value".to_string(), Field::Float(3.0)),
                ("count".to_string(), Field::Int(2)),
                ("note".to_string(), Field::Text("say \"hi\"".into())),
            ]),
            time: Some(instant("2026-01-01T12:00:00.5+00:00").unwrap()),
        };
        assert_eq!(
            line(&p),
            "Soil\\ Moisture,feature=bed,sensor=probe\\,1 count=2i,note=\"say \\\"hi\\\"\",value=3.0 1767268800500000000"
        );
    }
}
