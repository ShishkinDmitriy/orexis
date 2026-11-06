//! HOW BYTES BECOME A NUMBER — the stages, and the family among them — as `agent/sensing/pipeline.py` makes one:
//!
//! ```text
//! bytes ─[codec]→ document ─[pointer]→ number, or numbers each with how long ago
//! ```
//!
//! **A NUMBER IS NOT YET A QUANTITY**: what it is an observation of, and what quantity it is, are concluded by this
//! layer's rules. **THE CONCEPT IS THIS LAYER'S**: a codec is a family, `sensing:Codec`; which member serves a
//! sensor is a fact the world derives onto it (`sensing:decodedBy`), the member that ships, JSON, is held here by
//! its term, and a sensor whose world states none gets it. A member the world names that the table lacks is one
//! unread sensor and a warning, never a dead agent.

use std::collections::BTreeMap;

use oxsdatatypes::DateTime;
use serde_json::Value as Json;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{instant, seconds};
use orexis::ontology::BELIEF;
use orexis::store::{Store, Within, value};

use crate::ontology::JSON_CODEC;

/// What a sensor's value is called when nothing says otherwise: every single-property device here publishes
/// `{"value": ...}`.
pub const DEFAULT_POINTER: &str = "/value";

/// WHAT A READING IN AN ARRAY SAYS: its number, and how many seconds before the message it was taken.
const VALUE: &str = "value";
const AGE: &str = "age_s";

/// One stretch of a series: where it starts, where it ends, and the value it holds.
pub type Stretch = (DateTime, DateTime, f64);

/// Why bytes are no number: not a document of the codec's format, or a pointer that finds no number there.
#[derive(Debug, PartialEq)]
pub enum Unread {
    Codec(String),
    Pointer(String),
}

impl std::fmt::Display for Unread {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Unread::Codec(why) | Unread::Pointer(why) => f.write_str(why),
        }
    }
}

/// One wire format, both ways — a member of `sensing:Codec`, served by the term it implements.
pub trait Codec {
    /// The document these bytes hold.
    fn decode(&self, payload: &[u8]) -> Result<Json, Unread>;
    /// The bytes that document is, on the wire.
    fn encode(&self, document: &Json) -> Result<Vec<u8>, Unread>;
}

/// Bytes to a document and back, by the format every board here already speaks.
pub struct JsonCodec;

impl Codec for JsonCodec {
    fn decode(&self, payload: &[u8]) -> Result<Json, Unread> {
        serde_json::from_slice(payload).map_err(|e| Unread::Codec(format!("not a JSON document: {e}")))
    }

    fn encode(&self, document: &Json) -> Result<Vec<u8>, Unread> {
        serde_json::to_vec(document).map_err(|e| Unread::Codec(format!("not encodable as JSON: {e}")))
    }
}

/// The members, by the term each implements: this layer's one, and whatever a caller adds.
pub struct Codecs(BTreeMap<String, Box<dyn Codec + Send + Sync>>);

impl Codecs {
    /// The members this layer ships.
    pub fn shipped() -> Self {
        let mut out = Codecs(BTreeMap::new());
        out.0.insert(JSON_CODEC.to_string(), Box::new(JsonCodec));
        out
    }

    /// These members and `codec` serving `term`.
    pub fn with(mut self, term: &str, codec: impl Codec + Send + Sync + 'static) -> Self {
        self.0.insert(term.to_string(), Box::new(codec));
        self
    }
}

/// The one RAW VALUE a JSON Pointer identifies — RFC 6901. Number-only by our decision (#101).
pub fn resolve(pointer: &str, doc: &Json) -> Result<f64, Unread> {
    number(pointer, walk(pointer, doc)?)
}

/// Whatever a JSON Pointer identifies in `doc`, RFC 6901.
fn walk<'d>(pointer: &str, doc: &'d Json) -> Result<&'d Json, Unread> {
    if !pointer.starts_with('/') {
        return Err(Unread::Pointer(format!(
            "'{pointer}' is not a JSON Pointer — it must start with '/'"
        )));
    }
    let mut node = doc;
    for token in pointer.split('/').skip(1) {
        let key = token.replace("~1", "/").replace("~0", "~");
        node = match node {
            Json::Array(items) => {
                if key.is_empty() || !key.chars().all(|c| c.is_ascii_digit()) {
                    return Err(Unread::Pointer(format!("'{pointer}': '{key}' is not an array index")));
                }
                let index: usize = key.parse().unwrap_or(usize::MAX);
                items
                    .get(index)
                    .ok_or_else(|| Unread::Pointer(format!("'{pointer}': index {index} is past the end")))?
            }
            Json::Object(fields) => fields
                .get(&key)
                .ok_or_else(|| Unread::Pointer(format!("'{pointer}': no '{key}' here")))?,
            _ => {
                return Err(Unread::Pointer(format!(
                    "'{pointer}': '{key}' has nothing to select from"
                )));
            }
        };
    }
    Ok(node)
}

fn number(pointer: &str, node: &Json) -> Result<f64, Unread> {
    node.as_f64()
        .filter(|_| node.is_number())
        .ok_or_else(|| Unread::Pointer(format!("'{pointer}': what is there is not a number")))
}

/// THE BINDING: what the world derives onto a sensor about its bytes, every part optional.
const BINDING_Q: &str = "
SELECT ?codec ?pointer ?starts ?ends WHERE {
  OPTIONAL { $sensor sensing:decodedBy ?codec }
  OPTIONAL { $sensor sensing:readingPointer ?pointer }
  OPTIONAL { $sensor sensing:startsPointer ?starts }
  OPTIONAL { $sensor sensing:endsPointer ?ends } }";

#[derive(Default)]
struct Binding {
    codec: Option<String>,
    pointer: Option<String>,
    starts: Option<String>,
    ends: Option<String>,
}

fn binding(store: &Store, sensor: &str) -> Result<Binding, Error> {
    let common = store.graphs_of(&[BELIEF], &Within::common())?;
    let graphs: Vec<&str> = common.iter().map(String::as_str).collect();
    let found = store.rows(&bind(BINDING_Q, &[("sensor", Value::iri(sensor))])?, &graphs)?;
    Ok(found.first().map_or_else(Binding::default, |r| Binding {
        codec: value(r, "codec"),
        pointer: value(r, "pointer"),
        starts: value(r, "starts"),
        ends: value(r, "ends"),
    }))
}

/// The codec the binding names, or None where it is one nothing here implements — said in the log.
fn codec_of<'c>(codecs: &'c Codecs, sensor: &str, binding: &Binding) -> Option<&'c (dyn Codec + Send + Sync)> {
    let term = binding.codec.as_deref().unwrap_or(JSON_CODEC);
    let found = codecs.0.get(term).map(Box::as_ref);
    if found.is_none() {
        log::warn!("{sensor} names a codec nothing here implements: {term}");
    }
    found
}

/// What `sensor`'s share of `payload` holds, by the binding the world states for it — each reading as (number,
/// seconds before the message), oldest first — or None where any stage refuses, said in the log.
pub fn decode(store: &Store, sensor: &str, payload: &[u8]) -> Result<Option<Vec<(f64, f64)>>, Error> {
    decode_by(&Codecs::shipped(), store, sensor, payload)
}

/// `decode`, by the members `codecs` holds.
pub fn decode_by(
    codecs: &Codecs,
    store: &Store,
    sensor: &str,
    payload: &[u8],
) -> Result<Option<Vec<(f64, f64)>>, Error> {
    let binding = binding(store, sensor)?;
    let Some(codec) = codec_of(codecs, sensor, &binding) else {
        return Ok(None);
    };
    let pointer = binding.pointer.as_deref().unwrap_or(DEFAULT_POINTER);
    let read = || -> Result<Vec<(f64, f64)>, Unread> {
        let doc = codec.decode(payload)?;
        let node = walk(pointer, &doc)?;
        let Json::Array(items) = node else {
            return Ok(vec![(number(pointer, node)?, 0.0)]);
        };
        if items.is_empty() {
            return Err(Unread::Pointer(format!("'{pointer}': an array of no readings")));
        }
        let mut readings = Vec::new();
        for (n, item) in items.iter().enumerate() {
            let field = |key: &str, absent: Option<Json>| -> Result<f64, Unread> {
                let at = format!("{pointer}/{n}/{key}");
                match item {
                    Json::Object(fields) => match fields.get(key).cloned().or(absent) {
                        Some(found) => number(&at, &found),
                        None => Err(Unread::Pointer(format!("'{at}': what is there is not a number"))),
                    },
                    _ => Err(Unread::Pointer(format!("'{at}': what is there is not a number"))),
                }
            };
            readings.push((field(VALUE, None)?, field(AGE, Some(Json::from(0)))?));
        }
        readings.sort_by(|a, b| b.1.total_cmp(&a.1));
        Ok(readings)
    };
    match read() {
        Ok(readings) => Ok(Some(readings)),
        Err(why) => {
            log::warn!("{sensor}: unread — {why}");
            Ok(None)
        }
    }
}

/// Whether `sensor` reads a SERIES: it states where the instants its values are for are kept.
pub fn reads_series(store: &Store, sensor: &str) -> Result<bool, Error> {
    let binding = binding(store, sensor)?;
    Ok(binding.starts.is_some() || binding.ends.is_some())
}

/// The stretches `sensor`'s series in `payload` holds — (start, end, value), first first — by its binding, or None
/// where any stage refuses, said in the log. Each value holds from its instant to the next (starts) or from the one
/// before to its own (ends), and the stretch at the open end is as long as its neighbour. An instant is ISO 8601 or
/// seconds since the epoch, UTC where it states no offset. A value that is not a number is no stretch.
pub fn decode_series(store: &Store, sensor: &str, payload: &[u8]) -> Result<Option<Vec<Stretch>>, Error> {
    let binding = binding(store, sensor)?;
    let codecs = Codecs::shipped();
    let Some(codec) = codec_of(&codecs, sensor, &binding) else {
        return Ok(None);
    };
    let ends = binding.starts.is_none();
    let read = || -> Result<(Vec<Json>, Vec<DateTime>), Unread> {
        let document = codec.decode(payload)?;
        let values = walk(binding.pointer.as_deref().unwrap_or(DEFAULT_POINTER), &document)?;
        let at = if ends {
            binding.ends.as_deref()
        } else {
            binding.starts.as_deref()
        }
        .unwrap_or_default();
        let instants = walk(at, &document)?;
        let (Json::Array(values), Json::Array(instants)) = (values, instants) else {
            return Err(Unread::Pointer(
                "the values and the instants are not two arrays of one length".into(),
            ));
        };
        if values.len() != instants.len() {
            return Err(Unread::Pointer(
                "the values and the instants are not two arrays of one length".into(),
            ));
        }
        let times = instants.iter().map(instant_of).collect::<Result<Vec<_>, _>>()?;
        Ok((values.clone(), times))
    };
    let (values, times) = match read() {
        Ok(read) => read,
        Err(why) => {
            log::warn!("{sensor}: unread series — {why}");
            return Ok(None);
        }
    };
    if times.len() < 2 {
        log::warn!("{sensor}: a series of {} instant(s) says no stretch", times.len());
        return Ok(None);
    }
    let step = |a: DateTime, b: DateTime| b.checked_sub(a);
    let mut out = Vec::new();
    for (n, (when, value)) in times.iter().zip(&values).enumerate() {
        let Some(value) = value.as_f64().filter(|_| value.is_number()) else {
            continue;
        };
        let (start, end) = if ends {
            let start = if n > 0 {
                Some(times[n - 1])
            } else {
                step(times[0], times[1]).and_then(|d| when.checked_sub_day_time_duration(d))
            };
            (start, Some(*when))
        } else {
            let end = if n + 1 < times.len() {
                Some(times[n + 1])
            } else {
                step(times[times.len() - 2], times[times.len() - 1]).and_then(|d| when.checked_add_day_time_duration(d))
            };
            (Some(*when), end)
        };
        if let (Some(start), Some(end)) = (start, end) {
            out.push((start, end, value));
        }
    }
    Ok(Some(out))
}

/// An instant a series gives: ISO 8601, UTC where it states no offset, or seconds since the epoch.
fn instant_of(value: &Json) -> Result<DateTime, Unread> {
    let refused = || Unread::Pointer(format!("{value} is not an instant"));
    match value {
        Json::Number(n) => {
            let since = n.as_f64().ok_or_else(refused)?;
            let epoch = instant("1970-01-01T00:00:00Z").map_err(|_| refused())?;
            if since >= 0.0 {
                epoch.checked_add_day_time_duration(seconds(since)).ok_or_else(refused)
            } else {
                epoch.checked_sub_day_time_duration(seconds(-since)).ok_or_else(refused)
            }
        }
        Json::String(text) => {
            //  `fromisoformat` reads an instant to the minute; XSD wants its seconds.
            let full = if text.len() == 16 && text.as_bytes().get(13) == Some(&b':') {
                format!("{text}:00")
            } else {
                text.clone()
            };
            instant(&full).map_err(|_| refused())
        }
        _ => Err(refused()),
    }
}

#[cfg(test)]
mod tests {
    //! The pipeline, held as `agent/sensing/tests/test_pipeline.py` holds it: bytes to a document by the codec, to a
    //! number by the pointer — over the pot's probe and over a board's peripherals, and every way it refuses, which
    //! is None and a warning, never a number.

    use std::path::{Path, PathBuf};

    use serde_json::json;

    use orexis::snapshots::stand_in;

    use super::*;

    const TEST: &str = "http://example.org/test#";

    /// ONE BOARD, THREE PERIPHERALS, ONE MESSAGE: what a DHT11 beside a moisture probe publishes.
    const BOARD_MESSAGE: &[u8] = br#"{"temperature": 21.5, "humidity": 0.61, "soil": {"moisture": 0.22}}"#;

    fn here() -> &'static Path {
        Path::new(env!("CARGO_MANIFEST_DIR"))
    }

    fn world(name: &str) -> PathBuf {
        here().join("tests/worlds").join(name)
    }

    fn pot() -> Store {
        stand_in(&world("a_pot_and_its_probe.trig"))
    }

    fn board() -> Store {
        stand_in(&world("a_board_and_its_peripherals.trig"))
    }

    fn series() -> Store {
        stand_in(&here().join("tests/received/a_forecast_is_a_graph_per_stretch_ahead.trig"))
    }

    fn probe() -> String {
        format!("{TEST}probe")
    }

    #[test]
    fn json_then_the_default_pointer_then_identity() {
        assert_eq!(
            decode(&pot(), &probe(), br#"{"value": 0.183}"#).unwrap(),
            Some(vec![(0.183, 0.0)])
        );
    }

    #[test]
    fn two_sensors_on_one_board_take_their_own_values_from_one_message() {
        let store = board();
        assert_eq!(
            decode(&store, &format!("{TEST}thermo"), BOARD_MESSAGE).unwrap(),
            Some(vec![(21.5, 0.0)])
        );
        assert_eq!(
            decode(&store, &format!("{TEST}hygro"), BOARD_MESSAGE).unwrap(),
            Some(vec![(0.61, 0.0)])
        );
        assert_eq!(
            decode(&store, &probe(), BOARD_MESSAGE).unwrap(),
            Some(vec![(0.22, 0.0)])
        );
    }

    struct Csv;

    impl Codec for Csv {
        fn decode(&self, payload: &[u8]) -> Result<Json, Unread> {
            let text = String::from_utf8_lossy(payload);
            let numbers: Result<Vec<f64>, _> = text.split(',').map(str::parse::<f64>).collect();
            numbers.map(|n| json!(n)).map_err(|e| Unread::Codec(e.to_string()))
        }

        fn encode(&self, document: &Json) -> Result<Vec<u8>, Unread> {
            Ok(document.to_string().into_bytes())
        }
    }

    #[test]
    fn a_member_from_elsewhere_serves_by_the_term_it_declares() {
        let codecs = Codecs::shipped().with(&format!("{TEST}Csv"), Csv);
        let store = board();
        assert_eq!(
            decode_by(&codecs, &store, &format!("{TEST}gauge"), b"10130,225").unwrap(),
            Some(vec![(225.0, 0.0)])
        );
        assert_eq!(
            decode_by(&codecs, &store, &format!("{TEST}thermo"), b"10130,225").unwrap(),
            None,
            "the thermometer's bytes are JSON, whatever the gauge's are"
        );
    }

    #[test]
    fn a_missing_field_or_bytes_that_are_no_document_are_unread() {
        assert_eq!(decode(&pot(), &probe(), br#"{"temperature": 21}"#).unwrap(), None);
        assert_eq!(decode(&pot(), &probe(), b"\xff\xfe").unwrap(), None);
    }

    #[test]
    fn a_codec_nothing_here_implements_is_unread() {
        assert_eq!(decode(&board(), &format!("{TEST}barometer"), b"\xa1").unwrap(), None);
    }

    #[test]
    fn the_pointer_is_rfc_6901() {
        assert_eq!(resolve("/a/0/b~1c", &json!({"a": [{"b/c": 3}]})), Ok(3.0));
        assert!(resolve("value", &json!({"value": 1})).is_err());
        assert!(resolve("/a", &json!({"a": {"whole": "document"}})).is_err());
        assert!(resolve("/a/9", &json!({"a": [1]})).is_err());
        assert!(resolve("/a", &json!({"a": true})).is_err(), "a boolean is no number");
    }

    #[test]
    fn the_json_codec_codes_both_ways() {
        let doc = json!({"value": 1});
        assert_eq!(JsonCodec.decode(&JsonCodec.encode(&doc).unwrap()), Ok(doc));
        assert!(JsonCodec.decode(b"{").is_err());
        assert_eq!(DEFAULT_POINTER, "/value");
    }

    fn at(hour: u32) -> DateTime {
        instant(&format!("2026-01-01T{hour:02}:00:00Z")).unwrap()
    }

    #[test]
    fn an_ends_pointer_makes_each_value_the_stretch_up_to_its_instant() {
        let store = series();
        assert!(reads_series(&store, &format!("{TEST}weather")).unwrap());
        assert!(!reads_series(&store, &probe()).unwrap());
        let got = decode_series(
            &store,
            &format!("{TEST}weather"),
            br#"{"hourly": {"time": ["2026-01-01T13:00", "2026-01-01T14:00"], "precipitation": [0.4, 0.0]}}"#,
        )
        .unwrap();
        assert_eq!(got, Some(vec![(at(12), at(13), 0.4), (at(13), at(14), 0.0)]));
    }

    #[test]
    fn a_starts_pointer_and_epoch_instants_make_each_value_the_stretch_from_its_instant() {
        let store = series();
        store
            .update(
                "PREFIX sensing: <http://example.org/orexis/sensing#> PREFIX : <http://example.org/test#>
                 DELETE WHERE { GRAPH :world { :weather sensing:endsPointer ?p } } ;
                 INSERT DATA { GRAPH :world { :weather sensing:startsPointer \"/hourly/time\" } }",
            )
            .unwrap();
        let noon = 1_767_268_800;
        let payload = format!(
            r#"{{"hourly": {{"time": [{noon}, {}], "precipitation": [1, 2]}}}}"#,
            noon + 3600
        );
        let got = decode_series(&store, &format!("{TEST}weather"), payload.as_bytes()).unwrap();
        assert_eq!(got, Some(vec![(at(12), at(13), 1.0), (at(13), at(14), 2.0)]));
    }

    #[test]
    fn a_series_whose_arrays_disagree_is_unread() {
        let got = decode_series(
            &series(),
            &format!("{TEST}weather"),
            br#"{"hourly": {"time": ["2026-01-01T13:00"], "precipitation": [1, 2]}}"#,
        )
        .unwrap();
        assert_eq!(got, None);
    }

    #[test]
    fn an_array_of_readings_is_each_its_number_and_how_long_ago_oldest_first() {
        let store = pot();
        let got = decode(
            &store,
            &probe(),
            br#"{"value": [{"value": 361, "age_s": 0}, {"value": 656, "age_s": 25}]}"#,
        );
        assert_eq!(got.unwrap(), Some(vec![(656.0, 25.0), (361.0, 0.0)]));
        assert_eq!(
            decode(&store, &probe(), br#"{"value": [{"value": 718}]}"#).unwrap(),
            Some(vec![(718.0, 0.0)])
        );
    }

    #[test]
    fn an_array_holding_no_number_is_unread() {
        let store = pot();
        assert_eq!(decode(&store, &probe(), br#"{"value": []}"#).unwrap(), None);
        assert_eq!(decode(&store, &probe(), br#"{"value": [{"age_s": 3}]}"#).unwrap(), None);
    }
}
