//! THE TELEGRAM DRIVER, as `agent/transport/telegram/driver.py` keeps it: an agent's own bot over the Bot API.
//!
//! **THE BOT IS THE AGENT'S.** It is the account the agent speaks through (`telegram:hasBot`), its token
//! `TELEGRAM_BOT_TOKEN` and where the API answers `TELEGRAM_URL`, both environment.
//!
//! **IT POLLS.** `getUpdates` from the offset after the last update seen, on a thread of its own; every text message
//! waits in the inbox, its channel the chat's id. `handle` finds the `telegram:Chat` the world names by that id and
//! the person by the user id they wrote as, and says the prose; a chat the world names none of is dropped and said
//! once.
//!
//! **IT SAYS WHOM A GROUP'S WORDS WERE FOR**: words tagging the bot or replying to one of its messages are addressed to
//! this agent; words tagging or replying to someone else and not the bot are addressed to them. Which account is the
//! bot's own is asked of the API (`getMe`) before the first poll. In a chat with one person nothing is said.
//!
//! **IT SENDS.** `say_to` posts `sendMessage` to a chat the world names by its id, replying to the message it names;
//! `writing_in` posts `sendChatAction` with `typing`.

use std::collections::BTreeSet;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use oxigraph::model::Literal;
use oxsdatatypes::DateTime;
use serde_json::{Value as Json, json};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{BELIEF, local_of};
use orexis::store::{Store, Within, iri, value};
use orexis::transport::Inbox;
use orexis_speech::prose::{Carrier, Prose};

pub const TELEGRAM_URL: &str = "https://api.telegram.org";
pub const POLL_S: f64 = 3.0;
pub const TIMEOUT_S: u64 = 30;

const CHAT_Q: &str = "SELECT ?chat WHERE { ?chat a telegram:Chat ; telegram:chatId ?id FILTER (STR(?id) = $id) }";
const USER_Q: &str = "SELECT ?person WHERE { ?person telegram:userId ?id FILTER (STR(?id) = $id) }";
const ID_Q: &str = "SELECT ?id WHERE { $chat a telegram:Chat ; telegram:chatId ?id }";

/// The Bot API as the driver calls it: a method's URL and its JSON body, answered with JSON.
pub type Call = Arc<dyn Fn(&str, &Json) -> Result<Json, String> + Send + Sync>;
/// What runs a poll: on a thread of its own, or at once in a test.
pub type Spawn = Box<dyn Fn(Box<dyn FnOnce() + Send>) + Send + Sync>;

/// The API as a deployed agent calls it.
pub fn post() -> Call {
    let agent = ureq::AgentBuilder::new()
        .timeout(Duration::from_secs(TIMEOUT_S))
        .build();
    Arc::new(move |url, body| {
        let reply = agent
            .post(url)
            .set("content-type", "application/json")
            .send_string(&body.to_string());
        let response = match reply {
            Ok(r) => r,
            //  THE API ANSWERS A REFUSAL IN JSON, `ok` false with its description.
            Err(ureq::Error::Status(_, r)) => r,
            Err(e) => return Err(hidden(&e.to_string())),
        };
        let text = response.into_string().map_err(|e| hidden(&e.to_string()))?;
        serde_json::from_str(&text).map_err(|e| e.to_string())
    })
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

/// The bot's side of the API: where it answers, with what token, by what call — clonable onto a thread.
#[derive(Clone)]
pub struct Api {
    pub url: String,
    token: String,
    pub call: Call,
    polled: Arc<Mutex<Polled>>,
    polling: Arc<Mutex<()>>,
}

impl Api {
    fn method(&self, name: &str) -> String {
        format!("{}/bot{}/{name}", self.url, self.token)
    }

    /// The bot's own user id and username, asked of the API once.
    pub fn whoami(&self) -> Result<(String, String), String> {
        if let Some(bot) = self.polled.lock().unwrap().bot.clone() {
            return Ok(bot);
        }
        let reply = (self.call)(&self.method("getMe"), &json!({}))?;
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
    pub fn updates(&self) -> Result<Vec<(String, Json)>, String> {
        self.whoami()?;
        let mut body = json!({"timeout": 0, "allowed_updates": ["message"]});
        if let Some(offset) = self.polled.lock().unwrap().offset {
            body["offset"] = json!(offset);
        }
        let reply = (self.call)(&self.method("getUpdates"), &body)?;
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
                match self.addressed(&message)? {
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

    /// Whom a group's message was for: true where it tags the bot or replies to it, false where it tags or replies to
    /// someone else and not the bot, none where it does neither. An entity's offset and length are in UTF-16 code
    /// units, as the Bot API counts them.
    pub fn addressed(&self, message: &Json) -> Result<Option<bool>, String> {
        let (me, username) = self.whoami()?;
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
                Some("text_mention") => entity.get("user").and_then(|u| u.get("id")).map(text_of) == Some(me.clone()),
                Some("mention") => piece.trim_start_matches('@').to_lowercase() == username,
                Some("bot_command") if piece.contains('@') => {
                    piece.split_once('@').map(|(_, b)| b.to_lowercase()) == Some(username.clone())
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
        Ok(if mine {
            Some(true)
        } else if other {
            Some(false)
        } else {
            None
        })
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
    pub every: f64,
    pub spawn: Spawn,
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
            },
            every: POLL_S,
            spawn: Box::new(|work| {
                std::thread::spawn(work);
            }),
            inbox: Inbox::default(),
            unknown: BTreeSet::new(),
        }
    }

    /// The bot brought up from the environment: refused where it holds no token.
    pub fn connect(beliefs: &Store, me: &str, env: &dyn Fn(&str) -> Option<String>) -> Result<Self, Error> {
        let token = env("TELEGRAM_BOT_TOKEN").filter(|t| !t.is_empty()).ok_or_else(|| {
            Error::Evaluation(
                "no TELEGRAM_BOT_TOKEN in the environment — this agent speaks through a bot and holds no token for it; \
                 write secrets/<agent>/telegram.env and regenerate the compose file"
                    .into(),
            )
        })?;
        let url = env("TELEGRAM_URL")
            .filter(|u| !u.is_empty())
            .unwrap_or_else(|| TELEGRAM_URL.to_string());
        let mut bot = Telegram::new(beliefs, me, &token, &url, post());
        if let Some(every) = env("TELEGRAM_POLL_S").and_then(|s| s.parse().ok()) {
            bot.every = every;
        }
        Ok(bot)
    }

    /// Ask for what was written since the last poll, on a thread of its own, one poll at a time.
    pub fn poll(&self) {
        let (api, inbox, me) = (self.api.clone(), self.inbox.clone(), self.me.clone());
        (self.spawn)(Box::new(move || {
            let Ok(_one) = api.polling.try_lock() else { return };
            match api.updates() {
                Ok(found) => {
                    for (channel, said) in found {
                        inbox.deliver(&channel, said.to_string().as_bytes(), None);
                    }
                }
                Err(e) => log::warn!("{}: the bot would not answer: {e}", local_of(&me)),
            }
        }));
    }

    fn common(&self) -> Result<Vec<String>, Error> {
        self.beliefs.graphs_of(&[BELIEF], &Within::common())
    }

    /// A message on a chat the world names by its id: the prose it is, in the chat, by the person writing as the user;
    /// none where the world names no chat by that id.
    pub fn handle(&mut self, channel: &str, payload: &[u8], at: DateTime) -> Result<Option<Prose>, Error> {
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
        Ok(Some(Prose {
            channel: chat,
            sender,
            text: said.get("text").and_then(Json::as_str).unwrap_or_default().to_string(),
            at: Some(at),
            addressed: said.get("addressed").and_then(Json::as_bool),
            message: said.get("message").and_then(Json::as_str).map(str::to_string),
            reply: None,
        }))
    }

    /// `method` posted to the chat the world names `channel` by its id; false where it names none, or the API refuses
    /// or fails.
    fn posted(&self, channel: &str, method: &str, body: Json) -> bool {
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
        let reply = match (self.api.call)(&self.api.method(method), &body) {
            Ok(r) => r,
            Err(e) => {
                log::warn!("{}: the bot would not answer {method}: {e}", local_of(&self.me));
                return false;
            }
        };
        if !reply.get("ok").and_then(Json::as_bool).unwrap_or(true) {
            log::warn!(
                "telegram would not take a {method} for {}: {}",
                local_of(channel),
                reply.get("description").cloned().unwrap_or(reply.clone())
            );
            return false;
        }
        true
    }
}

impl Carrier for Telegram {
    fn say_to(&mut self, channel: &str, text: &str, reply: Option<&str>) -> bool {
        let mut body = json!({"text": text});
        if let Some(reply) = reply.and_then(|r| r.parse::<i64>().ok()) {
            body["reply_parameters"] = json!({"message_id": reply, "allow_sending_without_reply": true});
        }
        self.posted(channel, "sendMessage", body)
    }

    fn writing_in(&mut self, channel: &str) -> bool {
        self.posted(channel, "sendChatAction", json!({"action": "typing"}))
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
        let call: Call = Arc::new(move |url, body| {
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
        let mut bot = Telegram::new(store, &format!("{TEST}keeper"), "123:abc", TELEGRAM_URL, call);
        bot.spawn = Box::new(|work| work());
        (bot, updates, calls)
    }

    fn said(user: &str, text: &str, addressed: Json, message: &str) -> Json {
        json!({"from": user, "text": text, "addressed": addressed, "message": message})
    }

    #[test]
    fn updates_are_each_text_message_by_its_chats_id_and_the_offset_moves_past_them() {
        let store = world();
        let (bot, updates, calls) = bot(&store);
        *updates.lock().unwrap() = vec![
            message(10, 4242, " hello ", 111, json!({})),
            json!({"update_id": 11, "edited_message": {}}),
            message(12, -100, "hi all", 222, json!({})),
        ];
        assert_eq!(
            bot.api.updates().unwrap(),
            [
                ("4242".to_string(), said("111", "hello", Json::Null, "10")),
                ("-100".to_string(), said("222", "hi all", Json::Null, "12"))
            ]
        );
        assert!(bot.api.updates().unwrap().is_empty());
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

    #[test]
    fn in_a_group_words_that_tag_the_bot_or_reply_to_it_are_addressed_to_it_and_to_someone_else_not() {
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

    #[test]
    fn a_poll_delivers_each_message_to_the_inbox_and_an_api_refusing_is_asked_again() {
        let store = world();
        let (mut bot, updates, _) = bot(&store);
        *updates.lock().unwrap() = vec![message(1, 4242, "hello", 111, json!({}))];
        let good = bot.api.call.clone();
        bot.api.call = Arc::new(|_, _| Ok(json!({"ok": false, "description": "Unauthorized"})));
        bot.poll();
        assert!(bot.inbox.take().is_empty() && bot.api.bot().is_none());
        bot.api.call = good;
        bot.poll();
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
    fn a_message_is_prose_in_the_chat_the_world_names_by_its_id_by_the_person_writing_as_the_user() {
        let store = world();
        let (mut bot, _, _) = bot(&store);
        let before = store.len().unwrap();
        let payload = |s: Json| s.to_string().into_bytes();
        let heard: Vec<Prose> = [
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
            .map(|p| {
                (
                    p.channel.clone(),
                    p.sender.clone(),
                    p.text.clone(),
                    p.addressed,
                    p.message.clone(),
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

    #[test]
    fn what_the_agent_says_goes_to_send_message_with_the_chats_id_and_writing_to_a_chat_action() {
        let store = world();
        let (mut bot, _, calls) = bot(&store);
        assert!(bot.say_to(&format!("{TEST}anna_telegram"), "the fern is dry", None));
        assert!(bot.say_to(&format!("{TEST}household_telegram"), "it is", Some("42")));
        assert!(
            !bot.say_to(&format!("{TEST}anna_mail"), "x", None),
            "no Telegram chat is not this member's"
        );
        assert!(bot.writing_in(&format!("{TEST}anna_telegram")));
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

    #[test]
    fn an_api_that_fails_sends_nothing_and_connect_refuses_an_agent_with_no_token() {
        let store = world();
        let (mut bot, _, _) = bot(&store);
        bot.api.call = Arc::new(|_, _| Err("unreachable".into()));
        assert!(!bot.say_to(&format!("{TEST}anna_telegram"), "x", None));
        assert!(Telegram::connect(&store, &format!("{TEST}keeper"), &|_| None).is_err());
        let env = |k: &str| match k {
            "TELEGRAM_BOT_TOKEN" => Some("t".to_string()),
            "TELEGRAM_URL" => Some("https://bots.example/".to_string()),
            "TELEGRAM_POLL_S" => Some("5".to_string()),
            _ => None,
        };
        let bot = Telegram::connect(&store, &format!("{TEST}keeper"), &env).unwrap();
        assert_eq!((bot.api.url.as_str(), bot.every), ("https://bots.example", 5.0));
    }
}
