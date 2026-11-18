//! WHAT A DEVICE IS SENT, made of the settings a step's command answered for it: each value written as JSON at its
//! property's `actuation:commandPointer`, an RFC 6901 pointer, into one document — the mirror of sensing's
//! `sensing:readingPointer`, which takes a value out of the document a board publishes.

use oxigraph::model::Literal;
use serde_json::{Map, Number, Value as Json};

/// The JSON a setting's typed literal is: an integer as an integer, any other number as a number, a boolean as a
/// boolean, and anything else as its text.
///
/// ```
/// use oxigraph::model::{Literal, vocab::xsd};
/// use orexis_actuation::encode::json_of;
///
/// assert_eq!(json_of(&Literal::new_typed_literal("180", xsd::INTEGER)), serde_json::json!(180));
/// assert_eq!(json_of(&Literal::new_typed_literal("-1", xsd::INTEGER)), serde_json::json!(-1));
/// assert_eq!(json_of(&Literal::new_typed_literal("0.5", xsd::DOUBLE)), serde_json::json!(0.5));
/// assert_eq!(json_of(&Literal::new_typed_literal("true", xsd::BOOLEAN)), serde_json::json!(true));
/// assert_eq!(json_of(&Literal::new_simple_literal("open")), serde_json::json!("open"));
/// ```
pub fn json_of(value: &Literal) -> Json {
    const INTEGERS: [&str; 13] = [
        "integer",
        "int",
        "long",
        "short",
        "byte",
        "nonNegativeInteger",
        "positiveInteger",
        "nonPositiveInteger",
        "negativeInteger",
        "unsignedLong",
        "unsignedInt",
        "unsignedShort",
        "unsignedByte",
    ];
    const NUMBERS: [&str; 3] = ["decimal", "double", "float"];
    let kind = value
        .datatype()
        .as_str()
        .strip_prefix("http://www.w3.org/2001/XMLSchema#")
        .unwrap_or_default();
    let text = value.value();
    if INTEGERS.contains(&kind)
        && let Ok(n) = text.parse::<i64>()
    {
        return Json::from(n);
    }
    if NUMBERS.contains(&kind)
        && let Some(n) = text.parse::<f64>().ok().and_then(Number::from_f64)
    {
        return Json::Number(n);
    }
    if kind == "boolean" {
        return Json::Bool(text == "true" || text == "1");
    }
    Json::String(text.to_string())
}

/// `document` with `value` written at `pointer`, every object on the way made where missing; `None` where the
/// pointer is no RFC 6901 pointer, is the whole document, or passes through something that is not an object.
///
/// ```
/// use serde_json::json;
/// use orexis_actuation::encode::put;
///
/// let mut document = json!({});
/// put(&mut document, "/to/x", json!(3)).unwrap();
/// put(&mut document, "/to/y", json!(-1)).unwrap();
/// assert_eq!(document.to_string(), r#"{"to":{"x":3,"y":-1}}"#);
///
/// let mut document = json!({});
/// put(&mut document, "/a~1b/c~0d", json!(1)).unwrap();
/// assert_eq!(document, json!({"a/b": {"c~d": 1}}));
///
/// assert!(put(&mut json!({}), "dose_ml", json!(1)).is_none());
/// assert!(put(&mut json!({}), "", json!(1)).is_none());
/// assert!(put(&mut json!({"to": 1}), "/to/x", json!(1)).is_none());
/// ```
pub fn put(document: &mut Json, pointer: &str, value: Json) -> Option<()> {
    let tokens: Vec<String> = pointer
        .strip_prefix('/')?
        .split('/')
        .map(|t| t.replace("~1", "/").replace("~0", "~"))
        .collect();
    let (last, path) = tokens.split_last()?;
    let mut at = document;
    for token in path {
        at = at
            .as_object_mut()?
            .entry(token.clone())
            .or_insert_with(|| Json::Object(Map::new()));
    }
    at.as_object_mut()?.insert(last.clone(), value);
    Some(())
}

/// The document one device is sent: each `(pointer, value)` written in the order of its pointer, so a device set
/// two properties is sent the same bytes whatever order its settings were kept in; `None` where a pointer cannot be
/// written.
///
/// ```
/// use serde_json::json;
/// use orexis_actuation::encode::document;
///
/// let sent = document(&[("/to/y".into(), json!(0)), ("/to/x".into(), json!(2))]).unwrap();
/// assert_eq!(sent, r#"{"to":{"x":2,"y":0}}"#);
/// assert_eq!(document(&[("/dose_ml".into(), json!(180))]).unwrap(), r#"{"dose_ml":180}"#);
/// ```
pub fn document(settings: &[(String, Json)]) -> Option<String> {
    let mut sorted: Vec<&(String, Json)> = settings.iter().collect();
    sorted.sort_by(|a, b| a.0.cmp(&b.0));
    let mut out = Json::Object(Map::new());
    for (pointer, value) in sorted {
        put(&mut out, pointer, value.clone())?;
    }
    Some(out.to_string())
}
