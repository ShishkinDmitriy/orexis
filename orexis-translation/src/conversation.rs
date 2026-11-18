//! A CONVERSATION WITH THE MODEL, at a run-time edge and never in a pass: what the model is told, the tools it is
//! offered, each turn's calls answered, and what comes of it handed back to the translator's task, rung awake for it.
//! The conversation is a Tokio task of its own, the agent held busy while it runs.

use std::collections::BTreeMap;
use std::sync::mpsc::Sender;
use std::time::{Duration, Instant};

use oxsdatatypes::DateTime;
use serde_json::{Value as Json, json};

use orexis::clock::isoformat;
use orexis::rdf::round6;
use orexis::store::Store;
use orexis::task::Wake;

use crate::events::{Conversed, Translated};
use crate::past::Past;
use crate::readable::{Prefixes, Readable, namespace_of, namespaces};
use crate::stated::{STATE, Stating, tool};
use orexis_llm::model::{Model, TOKENS, why_not};

/// WHERE THE CHAT HAS OTHER AGENTS AND NOBODY WAS NAMED: the agent answers only where what it holds speaks to it.
pub const SILENT: &str = "NOTHING";
pub const UNADDRESSED: &str = " Several agents are in this chat and the message names none. Where what this agent holds says \
nothing that answers it, reply with exactly NOTHING and nothing else.";
/// What separates two messages of one answer, where its chat's style lets it be several.
pub const BETWEEN_MESSAGES: &str = "---";

/// WHAT THE MODEL IS TOLD OF WRITING ON A CHAT, beside what it is told of every answer: the style's guidance, and where
/// one answer may be several messages, how to part them; nothing where the style says nothing.
///
/// ```
/// use orexis_translation::chat::Style;
/// use orexis_translation::written_as;
///
/// assert_eq!(written_as(&Style::default()), None);
/// let letter = Style { guidance: Some("One letter.".into()), messages_at_most: 1 };
/// assert_eq!(written_as(&letter).as_deref(), Some("How to write on this chat: One letter."));
/// let chatty = Style { guidance: Some("Short lines.".into()), messages_at_most: 3 };
/// assert!(written_as(&chatty).unwrap().ends_with("a line holding only --- between two, and at most 3 messages."));
/// ```
pub fn written_as(style: &crate::chat::Style) -> Option<String> {
    let guidance = style.guidance.as_deref()?;
    let parted = if style.messages_at_most > 1 {
        format!(
            " Where you send more than one message, put a line holding only {BETWEEN_MESSAGES} between two, and at most {} messages.",
            style.messages_at_most
        )
    } else {
        String::new()
    };
    Some(format!("How to write on this chat: {guidance}{parted}"))
}

/// THE MESSAGES ONE ANSWER IS SENT AS: parted at each line holding only `---`, the empty ones dropped, and the last
/// taking whatever is past `at_most`; one message where the style lets it be no more, as the model wrote it.
///
/// ```
/// use orexis_translation::sent_as;
///
/// assert_eq!(sent_as("Hello.\n---\nThe fern is dry.", 3), ["Hello.", "The fern is dry."]);
/// assert_eq!(sent_as("a\n---\nb\n---\nc", 2), ["a", "b\n\nc"]);
/// assert_eq!(sent_as("Dear Anna,\n---\nyours", 1), ["Dear Anna,\n---\nyours"]);
/// assert_eq!(sent_as("\n---\nonly", 3), ["only"]);
/// ```
pub fn sent_as(words: &str, at_most: usize) -> Vec<String> {
    if at_most <= 1 {
        return vec![words.trim().to_string()];
    }
    let parts: Vec<String> = words
        .split('\n')
        .collect::<Vec<_>>()
        .split(|line| line.trim() == BETWEEN_MESSAGES)
        .map(|lines| lines.join("\n").trim().to_string())
        .filter(|part| !part.is_empty())
        .collect();
    if parts.len() <= at_most {
        return parts;
    }
    let mut kept = parts[..at_most - 1].to_vec();
    kept.push(parts[at_most - 1..].join("\n\n"));
    kept
}

/// HOW OFTEN THE AGENT IS SHOWN WRITING AGAIN, in seconds of the one timeline: Telegram shows a chat action for five.
pub const WRITING_S: f64 = 4.0;
/// WHAT A CHAT READS TO READ WHAT HAPPENED: the kernel's event.
pub(crate) const EVENT: &str = "http://example.org/orexis#Event";

/// The briefing's last block, uncached: the instant the agent stands at, to the minute.
pub(crate) fn instant_block(at: DateTime) -> String {
    let iso = isoformat(at);
    let minutes = match (iso.find('T'), iso[iso.find('T').unwrap_or(0)..].find(['+', '-', 'Z'])) {
        (Some(t), Some(zone)) => format!("{}{}", &iso[..t + 6], &iso[t + zone..]),
        _ => iso,
    };
    format!("IT IS NOW {minutes}.")
}

/// The prefixes a statement is written with where the chat reads nothing: the store's, and the agent's own world's.
pub(crate) fn prefixes_of(store: &Store, me: &str) -> Prefixes {
    let mut out = namespaces(store);
    let ns = namespace_of(me).to_string();
    let name = crate::readable::named(&ns, &out.keys().cloned().collect());
    out.insert(name, ns);
    out
}

/// What the model's conversation hands back to the translator, and what rings the translator's task to take it.
#[derive(Clone)]
pub(crate) struct Backs {
    pub(crate) tx: Sender<Back>,
    pub(crate) wake: Wake,
}

impl Backs {
    /// `back` handed to the translator, and its task rung.
    pub(crate) fn send(&self, back: Back) {
        let _ = self.tx.send(back);
        self.wake.ring();
    }
}

/// What the model's conversation hands back to the translator.
pub(crate) enum Back {
    /// A person's statement, held to its bounds: kept as any peer's document and believed.
    Keep(Vec<u8>),
    /// Words to say on a chat's channel, replying to the message named.
    Said {
        channel: String,
        words: String,
        reply: Option<String>,
    },
    /// An answer thought in a chat is done with.
    Ended(String),
    Spent(Translated),
    Conversed(Conversed),
    /// A statement to hold to its words' bounds on the translator's task, the answer awaited.
    Ask {
        stating: Stating,
        inputs: Json,
        person: String,
        prose: String,
        at: DateTime,
        answer: tokio::sync::oneshot::Sender<Answered>,
    },
}

pub(crate) type Answered = Result<(Option<Vec<u8>>, Vec<String>), String>;

/// What the conversation asks of the translator: a statement held to its words' bounds, over the channel back.
pub(crate) struct Asked {
    pub(crate) back: Backs,
    pub(crate) at: DateTime,
    pub(crate) stating: Option<Stating>,
    /// How long the conversation waits for the translator's answer, in seconds (`translation:answeredWithinS`).
    pub(crate) within_s: f64,
}

impl Asked {
    async fn state(&self, inputs: &Json, person: &str, prose: &str) -> Answered {
        let Some(stating) = self.stating.clone() else {
            return Ok((None, vec!["nothing is said".into()]));
        };
        let (answer, waited) = tokio::sync::oneshot::channel();
        self.back.send(Back::Ask {
            stating,
            inputs: inputs.clone(),
            person: person.to_string(),
            prose: prose.to_string(),
            at: self.at,
            answer,
        });
        match tokio::time::timeout(Duration::from_secs_f64(self.within_s), waited).await {
            Ok(Ok(answered)) => answered,
            Ok(Err(e)) => Err(e.to_string()),
            Err(_) => Err(format!("the agent did not answer within {}s", self.within_s)),
        }
    }
}

/// One conversation, everything it needs read on the translator's task and handed to the conversation's.
pub(crate) struct Conversation {
    pub(crate) chat: String,
    pub(crate) channel: String,
    pub(crate) person: (String, String),
    pub(crate) text: String,
    pub(crate) system: Vec<String>,
    pub(crate) stating: Option<Stating>,
    pub(crate) readable: Option<Readable>,
    pub(crate) past: Option<Past>,
    pub(crate) unaddressed: bool,
    pub(crate) reply: Option<String>,
    pub(crate) me: String,
    pub(crate) at: DateTime,
    /// How many turns it may take (`translation:turns`): the last offers no tool, so the model answers in words.
    pub(crate) turns: usize,
    /// How many messages the answer may be sent as, by the chat's style.
    pub(crate) messages_at_most: usize,
}

fn sum(spent: &mut BTreeMap<String, i64>, tokens: &BTreeMap<String, i64>) {
    for (k, v) in tokens {
        *spent.entry(k.clone()).or_default() += v;
    }
}

pub(crate) fn translated(
    act: &str,
    outcome: &str,
    model: Option<String>,
    requests: usize,
    spent: &BTreeMap<String, i64>,
    began: Instant,
) -> Translated {
    let t = |k: &str| Some(*spent.get(k).unwrap_or(&0) as f64);
    Translated {
        act: Some(act.into()),
        outcome: Some(outcome.into()),
        model,
        requests: Some(requests as f64),
        input_tokens: t(TOKENS[0]),
        cache_creation_input_tokens: t(TOKENS[1]),
        cache_read_input_tokens: t(TOKENS[2]),
        output_tokens: t(TOKENS[3]),
        duration_s: Some(round6(began.elapsed().as_secs_f64())),
    }
}

/// The conversation: each turn's tool calls answered and handed back, until the model answers in words or keeps
/// silent — what comes of it handed back to the translator.
pub(crate) async fn converse(c: Conversation, model: &dyn Model, mind: &Asked, back: &Backs) {
    let mut tools: Vec<Json> = Vec::new();
    if let Some(stating) = &c.stating {
        tools.push(tool(&stating.prefixes));
    }
    if let Some(r) = &c.readable {
        tools.extend(r.tools());
    }
    if let Some(p) = &c.past {
        tools.extend(p.tools());
    }
    let mut messages = vec![json!({"role": "user", "content": format!("From {}:\n\n{}", c.person.1, c.text)})];
    let mut calls: Vec<(String, Json, String)> = Vec::new();
    let mut spent: BTreeMap<String, i64> = BTreeMap::new();
    let (began, mut requests) = (Instant::now(), 0);
    let mut turn = None;
    let mut taken = 0;
    for n in 0..c.turns {
        requests += 1;
        taken = n + 1;
        let answered = model.converse(&c.system, &messages, &tools, n + 1 == c.turns).await;
        let t = match answered {
            Ok(t) => t,
            Err(e) => {
                back.send(Back::Spent(translated(
                    "answer",
                    "failed",
                    model.name(),
                    requests,
                    &spent,
                    began,
                )));
                back.send(Back::Conversed(Conversed {
                    chat: c.chat.clone(),
                    person: c.person.0.clone(),
                    wrote: c.text.clone(),
                    calls,
                    answer: Some(format!("the model would not answer: {e}")),
                    outcome: Some("failed".into()),
                    model: model.name(),
                    at: Some(c.at),
                }));
                log::warn!(
                    "{} could not answer {}: the model would not answer: {e}",
                    c.me,
                    c.person.1
                );
                if !c.unaddressed {
                    let words = format!("{} could not answer: {}.", c.me, why_not(&e));
                    back.send(Back::Said {
                        channel: c.channel.clone(),
                        words,
                        reply: c.reply.clone(),
                    });
                    back.send(Back::Ended(c.chat.clone()));
                }
                return;
            }
        };
        sum(&mut spent, &t.tokens);
        if t.calls.is_empty() {
            turn = Some(t);
            break;
        }
        messages.push(json!({"role": "assistant", "content": t.content}));
        let mut results = Vec::new();
        for (id, name, inputs) in &t.calls {
            let found = called(&c, name, inputs, mind, back).await;
            calls.push((name.clone(), inputs.clone(), found.clone()));
            results.push(json!({"type": "tool_result", "tool_use_id": id, "content": found}));
        }
        messages.push(json!({"role": "user", "content": results}));
        turn = Some(t);
    }
    let turn = turn.unwrap_or_default();
    log::info!(
        "{} answered {} in {taken} request(s): {}",
        c.me,
        c.person.1,
        TOKENS
            .iter()
            .map(|k| format!("{} {k}", spent.get(*k).unwrap_or(&0)))
            .collect::<Vec<_>>()
            .join(", ")
    );
    let mut words = turn.text.trim().to_string();
    let outcome = if words == SILENT {
        "silent"
    } else if words.is_empty() {
        "no words"
    } else {
        "said"
    };
    if words.is_empty() {
        let stop = if turn.stop.is_empty() {
            None
        } else {
            Some(turn.stop.as_str())
        };
        log::warn!(
            "{} could not answer {}: the model wrote no words ({})",
            c.me,
            c.person.1,
            stop.unwrap_or("no reason")
        );
        if !c.unaddressed {
            words = format!(
                "{} could not answer: its model wrote no words ({}).",
                c.me,
                stop.unwrap_or("no reason given")
            );
        }
    }
    back.send(Back::Spent(translated(
        "answer",
        outcome,
        model.name(),
        requests,
        &spent,
        began,
    )));
    back.send(Back::Conversed(Conversed {
        chat: c.chat.clone(),
        person: c.person.0.clone(),
        wrote: c.text.clone(),
        calls,
        answer: (!words.is_empty()).then(|| words.clone()),
        outcome: Some(outcome.into()),
        model: model.name(),
        at: Some(c.at),
    }));
    if !words.is_empty() && words != SILENT {
        //  ONE ANSWER, AS MANY MESSAGES AS ITS CHAT'S STYLE LETS IT BE: the first replying to what it answers.
        for (n, part) in sent_as(&words, c.messages_at_most).into_iter().enumerate() {
            back.send(Back::Said {
                channel: c.channel.clone(),
                words: part,
                reply: if n == 0 { c.reply.clone() } else { None },
            });
        }
    }
    if !c.unaddressed {
        back.send(Back::Ended(c.chat.clone()));
    }
}

/// What a tool call answers: a vocabulary or a query's rows off the chat's copy, the journal's entries or the series'
/// points; a statement kept, or why it is refused.
async fn called(c: &Conversation, name: &str, inputs: &Json, mind: &Asked, back: &Backs) -> String {
    let mut read = c.readable.as_ref().and_then(|r| r.call(name, inputs));
    if read.is_none()
        && let Some(past) = &c.past
    {
        read = past.call(name, inputs).await;
    }
    if let Some(found) = read {
        log::info!("{} read for {}: {name} {inputs}", c.me, c.person.1);
        return found;
    }
    if name != STATE || c.stating.is_none() {
        log::warn!("the model called {name:?}, which this chat offers no tool of");
        return format!("no tool is named {name}");
    }
    match mind.state(inputs, &c.person.0, &c.text).await {
        Ok((Some(payload), _)) => {
            back.send(Back::Keep(payload));
            "kept: the agent believes it now".into()
        }
        Ok((None, why)) => {
            log::info!("{} refused what {} stated: {}", c.me, c.person.1, why.join("; "));
            format!("not kept: {}", why.join("; "))
        }
        Err(e) => format!("not kept: {e}"),
    }
}
