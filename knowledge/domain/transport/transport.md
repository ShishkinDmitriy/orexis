---
type: Service
title: Transport
description: >-
  How an agent reaches the devices, services, peers and people of its world - a family whose
  contract the container holds (`agent/transport/transport.py`), with four members that ship: MQTT,
  speaking MQTT4SSN, HTTP, speaking the WoT Thing Description, Telegram and email. It hands sensing
  bytes, sends what a step commands, carries documents between agents and a person's prose to and
  from the agent; sensing, speech and translation know nothing of it.
---

# The contract

What the container asks of any member: bring itself up from the environment (`connect`, handed
the container's `deliver`), subscribe to the agent's
channels (`open`), turn a message into observations by calling sensing's `received` once per
sensor it is for (`handle`), and send what a device may be told — a cadence, a sense-now, and the
payload a step's command answers (`actuate`), say whether it `reaches` a sensor or an actuator,
and **start itself** (`start`, handed the runtime): its session's messages submitted as jobs its
part's task runs, what it listens on opened, what it does of its own accord scheduled, and
the agent held running, since what it senses goes on arriving. A member is a [part](/domain/kernel/part.md) of its own:
execution's part and speech's, linked to it, hand it a step's command (`command`) and a document
told (`tell_to`), which it sends where it reaches the recipient. Several are held behind
`Transports`, which sends a nudge or a command to the member that reaches its device.

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
the member is ([package](/domain/kernel/package.md)). A member imports sensing's `received` and
speech's `heard` only where a message is for one of them, so an agent that only listens never loads
sensing. The MQTT member's ontology ships the speaker's one need, a topic it listens to, since a
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
names none of sensing's words. Where each broker the agent is connected to listens, and the
agent's credential, come from the environment (`MQTT_BROKERS`, each broker's IRI and its url, then
`MQTT_USERNAME` and the rest), which [onboarding](/domain/onboarding/onboarding.md) writes; the member
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
`{"from": …, "text": …}`, and the member skips its own when the broker hands it back.

# The member that ships: HTTP

It adopts the W3C WoT Thing Description as it stands and declares no word of its own. A sensor
reached over HTTP is also a `td:Thing`, and its `td:hasForm` is a form whose `hctl:hasTarget` is a
URI template; `{latitude}` and `{longitude}` are filled from the `schema:geo` of what the sensor is
hosted by, variable by local name. Started, it polls each sensor at once and then every
`ssn-system:Frequency` the sensor states; a fetch runs on a thread of its own, one at a time per
sensor, and the response is submitted like a message.
The one sensor it serves today is a [forecast](/domain/kernel/forecast.md) service, whose
address is public and is read off the world, not told
([a-forecast-is-a-series-a-sensor-reads](/decisions/a-forecast-is-a-series-a-sensor-reads.md)).

# The member that ships: Telegram

The agent's own bot, the `telegram:Bot` it `telegram:hasBot`, its token `TELEGRAM_BOT_TOKEN` and where the API answers
`TELEGRAM_URL`, over the standard library. Started, it asks `getUpdates` every few seconds from the
offset past the last update seen, on a thread of its own; a text message's channel is its chat's id,
which the world states as a `telegram:Chat`'s `telegram:chatId`, and who wrote is the person the world
states under that `telegram:userId`. A message in a chat the world names none of is dropped and said
once. In a group it says whom the words were for, as Telegram tells it: words tagging the bot or
replying to one of its messages are addressed to the agent, words tagging or replying to someone else
and not it are not, and which account is the bot's own it asks the API (`getMe`) rather than any
document. `say_to` posts `sendMessage` with the chat's id, as a reply to the message the agent answers.
Its words are its own ontology's (`agent/transport/telegram/ontology.ttl`).

# The member that ships: email

The agent's own mailbox, named by `MAIL_ADDRESS` and the rest, over `imaplib` and `smtplib`. Started,
it polls the unseen messages every half minute; a message's channel is its sender's address, matched to
the `schema:ContactPoint` whose `schema:email` it is, and `say_to` sends to that address. It declares no
word of its own but its trigger.
