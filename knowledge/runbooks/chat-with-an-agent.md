---
type: Runbook
title: Chat with an agent
description: >-
  Give an agent a Telegram bot and a chat with you, worked on the terrace - the bot's token, the
  model's key, the chat's id in the world's secrets, onboarding and up - then ask it with /status or in
  words, check it is listening, and set up a group where several agents' bots answer.
---

# What you end up with

An agent that is a [translator](/domain/translation/translator.md) reads a [chat](/domain/speech/chat.md)
the world states and answers you there: `/status` with what it observes, for nothing, and a question
in words with the model's answer from its [askables](/domain/speech/askable.md). The terrace is
already declared for it: `:terrace_agent` plays `translation:Translator`, speaks through
`:terrace_bot`, and `speech.ttl` states `:terrace_and_dmitrii` over `:sovereign_telegram`. What the
repository cannot hold is the token, the key and the chat's id, so those are the steps below. For
another world, declare the same three things first (the translator page shows the self graph).

# Once per machine: the model

```bash
cp infra/model.env.example infra/secrets/model.env    # then set MODEL_NAME and MODEL_API_KEY; never committed
```

A changed key reaches a running agent only by recreating its container,
`podman compose up -d --force-recreate agent-<id>`: `podman compose restart` keeps the environment the
container was created with. Where the model answers is `infra/installation.ttl`'s `onboarding:Model`; with none there, onboarding
refuses a world with a translating agent. Without a key the agent still answers `/status`, and says in
its log that it has no model for anything else.

# Per agent: the bot

1. In Telegram, open `@BotFather`, send `/newbot`, and give it a name and a username. It answers with
   a token.
2. Write it where the terrace's compose file looks for it:

   ```bash
   mkdir -p world/terrace/secrets/terrace
   printf 'TELEGRAM_BOT_TOKEN=%s\n' '<the token>' > world/terrace/secrets/terrace/telegram.env
   ```

   The file is `secrets/<agent id>/telegram.env`, in the agent's own directory, one bot per agent. Where the Bot API answers is the
   world's deployment graph's (`:terrace_bot schema:url "https://api.telegram.org"`), told to the agent as
   `TELEGRAM_URL`.

# Per chat: its id

1. **With the agent not running**, write anything to your bot from the account you will chat from.
   While the agent polls, it takes every update itself and confirms it, and you will see nothing:
   stop it first with `podman compose stop agent-terrace` if it is up.
2. Ask the Bot API what it has:

   ```bash
   . world/terrace/secrets/terrace/telegram.env
   curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates" | python3 -m json.tool
   ```

   The chat's id is `result[].message.chat.id`, a number, negative for a group; who wrote is
   `result[].message.from.id`.
3. State it in the world, in a document in the agent's own directory under `secrets/`, since the id is yours and git holds none of
   that directory:

   ```turtle
   # world/terrace/secrets/terrace/chat.ttl
   @prefix : <http://example.org/orexis/world/terrace#> .
   @prefix orexis: <http://example.org/orexis#> .
   @prefix telegram: <http://example.org/orexis/telegram#> .
   <> a orexis:SocietyGraph .
   :sovereign_telegram telegram:chatId "<the id>" .
   ```

   The id is a string. A chat with one person needs no `telegram:userId`: the chat's one person is who
   wrote.

# Onboard and start

```bash
orexis-onboard terrace          # the ACL, the compose file and the rest
cd world/terrace && podman compose build && podman compose up -d
```

The compose file mounts the agent's own directory, `secrets/<agent>/`, whole, so a document written there
reaches the agent on its next restart and changes nothing committed. Each agent runs an image holding only its own packages and what they bring
([a-package-brings-its-own-dependencies](/decisions/a-package-brings-its-own-dependencies.md)), so
build the terrace's once before its first start, and again only when a package it runs changes what it
brings; a change to the code alone is mounted from the tree and needs a restart.

# Check it is listening

```bash
podman compose logs -f agent-terrace
```

At boot it says what it loads, and the list ends with `transport/telegram`:
`terrace loads belief, sensing, prediction, speech, translation, transport/mqtt, transport/http, transport/telegram`.
Then send `/status` to the bot: it answers within a few seconds (`TELEGRAM_POLL_S`, three by default)
with each sensor's latest reading, and asks no model. `/status` is a shortcut, not the way in: any
other words — "is the bed dry?", with or without the bot's @name — go to the model with the agent's
askables, the chat shows the bot typing while it thinks, and the answer comes from the rows the agent
read.

# A group with several agents

1. Create a group in Telegram and add each agent's bot.
2. For each bot, in `@BotFather`: `/setprivacy`, choose the bot, **Disable**. A bot with privacy on sees
   only commands, mentions of it and replies to it, so it would never hear an unnamed question.
   Telegram applies the change to groups the bot joins afterwards, so remove the bot and add it again.
3. Stop the agents, write in the group, and read the group's id and each writer's user id off
   `getUpdates` as above.
4. State the group as a chat in the world's `speech.ttl`, with every agent and person in it, and its
   id under `secrets/`:

   ```turtle
   :household a speech:Chat ;
       speech:participant :terrace_agent , :keeper_agent , :dmitrii ;
       speech:channel :household_telegram .
   :household_telegram a telegram:Chat .
   ```

   ```turtle
   # secrets/<agent>/chat.ttl of EVERY agent in the group, beside the one-to-one chat
   :household_telegram telegram:chatId "<the group's id>" .
   :dmitrii telegram:userId "<your user id>" .
   ```

5. `orexis-onboard <world>` and `podman compose up -d` again.

In the group, ask one agent as you would ask a person: tag its bot (`@<its bot's username>`), reply to
one of its messages, or name it — its id or the name the world gives it, `schema:name` ("terrace, is
the bed dry?"). The agent answers as a reply to your message, and the others keep silent; tag or reply
to someone else and every agent keeps silent unless you name it too. Ask nobody, and only an agent whose
askables answer the question replies. `/status` in a group is answered by every agent in it, and
`/status@<bot>` by that bot's agent alone. The bot's username is asked of Telegram, so no document
states it.

# When it does not answer

| what the log says | what to do |
|---|---|
| `no TELEGRAM_BOT_TOKEN in the environment`, and the agent exits | the token file is missing or empty, or the compose file was rendered before it existed: write it and run `orexis-onboard` again |
| `a message in Telegram chat <id>, which the world names in no chat: dropped` | `chat.ttl` is missing, holds another id, or is not mounted: check the id against `getUpdates` and re-run `orexis-onboard` |
| `words in <chat> from someone the chat names not: dropped` | in a group, the writer's `telegram:userId` is not stated, or names someone not in the chat |
| `<agent> could not answer: its model would not answer (HTTP Error 401: Unauthorized)`, in the chat too | the key in `infra/secrets/model.env` is refused: replace it, then recreate the container (`up -d --force-recreate`), since a restart keeps the old one |
| `<person> wrote to <agent>, and there is no model to hear it with` | `infra/secrets/model.env` lacks `MODEL_NAME` or `MODEL_API_KEY`; `/status` still works |
| `the bot would not answer: …` | the token is wrong (HTTP 401) or the API is unreachable from the host |
| nothing at all, in a group | privacy mode is still on for that bot, or no askable of the agent's speaks to an unnamed question |

Onboarding refuses before anything runs where a chat's agent has no bot (`speaks through no bot of its
own`), a bot's url is not `https://`, or the installation names no model. What each refusal holds is the
[requirement](/domain/onboarding/requirement.md) that says it.
