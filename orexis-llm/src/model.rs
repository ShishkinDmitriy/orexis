//! THE MODEL CLIENT, as `agent/translation/model.py` kept it: the one place an agent asks a language model, off its
//! pass, at a run-time edge.
//!
//! **A CONVERSATION, AND ONE CALL.** `converse` sends a system prompt in blocks, all but the last cached, the messages so
//! far with their last block marked for the cache, and the tools the model may call, none where it is the last turn;
//! `ask` is one call of one message, read as text. **WHAT ONE POST DOES NOT DO** the Python copy took Anthropic's SDK for:
//! an overloaded, rate-limited or unreachable API is asked again `llm:retries` times with backoff, and each failure is named
//! by its class, which `why_not` says in the chat in a person's terms. **WHERE IT ANSWERS IS THE WORLD'S TO SAY, AND
//! WHICH MODEL AND ITS KEY THE AGENT'S SECRET**: the url is the world's deployment graph's, of the `llm:Model` the
//! asking role names, and `MODEL_API_KEY` and `MODEL_NAME` are environment.

use std::collections::BTreeMap;
use std::future::Future;
use std::pin::Pin;
use std::time::Duration;

use serde_json::{Value as Json, json};

pub const DEFAULT_URL: &str = "https://api.anthropic.com";
const VERSION: &str = "2023-06-01";
/// WHAT A TURN SPENT, by the API's own names.
pub const TOKENS: [&str; 4] = [
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
];

/// Why the model would not answer, by the class of the failure, its retries spent.
#[derive(Clone, Debug, PartialEq)]
pub enum Failure {
    Refused(String),
    RateLimited(String),
    Overloaded(String),
    Unreachable(String),
    Other(String),
}

impl std::fmt::Display for Failure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let (Failure::Refused(s)
        | Failure::RateLimited(s)
        | Failure::Overloaded(s)
        | Failure::Unreachable(s)
        | Failure::Other(s)) = self;
        write!(f, "{s}")
    }
}

/// Why the model would not answer, in a person's terms.
pub fn why_not(failure: &Failure) -> String {
    match failure {
        Failure::Refused(_) => "its model refused its key".into(),
        Failure::RateLimited(_) => "its model is asked too often just now; try again in a minute".into(),
        Failure::Overloaded(_) => "its model is overloaded just now; try again in a minute".into(),
        Failure::Unreachable(_) => "its model could not be reached".into(),
        Failure::Other(s) => format!("its model would not answer ({s})"),
    }
}

/// What one call answered: the text, each tool called with its input, and the tokens spent.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Answer {
    pub text: String,
    pub calls: Vec<(String, Json)>,
    pub tokens: BTreeMap<String, i64>,
}

/// One turn of a conversation: the text the model wrote, each tool it called as its id, name and input, the content to
/// hand back as the assistant's message, why it stopped and what it spent.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Turn {
    pub text: String,
    pub calls: Vec<(String, String, Json)>,
    pub content: Vec<Json>,
    pub stop: String,
    pub tokens: BTreeMap<String, i64>,
}

/// A call to the model under way, awaited on the agent's runtime.
pub type Pending<'a, T> = Pin<Box<dyn Future<Output = T> + Send + 'a>>;

/// A LANGUAGE MODEL, as a package asks it: a conversation's turn, or one call, each awaited as a task of the asking
/// package's. A test stands one in, answering at once.
pub trait Model: Send + Sync {
    /// Which model, for what is said of its use.
    fn name(&self) -> Option<String> {
        None
    }

    fn converse<'a>(
        &'a self,
        system: &'a [String],
        messages: &'a [Json],
        tools: &'a [Json],
        last: bool,
    ) -> Pending<'a, Result<Turn, Failure>>;

    fn ask<'a>(&'a self, system: &'a str, text: &'a str) -> Pending<'a, Result<Answer, Failure>>;
}

/// A language model reached over the Messages API: which, where, and with what key.
pub struct Anthropic {
    pub name: String,
    key: String,
    pub url: String,
    pub max_tokens: u32,
    /// How often a failing API is asked again (`llm:retries`).
    pub retries: u32,
    client: reqwest::Client,
}

/// What this family's ontology states of a figure where no role is read: a model made by a test.
fn defaulted(term: &str) -> f64 {
    crate::DEFAULTS
        .figure(term)
        .expect("the llm family's ontology states a default for each of its figures")
}

impl Anthropic {
    pub fn new(name: &str, key: &str, url: &str) -> Self {
        Anthropic {
            name: name.to_string(),
            key: key.to_string(),
            url: url.trim_end_matches('/').to_string(),
            max_tokens: 1024,
            retries: 0,
            client: reqwest::Client::new(),
        }
        .paced(defaulted(crate::CALLED_WITHIN_S), defaulted(crate::RETRIES) as u32)
    }

    /// The model answering at `url` that the environment names and holds the key of, or none where it names none —
    /// said once.
    /// The model called within `within_s` real seconds a call (`llm:calledWithinS`) and asked again `retries`
    /// times where it fails (`llm:retries`): the asking role's figures.
    pub fn paced(mut self, within_s: f64, retries: u32) -> Self {
        match reqwest::Client::builder()
            .timeout(Duration::from_secs_f64(within_s))
            .user_agent("orexis-agent")
            .build()
        {
            Ok(client) => self.client = client,
            Err(e) => log::warn!("the model is called with no timeout: {e}"),
        }
        self.retries = retries;
        self
    }

    pub fn from_environ(url: &str, env: &dyn Fn(&str) -> Option<String>) -> Option<Self> {
        let (key, name) = (
            env("MODEL_API_KEY").filter(|k| !k.is_empty()),
            env("MODEL_NAME").filter(|n| !n.is_empty()),
        );
        let (Some(key), Some(name)) = (key, name) else {
            log::warn!("no model: MODEL_API_KEY and MODEL_NAME are not both set");
            return None;
        };
        Some(Anthropic::new(&name, &key, url))
    }

    /// One request, asked again where the API is overloaded, rate-limited, timing out or unreachable, with the SDK's
    /// backoff between.
    async fn post(&self, body: &Json) -> Result<Json, Failure> {
        let mut attempt = 0;
        loop {
            let reply = self
                .client
                .post(format!("{}/v1/messages", self.url))
                .header("x-api-key", &self.key)
                .header("anthropic-version", VERSION)
                .header("content-type", "application/json")
                .body(body.to_string())
                .send()
                .await;
            let failure = match reply {
                Ok(response) if response.status().is_success() => {
                    let text = response.text().await.map_err(|e| Failure::Other(e.to_string()))?;
                    return serde_json::from_str(&text).map_err(|e| Failure::Other(e.to_string()));
                }
                Ok(response) => {
                    let code = response.status().as_u16();
                    let said = response.text().await.unwrap_or_default();
                    let said = format!("Error code: {code} - {said}");
                    match code {
                        401 | 403 => return Err(Failure::Refused(said)),
                        408 | 409 => Failure::Other(said),
                        429 => Failure::RateLimited(said),
                        c if c >= 500 => Failure::Overloaded(said),
                        _ => return Err(Failure::Other(said)),
                    }
                }
                Err(e) => Failure::Unreachable(e.to_string()),
            };
            if attempt >= self.retries {
                return Err(failure);
            }
            //  THE SDK'S BACKOFF: half a second doubled each time, at most eight.
            tokio::time::sleep(Duration::from_secs_f64((0.5 * 2f64.powi(attempt as i32)).min(8.0))).await;
            attempt += 1;
        }
    }
}

/// What one request spent, by the API's own names; nought for a name its reply does not carry.
fn tokens(reply: &Json) -> BTreeMap<String, i64> {
    TOKENS
        .iter()
        .map(|k| {
            (
                k.to_string(),
                reply
                    .get("usage")
                    .and_then(|u| u.get(*k))
                    .and_then(Json::as_i64)
                    .unwrap_or(0),
            )
        })
        .collect()
}

/// The conversation with its last block marked for the cache, so the next turn reads all of it from there — a copy,
/// since a mark left behind on every turn would pass the API's four.
pub fn cached(messages: &[Json]) -> Vec<Json> {
    let Some((last, rest)) = messages.split_last() else {
        return Vec::new();
    };
    let mut last = last.clone();
    let mut blocks: Vec<Json> = match last.get("content") {
        Some(Json::String(s)) => vec![json!({"type": "text", "text": s})],
        Some(Json::Array(a)) => a.clone(),
        _ => Vec::new(),
    };
    if let Some(block) = blocks.last_mut() {
        block["cache_control"] = json!({"type": "ephemeral"});
    }
    last["content"] = Json::Array(blocks);
    rest.iter().cloned().chain(std::iter::once(last)).collect()
}

/// The body of one turn: the system prompt in blocks, every one but the last cached, the conversation, and the tools,
/// none to be chosen on the last turn.
pub fn turn_body(
    model: &str,
    max_tokens: u32,
    system: &[String],
    messages: &[Json],
    tools: &[Json],
    last: bool,
) -> Json {
    let mut blocks: Vec<Json> = system
        .iter()
        .filter(|t| !t.is_empty())
        .map(|t| json!({"type": "text", "text": t}))
        .collect();
    if blocks.len() > 1 {
        let n = blocks.len();
        blocks[n - 2]["cache_control"] = json!({"type": "ephemeral"});
    }
    let mut body = json!({"model": model, "max_tokens": max_tokens, "system": blocks, "messages": cached(messages)});
    if !tools.is_empty() {
        body["tools"] = Json::Array(tools.to_vec());
        body["tool_choice"] = json!({"type": if last { "none" } else { "auto" }});
    }
    body
}

impl Model for Anthropic {
    fn name(&self) -> Option<String> {
        Some(self.name.clone())
    }

    fn converse<'a>(
        &'a self,
        system: &'a [String],
        messages: &'a [Json],
        tools: &'a [Json],
        last: bool,
    ) -> Pending<'a, Result<Turn, Failure>> {
        Box::pin(async move {
            let reply = self
                .post(&turn_body(&self.name, self.max_tokens, system, messages, tools, last))
                .await?;
            Ok(turn_of(&reply))
        })
    }

    fn ask<'a>(&'a self, system: &'a str, text: &'a str) -> Pending<'a, Result<Answer, Failure>> {
        Box::pin(async move {
            let body = json!({"model": self.name, "max_tokens": self.max_tokens, "system": system,
                              "messages": [{"role": "user", "content": text}]});
            Ok(answer_of(&self.post(&body).await?))
        })
    }
}

/// What a turn's reply says: its text, each tool it called and the content to hand back, why it stopped and what it
/// spent.
fn turn_of(reply: &Json) -> Turn {
    let mut turn = Turn {
        stop: reply
            .get("stop_reason")
            .and_then(Json::as_str)
            .unwrap_or_default()
            .to_string(),
        tokens: tokens(reply),
        ..Turn::default()
    };
    for block in reply
        .get("content")
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default()
    {
        match block.get("type").and_then(Json::as_str) {
            Some("text") => {
                let text = block.get("text").and_then(Json::as_str).unwrap_or_default();
                turn.text += text;
                turn.content.push(json!({"type": "text", "text": text}));
            }
            Some("tool_use") => {
                let (id, name) = (
                    block.get("id").and_then(Json::as_str).unwrap_or_default().to_string(),
                    block.get("name").and_then(Json::as_str).unwrap_or_default().to_string(),
                );
                let input = block
                    .get("input")
                    .cloned()
                    .filter(|i| !i.is_null())
                    .unwrap_or(json!({}));
                turn.content
                    .push(json!({"type": "tool_use", "id": id, "name": name, "input": input}));
                turn.calls.push((id, name, input));
            }
            _ => {}
        }
    }
    turn
}

/// What one call's reply says: its text, each tool it called, and what it spent.
fn answer_of(reply: &Json) -> Answer {
    let mut answer = Answer {
        tokens: tokens(reply),
        ..Answer::default()
    };
    for block in reply
        .get("content")
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default()
    {
        match block.get("type").and_then(Json::as_str) {
            Some("text") => answer.text += block.get("text").and_then(Json::as_str).unwrap_or_default(),
            Some("tool_use") => answer.calls.push((
                block.get("name").and_then(Json::as_str).unwrap_or_default().to_string(),
                block.get("input").cloned().unwrap_or(json!({})),
            )),
            _ => {}
        }
    }
    answer
}

#[cfg(test)]
mod tests {
    //! Held to `agent/translation/tests/test_model.py`.

    use super::*;

    #[test]
    fn a_turn_marks_the_conversations_last_block_for_the_cache_and_leaves_the_conversation_unmarked() {
        let messages = vec![
            json!({"role": "user", "content": "the forecast?"}),
            json!({"role": "assistant", "content": [{"type": "tool_use", "id": "c0", "name": "query", "input": {}}]}),
            json!({"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c0", "content": "(no rows)"}]}),
        ];
        let body = turn_body(
            "m",
            1024,
            &["instructions".into(), "briefing".into()],
            &messages,
            &[],
            false,
        );
        let sent = body["messages"].as_array().unwrap();
        assert_eq!(
            sent.last().unwrap()["content"].as_array().unwrap().last().unwrap()["cache_control"],
            json!({"type": "ephemeral"})
        );
        assert_eq!(&sent[..2], &messages[..2]);
        assert!(
            messages[2]["content"][0].get("cache_control").is_none(),
            "the mark is the request's"
        );
        assert_eq!(
            body["system"][0]["cache_control"],
            json!({"type": "ephemeral"}),
            "all but the last block cached"
        );
        assert!(body["system"][1].get("cache_control").is_none());
        assert!(body.get("tools").is_none() && body.get("tool_choice").is_none());
        let one = turn_body(
            "m",
            1024,
            &["instructions".into()],
            &messages[..1],
            &[json!({"name": "query"})],
            true,
        );
        assert_eq!(
            one["messages"],
            json!([{"role": "user", "content": [{"type": "text", "text": "the forecast?", "cache_control": {"type": "ephemeral"}}]}])
        );
        assert_eq!(
            one["tool_choice"],
            json!({"type": "none"}),
            "the last turn answers in words"
        );
    }

    #[test]
    fn the_environment_names_the_model_or_there_is_none() {
        let url = "https://a.example/";
        assert!(Anthropic::from_environ(url, &|_| None).is_none());
        assert!(Anthropic::from_environ(url, &|k| (k == "MODEL_API_KEY").then(|| "k".into())).is_none());
        let env = |k: &str| match k {
            "MODEL_API_KEY" => Some("k".to_string()),
            "MODEL_NAME" => Some("claude-x".to_string()),
            _ => None,
        };
        let model = Anthropic::from_environ(url, &env).unwrap();
        assert_eq!(
            (model.name.as_str(), model.url.as_str()),
            ("claude-x", "https://a.example")
        );
    }

    #[test]
    fn a_failure_is_said_by_its_class_in_a_persons_terms() {
        assert_eq!(why_not(&Failure::Refused("401".into())), "its model refused its key");
        assert_eq!(
            why_not(&Failure::RateLimited("429".into())),
            "its model is asked too often just now; try again in a minute"
        );
        assert_eq!(
            why_not(&Failure::Overloaded("529".into())),
            "its model is overloaded just now; try again in a minute"
        );
        assert_eq!(
            why_not(&Failure::Unreachable("dns".into())),
            "its model could not be reached"
        );
        assert_eq!(
            why_not(&Failure::Other("boom".into())),
            "its model would not answer (boom)"
        );
    }
}
