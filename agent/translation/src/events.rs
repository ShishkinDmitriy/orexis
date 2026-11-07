//! WHAT TRANSLATION SAYS HAPPENED, as `agent/translation/events.py` declares it. `Translated` only the metrics hear: one
//! use of the model — a person's message answered over a conversation's requests, or an agent's statement rendered in
//! one — with what it spent by the API's own names. `Conversed` only the journal hears: a person's message and the
//! conversation it began, in translation's words — the chat, the person, what they wrote, each tool the model called
//! with what it was handed and answered, and the words said back.

use oxigraph::model::{BlankNode, NamedNode, Triple};
use oxsdatatypes::DateTime;
use serde_json::Value as Json;

use orexis::events::{Event, Mark, integer, node, text, triple, typed};

pub const TRANSLATION: &str = "http://example.org/orexis/translation#";
/// HOW MUCH OF A TOOL'S ANSWER IS JOURNALED: past it the answer says it was cut.
pub const RESULT_CHARS: usize = 8000;

/// One use of the model: what it was for, how it ended, which model, the requests it made, the tokens they spent by the
/// API's own names, and its real seconds.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Translated {
    pub act: Option<String>,
    pub outcome: Option<String>,
    pub model: Option<String>,
    pub requests: Option<f64>,
    pub input_tokens: Option<f64>,
    pub cache_creation_input_tokens: Option<f64>,
    pub cache_read_input_tokens: Option<f64>,
    pub output_tokens: Option<f64>,
    pub duration_s: Option<f64>,
}

impl Event for Translated {
    fn metric(&self) -> Option<&'static str> {
        Some("translated")
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![
            ("act", Mark::Tag(self.act.clone())),
            ("outcome", Mark::Tag(self.outcome.clone())),
            ("model", Mark::Tag(self.model.clone())),
            ("requests", Mark::Value(self.requests)),
            ("input_tokens", Mark::Value(self.input_tokens)),
            (
                "cache_creation_input_tokens",
                Mark::Value(self.cache_creation_input_tokens),
            ),
            ("cache_read_input_tokens", Mark::Value(self.cache_read_input_tokens)),
            ("output_tokens", Mark::Value(self.output_tokens)),
            ("duration_s", Mark::Value(self.duration_s)),
        ]
    }
}

/// A person's message answered: the chat, the person, what they wrote, each tool call as (tool, what it was handed,
/// what it answered), the words said back where any were, how it ended and the model, at `at`.
#[derive(Clone, Debug, PartialEq)]
pub struct Conversed {
    pub chat: String,
    pub person: String,
    pub wrote: String,
    pub calls: Vec<(String, Json, String)>,
    pub answer: Option<String>,
    pub outcome: Option<String>,
    pub model: Option<String>,
    pub at: Option<DateTime>,
}

/// A JSON value as Python's `json.dumps(…, ensure_ascii=False, sort_keys=True)` writes it.
pub fn dumps(value: &Json) -> String {
    match value {
        Json::Object(map) => {
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort();
            let inner: Vec<String> = keys
                .iter()
                .map(|k| format!("{}: {}", Json::String((*k).clone()), dumps(&map[*k])))
                .collect();
            format!("{{{}}}", inner.join(", "))
        }
        Json::Array(items) => format!("[{}]", items.iter().map(dumps).collect::<Vec<_>>().join(", ")),
        other => other.to_string(),
    }
}

impl Event for Conversed {
    fn statements(&self, entry: &NamedNode) -> Option<Vec<Triple>> {
        let said = |name: &str, value: oxigraph::model::Term| {
            Triple::new(entry.clone(), node(&format!("{TRANSLATION}{name}")), value)
        };
        let mut out = vec![
            typed(entry.clone(), &format!("{TRANSLATION}Conversed")),
            said("chat", node(&self.chat).into()),
            said("person", node(&self.person).into()),
            said("wrote", text(&self.wrote).into()),
        ];
        for (name, value) in [
            ("answer", &self.answer),
            ("outcome", &self.outcome),
            ("model", &self.model),
        ] {
            if let Some(v) = value.as_ref().filter(|v| !v.is_empty()) {
                out.push(said(name, text(v).into()));
            }
        }
        for (order, (tool, handed, answered)) in self.calls.iter().enumerate() {
            let call = BlankNode::default();
            let answered = if answered.chars().count() <= RESULT_CHARS {
                answered.clone()
            } else {
                answered.chars().take(RESULT_CHARS).collect::<String>() + " [cut]"
            };
            out.push(said("call", call.clone().into()));
            out.push(triple(
                call.clone(),
                &format!("{TRANSLATION}order"),
                integer(order as i64),
            ));
            out.push(triple(call.clone(), &format!("{TRANSLATION}tool"), text(tool)));
            out.push(triple(
                call.clone(),
                &format!("{TRANSLATION}handed"),
                text(&dumps(handed)),
            ));
            out.push(triple(call, &format!("{TRANSLATION}answered"), text(&answered)));
        }
        Some(out)
    }

    fn at(&self) -> Option<DateTime> {
        self.at
    }
}
