---
type: Service
title: Transport
description: >-
  How an agent reaches the devices, services, peers and people of its world - a family whose
  contract is a crate its members share (`orexis-transport/`), with four members that ship: MQTT,
  speaking MQTT4SSN, HTTP, speaking the WoT Thing Description, Telegram and email. It hands sensing
  bytes, sends what a step commands, carries documents between agents and a person's prose to and
  from the agent; sensing, speech and translation know nothing of it.
---

# The contract

The family's contract is `orexis-transport/`, a crate each member depends on and nothing else reads: it is no
package, registers nothing and plays no role. It holds what every member does alike. A member's own thread leaves
each message it receives in an `Inbox`, which rings the member's task awake; the task's core queues what arrived
(`Pending`) and runs its jobs until none is left (`Jobs::queued`); and the first thing its start asks is whether the
world wires the self through it (`wired`). A member that carries a [chat](/domain/speech/chat.md)'s words is a chat
carrier, Telegram and email the two that ship: each says only how it polls, reads a message and says a text
(`chat::ChatMember`), and one core runs both (`chat::ChatTransport`). MQTT and HTTP keep a core of their own on the
same queue, since nudging a sensor, telling a peer a document, sending a step's command and polling a url per sensor
are theirs alone. A member in a check is handed nothing and reaches nothing.

**A channel is the transport's, and what points at it says which row reads it.** A member carries
bytes on a channel — a topic, a url, a Telegram chat, a mailbox — and none of it means anything to
the member: a channel a sensor observes is sensing's, one an agent listens on is speech's, and the
channel of a [chat](/domain/speech/chat.md) the agent is in is a person's prose, the
[translator](/domain/translation/translator.md)'s. For that row a member keeps a person's words as
a `speech:ProseGraph` - the channel, who wrote where the channel tells, and the words - and says
`speech:ProseKept`, speech's words, since a chat is and every member is above speech; translation keeps the agent's answer the same way and says the same event, which
each member hears beneath its own carrying trigger and sends by `say_to` where it carries the channel,
the graph's provenance telling a person's words from the agent's
([policy](/domain/kernel/policy.md)); so a member imports no translation and translation imports no member
([an-agent-translates-for-itself](/decisions/an-agent-translates-for-itself.md)).

Whether a member is loaded at all is not asked of it, since asking would import it. A transport is
no [role](/domain/kernel/role.md) and no author declares one: the runtime loads a member where a role
the agent is declared in needs bytes and the society wires a bus — MQTT for an
[observer](/domain/sensing/observer.md)'s sensor on a topic or a [speaker](/domain/speech/speaker.md)
listening to one or a translator in a chat over one, HTTP for an observer's sensor with a form,
Telegram for a translator speaking through a bot, email for one in a chat by mail — read off the world before anything of
the member is ([package](/domain/kernel/package.md)). A member offers the rows above it a channel it
reaches and the acts on one (`orexis_transport::Member`), and adds itself to the agent's `Members` as it
makes its core; HTTP imports nothing above it, and MQTT still hands sensing's `received` and speech's
`heard` what arrives, until it is moved onto the contract (#1220). The MQTT member's ontology ships the speaker's one need, a topic it listens to, since a
topic is its word.

# The member that ships: MQTT

It adopts MQTT4SSN as it stands and declares no word of its own but its trigger. A sensor
`mqtt4ssn:observesTopic` a topic, a board `mqtt4ssn:listensToTopic` another, and a topic is named
by the `mqtt4ssn:hasFilterPattern` of the filters that match it: the agent subscribes by the
pattern and publishes a command to a pattern with no wildcard. No society states a filter: onboarding
names each topic by one convention, for its publisher or its listener, into a derived society document
the member reads as any other ([requirement](/domain/onboarding/requirement.md)), so a board has one
readings topic and its sensors each read their own value of the one message by pointer. Which sensors are the agent's is its
[observer](/domain/sensing/observer.md) role's to declare, and the member asks sensing for them and
names none of sensing's words. Which brokers the agent is connected to is the society's to say, where each answers the world's derived
[deployment](/domain/onboarding/deployment.md)'s, and the agent's credential the environment's (`MQTT_USERNAME`
and the rest), which [onboarding](/domain/onboarding/onboarding.md) writes; the member
refuses to guess one, and holds a client per broker. A world may have any number of brokers, and
MQTT4SSN says which each client `isConnectedToBroker`: a sensor's topic is subscribed to on every
broker the agent shares with the sensor's client, its own on every broker it is connected to, and a
command or a document goes out on the first broker it shares with whoever it is for. Started, it
asks after its sensors' missing readings as one falls due, telling each such board to sense now, a
minute later again while a board it told stays silent, and otherwise waits for the next reading to fall
due ([sensing](/domain/sensing/sensing.md)'s `next_lapse`).

A peer's document travels the same way: the member hears speech's `speech:Said` beneath its
`mqtt:TellingTrigger`, reads the document back from the store, and `tell` publishes it on the topic each recipient listens to,
and one arriving is handed to [speech](/domain/speech/speech.md)'s `heard`; a document to a person is
not the bus's, and is passed over in silence. A chat's topic carries prose both ways, each message
`{"from": …, "text": …}`, and the member skips its own when the broker hands it back. A board told to sense that sends no reading is told
again after `mqtt:askedAgainAfterS`, a figure a role the agent plays may state, sixty seconds where none does.

# The member that ships: HTTP

It adopts the W3C WoT Thing Description as it stands and declares no word of its own. A sensor
reached over HTTP is also a `td:Thing`, and its `td:hasForm` is a form whose `hctl:hasTarget` is a
URI template; `{latitude}` and `{longitude}` are filled from the `schema:geo` of what the sensor is
hosted by, variable by local name. Such a thing is a channel the member is asked on
(`Exchange::Requested`): a request is one fetch with `reqwest`, awaited as a Tokio task, one at a time
per sensor, and the body is left in the inbox of whoever asked; who asks, and how often, is
[sensing](/domain/sensing/sensing.md)'s. The member runs no task of its own.
The one sensor it serves today is a [forecast](/domain/kernel/forecast.md) service, whose
address is public and is read off the world, not told
([a-forecast-is-a-series-a-sensor-reads](/decisions/a-forecast-is-a-series-a-sensor-reads.md)). A fetch is given
up after `http:fetchedWithinS`, the member's one word of its own, thirty seconds where no role states it.

# The member that ships: Telegram

The agent's own bot, the `telegram:Bot` it `telegram:hasBot`, its token `TELEGRAM_BOT_TOKEN` and where the API answers
the world's derived deployment's word of the bot, over the standard library. Started, it asks `getUpdates` every few seconds from the
offset past the last update seen, on a thread of its own; a text message's channel is its chat's id,
which the world states as a `telegram:Chat`'s `telegram:chatId`, and who wrote is the person the world
states under that `telegram:userId`. A message in a chat the world names none of is dropped and said
once. In a group it says whom the words were for, as Telegram tells it: words tagging the bot or
replying to one of its messages are addressed to the agent, words tagging or replying to someone else
and not it are not, and which account is the bot's own it asks the API (`getMe`) rather than any
document. `say_to` posts `sendMessage` with the chat's id, as a reply to the message the agent answers.
Its words are its own ontology's (`orexis-transport-telegram/ontology.ttl`), among them how often the bot is
polled and how long one call of the API may take, `telegram:polledEveryS` and `telegram:calledWithinS`, three and
thirty seconds where no role states them.

# The member that ships: email

The agent's own mailbox, named by `MAIL_ADDRESS` and the rest, over `imaplib` and `smtplib`. Started,
it polls the unseen messages every half minute; a message's channel is its sender's address, matched to
the `schema:ContactPoint` whose `schema:email` it is, and `say_to` sends to that address. It declares no
word of its own but its trigger.
