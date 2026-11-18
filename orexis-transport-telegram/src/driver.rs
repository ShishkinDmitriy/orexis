//! THE TELEGRAM DRIVER, as `agent/transport/telegram/driver.py` keeps it: an agent's own bot over the Bot API.
//!
//! **THE BOT IS THE AGENT'S.** It is the account the agent speaks through (`telegram:hasBot`), its token
//! `TELEGRAM_BOT_TOKEN`, environment, and where the API answers the world's derived deployment's word of the bot.
//!
//! **IT POLLS.** `getUpdates` from the offset after the last update seen, awaited as a Tokio task; every text message
//! waits in the inbox, its channel the chat's id. `handle` finds the `telegram:Chat` the world names by that id and
//! the person by the user id they wrote as, and says the prose; a chat the world names none of is dropped and said
//! once.
//!
//! **IT SAYS WHOM A GROUP'S WORDS WERE FOR**: words tagging the bot or replying to one of its messages are addressed to
//! this agent; words tagging or replying to someone else and not the bot are addressed to them. Which account is the
//! bot's own is asked of the API (`getMe`) before the first poll. In a chat with one person nothing is said.
//!
//! **IT SENDS.** `say` posts `sendMessage` to a chat the world names by its id, replying to the message the words
//! answer, or `sendChatAction` with `typing` where the words say only that the agent is writing. What it is told is
//! posted by one Tokio task in the order it was told, so a long answer kept as several messages arrives as it was said.

use std::collections::{BTreeSet, VecDeque};
use std::future::Future;
use std::pin::Pin;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use oxigraph::model::Literal;
use oxsdatatypes::DateTime;
use serde_json::{Value as Json, json};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{BELIEF, local_of};
use orexis::store::{Store, Within, iri, value};
use orexis_transport::Inbox;
use orexis_transport::chat::Words;

pub const TELEGRAM_URL: &str = "https://api.telegram.org";
/// WHAT HOLDS WHERE NO ROLE SAYS HOW OFTEN: the defaults this transport's ontology states (`sh:defaultValue`).
pub static DEFAULTS: std::sync::LazyLock<orexis::shape::Defaults> =
    std::sync::LazyLock::new(|| orexis::shape::Defaults::of("the telegram transport", include_str!("../ontology.ttl")));

/// A FIGURE OF THE ROLE THIS PACKAGE IS LOADED FOR: what a role the self plays says of `term` in the agent's self
/// graph, read by this package's own query, and where no role says it the default this ontology states. Two
/// answers are never picked between: several, or one that is no number, is the default, said in the log.
pub fn figure_of(store: &orexis::store::Store, term: &str) -> Result<f64, orexis::Error> {
    use orexis::bind::{Value, bind};
    use orexis::store::{Within, value};
    let selves = store.graphs_of(&[orexis::ontology::SELF_GRAPH], &Within::default())?;
    let selves: Vec<&str> = selves.iter().map(String::as_str).collect();
    let text = bind(
        "PREFIX orexis: <http://example.org/orexis#>
            SELECT DISTINCT ?n WHERE { ?me a orexis:Self ; orexis:plays ?role . ?role $figure ?n }",
        &[("figure", Value::iri(term))],
    )?;
    let said: Vec<String> = store
        .rows(&text, &selves)?
        .iter()
        .filter_map(|row| value(row, "n"))
        .collect();
    if let [one] = said.as_slice()
        && let Ok(figure) = one.parse::<f64>()
    {
        return Ok(figure);
    }
    let default = DEFAULTS.figure(term)?;
    if !said.is_empty() {
        log::warn!(
            "the self's roles say {} for {}: the default, {default}, holds",
            said.join(", "),
            orexis::ontology::local_of(term)
        );
    }
    Ok(default)
}
/// HOW LONG ONE CALL OF THE BOT API MAY TAKE, in real seconds: a figure a role states.
pub const CALLED_WITHIN_S: &str = "http://example.org/orexis/telegram#calledWithinS";

/// Where the bot `me` speaks through answers, as the world's deployment graph says, or None where it says nothing.
pub fn answers(beliefs: &Store, me: &str) -> Result<Option<String>, Error> {
    /// WHERE THE SELF'S BOT ANSWERS: the `schema:url` the world's deployment graph states of the bot the society says
    /// the agent speaks through.
    const ANSWERS_Q: &str = "PREFIX schema: <https://schema.org/>
        PREFIX telegram: <http://example.org/orexis/telegram#>
        SELECT ?url WHERE { $me telegram:hasBot ?bot . ?bot schema:url ?url } ORDER BY ?url";
    let mut known = beliefs.graphs_of(&[orexis::ontology::BELIEF], &orexis::store::Within::common())?;
    known.extend(beliefs.graphs_of(&[orexis::ontology::DEPLOYMENT], &orexis::store::Within::common())?);
    let known: Vec<&str> = known.iter().map(String::as_str).collect();
    let text = orexis::bind::bind(ANSWERS_Q, &[("me", orexis::bind::Value::iri(me))])?;
    Ok(beliefs
        .rows(&text, &known)?
        .iter()
        .find_map(|row| orexis::store::value(row, "url"))
        .filter(|url| !url.is_empty()))
}

/// HOW OFTEN THE BOT IS POLLED, in real seconds: what a role the self plays says in the agent's self graph
/// (`telegram:polledEveryS`), and the default the transport's ontology states where none says.
pub fn polled_every_s(beliefs: &Store) -> Result<f64, Error> {
    let mut known = beliefs.graphs_of(&[orexis::ontology::SELF_GRAPH], &orexis::store::Within::default())?;
    known.extend(beliefs.graphs_of(&[orexis::ontology::ONTOLOGY], &orexis::store::Within::default())?);
    let known: Vec<&str> = known.iter().map(String::as_str).collect();
    //  ONE QUERY: what a role the self plays says or, where none says, the default the transport's ontology states.
    beliefs
        .rows(
            "PREFIX orexis: <http://example.org/orexis#>
             PREFIX sh: <http://www.w3.org/ns/shacl#>
             PREFIX telegram: <http://example.org/orexis/telegram#>
             SELECT (COALESCE(?said, ?own) AS ?every) WHERE { \
             OPTIONAL { ?me a orexis:Self ; orexis:plays ?role . \
                        ?role telegram:polledEveryS ?said FILTER(?said > 0) } \
             OPTIONAL { ?shape sh:property [ sh:path telegram:polledEveryS ; \
                        sh:defaultValue ?own ] } } ORDER BY ?every",
            &known,
        )?
        .iter()
        .find_map(|row| orexis::store::value(row, "every")?.parse::<f64>().ok())
        .ok_or_else(|| Error::Document("the telegram transport's ontology states no default for polledEveryS".into()))
}

/// A call under way: the API's JSON answer, or why there is none.
pub type Answered = Pin<Box<dyn Future<Output = Result<Json, String>> + Send>>;
/// The Bot API as the driver calls it: a method's URL and its JSON body, answered with JSON.
pub type Call = Arc<dyn Fn(String, Json) -> Answered + Send + Sync>;

/// A call that answers each method at once with what `answer` says of its URL and body: a test's Bot API.
pub fn answering(answer: impl Fn(&str, &Json) -> Result<Json, String> + Send + Sync + 'static) -> Call {
    Arc::new(move |url: String, body: Json| {
        let answered = answer(&url, &body);
        Box::pin(async move { answered })
    })
}

/// The API as a deployed agent calls it, over rustls, a call given up after `within_s` real seconds.
pub fn post(within_s: f64) -> Result<Call, Error> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs_f64(within_s))
        .user_agent("orexis-agent")
        .build()
        .map_err(|e| Error::Evaluation(format!("no client for the Bot API: {e}")))?;
    Ok(Arc::new(move |url: String, body: Json| {
        let client = client.clone();
        Box::pin(async move {
            //  THE API ANSWERS A REFUSAL IN JSON, `ok` false with its description, so any status is read.
            let response = client
                .post(&url)
                .header(reqwest::header::CONTENT_TYPE, "application/json")
                .body(body.to_string())
                .send()
                .await
                .map_err(|e| hidden(&e.to_string()))?;
            let text = response.text().await.map_err(|e| hidden(&e.to_string()))?;
            serde_json::from_str(&text).map_err(|e| e.to_string())
        })
    }))
}

/// `text` with the token cut out of every Bot API url in it: a client's error names the url it called, and the token
/// is a path segment of it (`/bot<token>/<method>`), so said as it stands the error would hand the bot to anyone who
/// reads the log or the journal.
pub fn hidden(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut rest = text;
    while let Some(at) = rest.find("/bot") {
        let (before, after) = rest.split_at(at + 4);
        out.push_str(before);
        let end = after
            .find(|c: char| c == '/' || c.is_whitespace() || c == '"' || c == ')')
            .unwrap_or(after.len());
        if end > 0 {
            out.push_str("<token>");
        }
        rest = &after[end..];
    }
    out.push_str(rest);
    out
}

/// What the bot knows of itself and its polling, shared with the polling thread.
#[derive(Default)]
struct Polled {
    offset: Option<i64>,
    bot: Option<(String, String)>,
}

/// The bot's side of the API: where it answers, with what token, by what call — clonable onto a task.
#[derive(Clone)]
pub struct Api {
    pub url: String,
    token: String,
    pub call: Call,
    polled: Arc<Mutex<Polled>>,
    polling: Arc<tokio::sync::Mutex<()>>,
    /// What the agent said and the API has yet to take, oldest first: posted by one task while any is left.
    outbox: Arc<Mutex<VecDeque<(String, Json)>>>,
}

impl Api {
    fn method(&self, name: &str) -> String {
        format!("{}/bot{}/{name}", self.url, self.token)
    }

    /// The bot's own user id and username, asked of the API once.
    pub async fn whoami(&self) -> Result<(String, String), String> {
        if let Some(bot) = self.bot() {
            return Ok(bot);
        }
        let reply = (self.call)(self.method("getMe"), json!({})).await?;
        let found = if reply.get("ok").and_then(Json::as_bool).unwrap_or(true) {
            reply.get("result").cloned().unwrap_or(Json::Null)
        } else {
            Json::Null
        };
        let Some(id) = found.get("id") else {
            let said = reply.get("description").cloned().unwrap_or(reply.clone());
            return Err(format!("getMe told nothing of the bot: {said}"));
        };
        let bot = (
            text_of(id),
            found
                .get("username")
                .and_then(Json::as_str)
                .unwrap_or_default()
                .to_lowercase(),
        );
        self.polled.lock().unwrap().bot = Some(bot.clone());
        Ok(bot)
    }

    /// The bot, once `getMe` has told it.
    pub fn bot(&self) -> Option<(String, String)> {
        self.polled.lock().unwrap().bot.clone()
    }

    /// Every text message since the last poll, as its chat's id and what it says — who wrote it, the words, whom a
    /// group's words were for and its id; an update that is no text message is passed over, and every update seen is
    /// confirmed by the next poll's offset.
    pub async fn updates(&self) -> Result<Vec<(String, Json)>, String> {
        let (me, username) = self.whoami().await?;
        let mut body = json!({"timeout": 0, "allowed_updates": ["message"]});
        let offset = self.polled.lock().unwrap().offset;
        if let Some(offset) = offset {
            body["offset"] = json!(offset);
        }
        let reply = (self.call)(self.method("getUpdates"), body).await?;
        let mut out = Vec::new();
        let ok = reply.get("ok").and_then(Json::as_bool).unwrap_or(true);
        let results = if ok {
            reply
                .get("result")
                .and_then(Json::as_array)
                .cloned()
                .unwrap_or_default()
        } else {
            Vec::new()
        };
        for update in results {
            let id = update.get("update_id").and_then(Json::as_i64).unwrap_or(0);
            {
                let mut polled = self.polled.lock().unwrap();
                polled.offset = Some(polled.offset.unwrap_or(0).max(id + 1));
            }
            let message = update.get("message").cloned().unwrap_or(Json::Null);
            let (Some(text), Some(chat)) = (message.get("text").and_then(Json::as_str), message.get("chat")) else {
                continue;
            };
            let Some(chat_id) = chat.get("id").filter(|c| !c.is_null()) else {
                continue;
            };
            let sender = message.get("from").and_then(|f| f.get("id")).map(text_of);
            let number = message.get("message_id").map(text_of);
            let addressed = if chat.get("type").and_then(Json::as_str) == Some("private") {
                Json::Null
            } else {
                match addressed(&message, &me, &username) {
                    Some(b) => json!(b),
                    None => Json::Null,
                }
            };
            out.push((
                text_of(chat_id),
                json!({"from": sender, "text": text.trim(), "addressed": addressed, "message": number}),
            ));
        }
        Ok(out)
    }

    /// The agent's words posted by `method` with `body`, after whatever it said before and the API has yet to take: the
    /// first left starts the one task that posts them, oldest first, until none is left.
    fn tell(&self, method: &str, body: Json, me: &str) {
        let mut outbox = self.outbox.lock().unwrap();
        outbox.push_back((method.to_string(), body));
        if outbox.len() > 1 {
            return;
        }
        let (api, me) = (self.clone(), me.to_string());
        tokio::spawn(async move {
            let mut next = api.outbox.lock().unwrap().front().cloned();
            while let Some((method, body)) = next {
                api.posted(&method, body, &me).await;
                next = {
                    let mut outbox = api.outbox.lock().unwrap();
                    outbox.pop_front();
                    outbox.front().cloned()
                };
            }
        });
    }

    /// `method` posted with `body`; whether the API took it, what it would not said in the log.
    async fn posted(&self, method: &str, body: Json, me: &str) -> bool {
        let reply = match (self.call)(self.method(method), body).await {
            Ok(r) => r,
            Err(e) => {
                log::warn!("{}: the bot would not answer {method}: {e}", local_of(me));
                return false;
            }
        };
        if !reply.get("ok").and_then(Json::as_bool).unwrap_or(true) {
            log::warn!(
                "{}: telegram would not take a {method}: {}",
                local_of(me),
                reply.get("description").cloned().unwrap_or(reply.clone())
            );
            return false;
        }
        true
    }
}

/// Whom a group's message was for, the bot being the user `me` named `username`: true where it tags the bot or replies
/// to it, false where it tags or replies to someone else and not the bot, none where it does neither. An entity's
/// offset and length are in UTF-16 code units, as the Bot API counts them.
fn addressed(message: &Json, me: &str, username: &str) -> Option<bool> {
    let units: Vec<u16> = message
        .get("text")
        .and_then(Json::as_str)
        .unwrap_or_default()
        .encode_utf16()
        .collect();
    let (mut mine, mut other) = (false, false);
    for entity in message
        .get("entities")
        .and_then(Json::as_array)
        .cloned()
        .unwrap_or_default()
    {
        let start = entity.get("offset").and_then(Json::as_u64).unwrap_or(0) as usize;
        let length = entity.get("length").and_then(Json::as_u64).unwrap_or(0) as usize;
        let piece = String::from_utf16_lossy(units.get(start..(start + length).min(units.len())).unwrap_or(&[]));
        let tagged = match entity.get("type").and_then(Json::as_str) {
            Some("text_mention") => entity.get("user").and_then(|u| u.get("id")).map(text_of).as_deref() == Some(me),
            Some("mention") => piece.trim_start_matches('@').to_lowercase() == username,
            Some("bot_command") if piece.contains('@') => {
                piece.split_once('@').map(|(_, b)| b.to_lowercase()).as_deref() == Some(username)
            }
            _ => continue,
        };
        mine |= tagged;
        other |= !tagged;
    }
    if let Some(replied) = message
        .get("reply_to_message")
        .and_then(|r| r.get("from"))
        .and_then(|f| f.get("id"))
    {
        let to_me = text_of(replied) == me;
        mine |= to_me;
        other |= !to_me;
    }
    if mine {
        Some(true)
    } else if other {
        Some(false)
    } else {
        None
    }
}

/// A JSON number or string as the text it is, as Python's `str` of it.
fn text_of(value: &Json) -> String {
    match value {
        Json::String(s) => s.clone(),
        other => other.to_string(),
    }
}

/// One agent's bot: polled for what is written to it, told what the agent says.
pub struct Telegram {
    beliefs: Store,
    pub me: String,
    pub api: Api,
    pub polled_every_s: f64,
    pub inbox: Inbox,
    unknown: BTreeSet<String>,
}

impl Telegram {
    /// The store the member keeps what it carries in.
    pub fn beliefs(&self) -> &Store {
        &self.beliefs
    }

    pub fn new(beliefs: &Store, me: &str, token: &str, url: &str, call: Call) -> Self {
        Telegram {
            beliefs: beliefs.clone(),
            me: me.to_string(),
            api: Api {
                url: url.trim_end_matches('/').to_string(),
                token: token.to_string(),
                call,
                polled: Arc::default(),
                polling: Arc::default(),
                outbox: Arc::default(),
            },
            //  UNTIL IT CONNECTS and reads what a role says, as often as the transport's ontology states.
            polled_every_s: DEFAULTS
                .figure("http://example.org/orexis/telegram#polledEveryS")
                .expect("the transport's ontology states how often it polls"),
            inbox: Inbox::default(),
            unknown: BTreeSet::new(),
        }
    }

    /// A bot that reaches nothing: every call refused, for an agent that is not deployed and was handed none.
    pub fn unreachable(beliefs: &Store, me: &str) -> Self {
        let call = answering(|_, _| Err("an agent that is not deployed reaches no bot".to_string()));
        Self::new(beliefs, me, "", "", call)
    }

    /// The bot brought up: where it answers is the world's deployment graph's to say, the Bot API's own address
    /// where it says nothing, and its token the environment's. Refused where it holds no token.
    pub fn connect(beliefs: &Store, me: &str, env: &dyn Fn(&str) -> Option<String>) -> Result<Self, Error> {
        let token = env("TELEGRAM_BOT_TOKEN").filter(|t| !t.is_empty()).ok_or_else(|| {
            Error::Evaluation(
                "no TELEGRAM_BOT_TOKEN in the environment — this agent speaks through a bot and holds no token for it; \
                 write secrets/<agent>/telegram.env and regenerate the compose file"
                    .into(),
            )
        })?;
        let url = answers(beliefs, me)?.unwrap_or_else(|| TELEGRAM_URL.to_string());
        let mut bot = Telegram::new(beliefs, me, &token, &url, post(figure_of(beliefs, CALLED_WITHIN_S)?)?);
        bot.polled_every_s = polled_every_s(beliefs)?;
        Ok(bot)
    }

    /// Ask for what was written since the last poll, awaited as a Tokio task, one poll at a time.
    pub fn poll(&self) {
        let Ok(one) = self.api.polling.clone().try_lock_owned() else {
            return;
        };
        let (api, inbox, me) = (self.api.clone(), self.inbox.clone(), self.me.clone());
        tokio::spawn(async move {
            let _one = one;
            match api.updates().await {
                Ok(found) => {
                    for (channel, said) in found {
                        inbox.deliver(&channel, said.to_string().as_bytes(), None);
                    }
                }
                Err(e) => log::warn!("{}: the bot would not answer: {e}", local_of(&me)),
            }
        });
    }

    fn common(&self) -> Result<Vec<String>, Error> {
        self.beliefs.graphs_of(&[BELIEF], &Within::common())
    }

    /// Whether `channel` is a chat on Telegram, one this bot carries.
    pub fn carries(&self, channel: &str) -> Result<bool, Error> {
        const CARRIES_Q: &str = "PREFIX telegram: <http://example.org/orexis/telegram#> ASK { $chat a telegram:Chat }";
        let common = self.common()?;
        let common: Vec<&str> = common.iter().map(String::as_str).collect();
        self.beliefs
            .ask(&bind(CARRIES_Q, &[("chat", Value::iri(channel))])?, &common)
    }

    /// A message on a chat the world names by its id: the chat, and its words, by the person writing as the user; none
    /// where the world names no chat by that id.
    pub fn handle(&mut self, channel: &str, payload: &[u8], _at: DateTime) -> Result<Option<(String, Words)>, Error> {
        const CHAT_Q: &str = "PREFIX telegram: <http://example.org/orexis/telegram#>
            SELECT ?chat WHERE { ?chat a telegram:Chat ; telegram:chatId ?id FILTER (STR(?id) = $id) }";
        const USER_Q: &str = "PREFIX telegram: <http://example.org/orexis/telegram#>
            SELECT ?person WHERE { ?person telegram:userId ?id FILTER (STR(?id) = $id) }";
        let common = self.common()?;
        let common: Vec<&str> = common.iter().map(String::as_str).collect();
        let literal = |s: &str| Value::Term(Literal::new_simple_literal(s).into());
        let chats = self
            .beliefs
            .rows(&bind(CHAT_Q, &[("id", literal(channel))])?, &common)?;
        let Some(chat) = chats.first().and_then(|r| iri(r, "chat")) else {
            if self.unknown.insert(channel.to_string()) {
                log::warn!(
                    "{}: a message in Telegram chat {channel}, which the world names in no chat: dropped",
                    local_of(&self.me)
                );
            }
            return Ok(None);
        };
        let said: Json = serde_json::from_slice(payload).map_err(|e| Error::Evaluation(e.to_string()))?;
        let sender = match said.get("from").and_then(Json::as_str) {
            Some(from) => self
                .beliefs
                .rows(&bind(USER_Q, &[("id", literal(from))])?, &common)?
                .first()
                .and_then(|r| iri(r, "person")),
            None => None,
        };
        Ok(Some((
            chat,
            Words {
                text: said.get("text").and_then(Json::as_str).unwrap_or_default().to_string(),
                from: sender,
                addressed: said.get("addressed").and_then(Json::as_bool),
                message: said.get("message").and_then(Json::as_str).map(str::to_string),
                ..Words::default()
            },
        )))
    }

    /// `method` told to the chat the world names `channel` by its id; false where it names none.
    fn told(&self, channel: &str, method: &str, body: Json) -> bool {
        const ID_Q: &str = "PREFIX telegram: <http://example.org/orexis/telegram#>
            SELECT ?id WHERE { $chat a telegram:Chat ; telegram:chatId ?id }";
        let Ok(common) = self.common() else { return false };
        let common: Vec<&str> = common.iter().map(String::as_str).collect();
        let Ok(text) = bind(ID_Q, &[("chat", Value::iri(channel))]) else {
            return false;
        };
        let Some(id) = self
            .beliefs
            .rows(&text, &common)
            .ok()
            .and_then(|r| r.first().and_then(|r| value(r, "id")))
        else {
            return false;
        };
        let mut body = body;
        body["chat_id"] = json!(id);
        self.api.tell(method, body, &self.me);
        true
    }
}

impl Telegram {
    /// `words` said on the chat `channel`: sent as a message, a reply where they name the words they answer, or the
    /// agent shown typing where they say only that it is writing, after what it said before. Whether the chat is one
    /// the world names; what the API would not take is said in the log.
    pub fn say(&mut self, channel: &str, words: &Words) -> bool {
        if words.writing {
            return self.told(channel, "sendChatAction", json!({"action": "typing"}));
        }
        let mut body = json!({"text": words.text});
        if let Some(reply) = words.reply.as_deref().and_then(|r| r.parse::<i64>().ok()) {
            body["reply_parameters"] = json!({"message_id": reply, "allow_sending_without_reply": true});
        }
        self.told(channel, "sendMessage", body)
    }
}

#[cfg(test)]
mod tests {
    //! The driver over a stand-in Bot API, held to `agent/transport/telegram/tests/test_driver.py`.

    use std::path::Path;

    use super::*;

    #[test]
    fn a_bot_api_url_in_an_error_says_no_token() {
        assert_eq!(
            hidden("https://api.telegram.org/bot123:ABC-def_g/getUpdates: Connection Failed: timed out"),
            "https://api.telegram.org/bot<token>/getUpdates: Connection Failed: timed out"
        );
        assert_eq!(hidden("no url here"), "no url here");
        assert_eq!(
            hidden("https://x/bot42:k and https://x/bot42:k/sendMessage"),
            "https://x/bot<token> and https://x/bot<token>/sendMessage"
        );
    }
    use orexis::snapshots::{now, stand_in};

    const TEST: &str = "http://example.org/test#";
    const BOT_ID: i64 = 900;

    type Calls = Arc<Mutex<Vec<(String, Json)>>>;

    /// The Bot API: `getUpdates` answers what is queued and forgets it, anything else is kept.
    fn api(updates: Arc<Mutex<Vec<Json>>>) -> (Call, Calls) {
        let calls: Calls = Arc::default();
        let kept = calls.clone();
        let call = answering(move |url, body| {
            let name = url.rsplit('/').next().unwrap().to_string();
            kept.lock().unwrap().push((name.clone(), body.clone()));
            Ok(match name.as_str() {
                "getUpdates" => json!({"ok": true, "result": std::mem::take(&mut *updates.lock().unwrap())}),
                "getMe" => json!({"ok": true, "result": {"id": BOT_ID, "is_bot": true, "username": "Keeper_Home_bot"}}),
                _ => json!({"ok": true, "result": {}}),
            })
        });
        (call, calls)
    }

    fn message(update: i64, chat: i64, text: &str, user: i64, more: Json) -> Json {
        let kind = if chat > 0 { "private" } else { "group" };
        let mut message =
            json!({"message_id": update, "chat": {"id": chat, "type": kind}, "from": {"id": user}, "text": text});
        if let Json::Object(more) = more {
            for (k, v) in more {
                message[k] = v;
            }
        }
        json!({"update_id": update, "message": message})
    }

    /// An entity over the first `piece` in `text`, in UTF-16 code units as the Bot API counts.
    fn tag(text: &str, piece: &str, kind: &str) -> Json {
        let start = text[..text.find(piece).unwrap()].encode_utf16().count();
        json!({"type": kind, "offset": start, "length": piece.encode_utf16().count()})
    }

    fn world() -> Store {
        stand_in(&Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/worlds/a_chat_on_telegram.trig"))
    }

    fn bot(store: &Store) -> (Telegram, Arc<Mutex<Vec<Json>>>, Calls) {
        let updates: Arc<Mutex<Vec<Json>>> = Arc::default();
        let (call, calls) = api(updates.clone());
        let bot = Telegram::new(store, &format!("{TEST}keeper"), "123:abc", TELEGRAM_URL, call);
        (bot, updates, calls)
    }

    /// Every task spawned so far run as far as it goes.
    async fn settled() {
        for _ in 0..8 {
            tokio::task::yield_now().await;
        }
    }

    fn said(user: &str, text: &str, addressed: Json, message: &str) -> Json {
        json!({"from": user, "text": text, "addressed": addressed, "message": message})
    }

    #[tokio::test]
    async fn updates_are_each_text_message_by_its_chats_id_and_the_offset_moves_past_them() {
        let store = world();
        let (bot, updates, calls) = bot(&store);
        *updates.lock().unwrap() = vec![
            message(10, 4242, " hello ", 111, json!({})),
            json!({"update_id": 11, "edited_message": {}}),
            message(12, -100, "hi all", 222, json!({})),
        ];
        assert_eq!(
            bot.api.updates().await.unwrap(),
            [
                ("4242".to_string(), said("111", "hello", Json::Null, "10")),
                ("-100".to_string(), said("222", "hi all", Json::Null, "12"))
            ]
        );
        assert!(bot.api.updates().await.unwrap().is_empty());
        let calls = calls.lock().unwrap();
        let offsets: Vec<Json> = calls
            .iter()
            .filter(|(n, _)| n == "getUpdates")
            .map(|(_, b)| b.get("offset").cloned().unwrap_or(Json::Null))
            .collect();
        assert_eq!(
            offsets,
            [Json::Null, json!(13)],
            "every update seen is confirmed by the next poll"
        );
        let names: Vec<&str> = calls.iter().map(|(n, _)| n.as_str()).collect();
        assert_eq!(
            names,
            ["getMe", "getUpdates", "getUpdates"],
            "the bot's own account, asked once"
        );
    }

    #[tokio::test]
    async fn in_a_group_words_that_tag_the_bot_or_reply_to_it_are_addressed_to_it_and_to_someone_else_not() {
        let store = world();
        let (bot, updates, _) = bot(&store);
        let tagged = "🌿 @keeper_home_bot is the door locked?";
        let other = "@anna_k what do you think?";
        let both = "@anna_k and @Keeper_Home_bot, look";
        let command = "/status@Keeper_Home_bot";
        let entities = |e: Vec<Json>| json!({"entities": e});
        *updates.lock().unwrap() = vec![
            message(
                1,
                -100,
                tagged,
                111,
                entities(vec![tag(tagged, "@keeper_home_bot", "mention")]),
            ),
            message(2, -100, other, 111, entities(vec![tag(other, "@anna_k", "mention")])),
            message(
                3,
                -100,
                both,
                111,
                entities(vec![
                    tag(both, "@anna_k", "mention"),
                    tag(both, "@Keeper_Home_bot", "mention"),
                ]),
            ),
            message(
                4,
                -100,
                "is it?",
                111,
                json!({"reply_to_message": {"message_id": 70, "from": {"id": BOT_ID, "is_bot": true}}}),
            ),
            message(
                5,
                -100,
                "is it?",
                111,
                json!({"reply_to_message": {"message_id": 71, "from": {"id": 222}}}),
            ),
            message(
                6,
                -100,
                command,
                111,
                entities(vec![tag(command, command, "bot_command")]),
            ),
            message(
                7,
                -100,
                "/status@other_bot",
                111,
                entities(vec![tag("/status@other_bot", "/status@other_bot", "bot_command")]),
            ),
            message(
                8,
                -100,
                "Kim, look",
                111,
                entities(vec![{
                    let mut t = tag("Kim, look", "Kim", "text_mention");
                    t["user"] = json!({"id": BOT_ID});
                    t
                }]),
            ),
            message(9, -100, "nobody tagged", 111, json!({})),
            message(
                10,
                4242,
                "@anna_k said so",
                111,
                entities(vec![tag("@anna_k said so", "@anna_k", "mention")]),
            ),
        ];
        let addressed: Vec<Json> = bot
            .api
            .updates()
            .await
            .unwrap()
            .iter()
            .map(|(_, s)| s["addressed"].clone())
            .collect();
        let t = Json::Bool(true);
        let f = Json::Bool(false);
        assert_eq!(
            addressed,
            [
                t.clone(),
                f.clone(),
                t.clone(),
                t.clone(),
                f.clone(),
                t.clone(),
                f,
                t,
                Json::Null,
                Json::Null
            ]
        );
    }

    #[tokio::test]
    async fn a_poll_delivers_each_message_to_the_inbox_and_an_api_refusing_is_asked_again() {
        let store = world();
        let (mut bot, updates, _) = bot(&store);
        *updates.lock().unwrap() = vec![message(1, 4242, "hello", 111, json!({}))];
        let good = bot.api.call.clone();
        bot.api.call = answering(|_, _| Ok(json!({"ok": false, "description": "Unauthorized"})));
        bot.poll();
        settled().await;
        assert!(bot.inbox.take().is_empty() && bot.api.bot().is_none());
        bot.api.call = good;
        bot.poll();
        settled().await;
        assert_eq!(bot.api.bot(), Some((BOT_ID.to_string(), "keeper_home_bot".to_string())));
        let arrived = bot.inbox.take();
        assert_eq!(arrived.len(), 1);
        let said: Json = serde_json::from_slice(&arrived[0].payload).unwrap();
        assert_eq!(
            (arrived[0].topic.as_str(), said),
            ("4242", self::said("111", "hello", Json::Null, "1"))
        );
    }

    #[test]
    fn a_message_is_words_on_the_chat_the_world_names_by_its_id_by_the_person_writing_as_the_user() {
        let store = world();
        let (mut bot, _, _) = bot(&store);
        let before = store.len().unwrap();
        let payload = |s: Json| s.to_string().into_bytes();
        let heard: Vec<(String, Words)> = [
            bot.handle("4242", &payload(said("111", "hello", Json::Null, "5")), now())
                .unwrap(),
            bot.handle("-100", &payload(said("999", "who am I", json!(true), "6")), now())
                .unwrap(),
        ]
        .into_iter()
        .flatten()
        .collect();
        type Said = (String, Option<String>, String, Option<bool>, Option<String>);
        let got: Vec<Said> = heard
            .iter()
            .map(|(channel, w)| {
                (
                    channel.clone(),
                    w.from.clone(),
                    w.text.clone(),
                    w.addressed,
                    w.message.clone(),
                )
            })
            .collect();
        assert_eq!(
            got,
            [
                (
                    format!("{TEST}anna_telegram"),
                    Some(format!("{TEST}anna")),
                    "hello".into(),
                    None,
                    Some("5".into())
                ),
                (
                    format!("{TEST}household_telegram"),
                    None,
                    "who am I".into(),
                    Some(true),
                    Some("6".into())
                ),
            ]
        );
        assert_eq!(store.len().unwrap(), before);
        for _ in 0..2 {
            assert!(
                bot.handle("777", &payload(said("111", "hi", Json::Null, "7")), now())
                    .unwrap()
                    .is_none(),
                "dropped"
            );
        }
    }

    #[tokio::test]
    async fn what_the_agent_says_goes_to_send_message_with_the_chats_id_and_writing_to_a_chat_action() {
        let store = world();
        let (mut bot, _, calls) = bot(&store);
        assert!(bot.say(&format!("{TEST}anna_telegram"), &Words::said("the fern is dry")));
        let reply = Words {
            reply: Some("42".into()),
            ..Words::said("it is")
        };
        assert!(bot.say(&format!("{TEST}household_telegram"), &reply));
        assert!(
            !bot.say(&format!("{TEST}anna_mail"), &Words::said("x")),
            "no Telegram chat is not this member's"
        );
        assert!(!bot.carries(&format!("{TEST}anna_mail")).unwrap());
        let writing = Words {
            writing: true,
            ..Words::default()
        };
        assert!(bot.say(&format!("{TEST}anna_telegram"), &writing));
        settled().await;
        assert_eq!(
            *calls.lock().unwrap(),
            [
                (
                    "sendMessage".to_string(),
                    json!({"chat_id": "4242", "text": "the fern is dry"})
                ),
                (
                    "sendMessage".to_string(),
                    json!({"chat_id": "-100", "text": "it is", "reply_parameters": {"message_id": 42, "allow_sending_without_reply": true}})
                ),
                (
                    "sendChatAction".to_string(),
                    json!({"chat_id": "4242", "action": "typing"})
                ),
            ]
        );
    }

    #[tokio::test]
    async fn an_api_that_fails_sends_nothing_and_connect_refuses_an_agent_with_no_token() {
        let store = world();
        //  THE TRANSPORT'S ONTOLOGY STATES HOW OFTEN WHERE NO ROLE DOES, as the package brings it.
        store
            .update(
                "PREFIX : <http://example.org/test#>
                 PREFIX sh: <http://www.w3.org/ns/shacl#>
                 PREFIX telegram: <http://example.org/orexis/telegram#>
                 INSERT DATA { GRAPH :ontology { [] sh:property \
                 [ sh:path telegram:polledEveryS ; sh:defaultValue 3 ] } }",
            )
            .unwrap();
        let (mut bot, _, _) = bot(&store);
        bot.api.call = answering(|_, _| Err("unreachable".into()));
        assert!(
            bot.say(&format!("{TEST}anna_telegram"), &Words::said("x")),
            "told to a chat the world names, and what the API would not take said in the log"
        );
        settled().await;
        assert!(bot.api.outbox.lock().unwrap().is_empty(), "and not told again");
        assert!(Telegram::connect(&store, &format!("{TEST}keeper"), &|_| None).is_err());
        let env = |k: &str| match k {
            "TELEGRAM_BOT_TOKEN" => Some("t".to_string()),
            _ => None,
        };
        let bot = Telegram::connect(&store, &format!("{TEST}keeper"), &env).unwrap();
        //  WHERE IT ANSWERS IS THE WORLD'S DEPLOYMENT'S TO SAY, and this world says nothing: the Bot API's own.
        assert_eq!(
            (bot.api.url.as_str(), bot.polled_every_s),
            (TELEGRAM_URL.trim_end_matches('/'), 3.0)
        );
    }
}
