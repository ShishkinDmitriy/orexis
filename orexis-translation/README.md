# orexis-translation

Speaks with people. What a person writes in a chat becomes a statement in the words the chat allows, or a question
the model answers from what the chat may read; what the agent says to a person is phrased and sent back.

- **Loaded for:** `translation:Translator`, beneath the speaker.
- **Words:** `ontology.ttl` (`translation:`). **Dictionary:** `knowledge/domain/translation/`.
- **Imports:** the kernel and speech. It imports no transport member.
- **Needs:** the model's key, mounted into this agent's container alone.

## What starts it

| Heard | Said by | Starts |
|---|---|---|
| `translation:TranslatingTrigger`: `speech:ProseKept` | a transport that kept a person's words | `translation:Translating`, where the words' provenance says they are a person's |
| `translation:PhrasingTrigger`: `speech:Said` | speech | `translation:Phrasing`, for each the document is to that is a person in a chat of the agent's |
| the model's answer, handed back as a job (an arrival) | its own thread | the answer kept as prose, or the statement kept |
| the clock, every 4 s while an answer is thought | | `speech:WritingAnnounced` said again |

## Activities

| Activity | What happens | Ends saying |
|---|---|---|
| `translation:Translating` | find the chat and who spoke; judge whether the words were for this agent; brief the model and offer it the chat's tools, off the mind's thread | `speech:WritingAnnounced`; later `translation:Conversed` and `speech:ProseKept` for the answer |
| `translation:Phrasing` | the model is asked to write the message for the person, off the mind's thread | `speech:ProseKept` for the words, which the chat's transport carries |

## What it says

`translation:Conversed` (the chat, the person, each tool the model called, the words said back and how it ended),
kept by the journal for good.
