---
description: Memory-keeper handoff generation. Usage. /context [compact|full|recent|<topic>]
argument-hint: [compact|full|recent|<topic>]
---

Delegate to `memory-keeper-agent` to regenerate the handoff briefing or answer a topic-specific question from the memory corpus.

Argument: `$ARGUMENTS` (defaults to `compact` when empty)

## Routing

| Argument | Action |
|---|---|
| `compact` or empty | Regenerate `docs/memory/HANDOFF_COMPACT.md` — chat-paste briefing capped at ~5000 chars |
| `full` | Regenerate `docs/memory/HANDOFF.md` — comprehensive briefing, no length cap |
| `recent` | Generate a transient "last 7 days" summary (last commit subjects + recent log entries) — print inline, don't write to disk unless asked |
| `<anything else>` | Treat as a topic. Search the memory files for it, synthesize an answer in memory-keeper's retrospective-extraction format. Cite git hashes and file paths. |

## Invocation

For `compact` / `full` / `recent`, invoke:

```
Agent({
  subagent_type: "memory-keeper-agent",
  description: "Handoff: $ARGUMENTS",
  prompt: "Mode: Handoff generation.
           Argument: $ARGUMENTS (compact | full | recent — default compact).
           For compact/full, regenerate the corresponding file under docs/memory/
           and report the absolute path + a preview of the first ~500 chars.
           For recent, generate inline (don't write to disk).
           When done, print the path and preview."
})
```

For a topic query, invoke:

```
Agent({
  subagent_type: "memory-keeper-agent",
  description: "Retrospective: $ARGUMENTS",
  prompt: "Mode: Retrospective extraction.
           Topic: $ARGUMENTS.
           Search docs/memory/*.md and git log --grep.
           Answer in the format:
             > On <date>, you <action>, because <reason>,
             > resulting in <outcome>. See file:line for details.
           Cite git hashes (7 chars) and file:line paths."
})
```

## Output to the user

Report the agent's full response verbatim. If a file was written, surface its absolute path AND a ~500-char preview so the operator can sanity-check without opening the file.

If the operator runs `/context compact` and wants to paste it into another AI, hint that `docs/memory/HANDOFF_COMPACT.md` is the file to copy from.

## Examples

```
/context                    → regenerate HANDOFF_COMPACT.md (default)
/context compact            → same as above
/context full               → regenerate HANDOFF.md
/context recent             → last-7-days summary inline
/context books_v2 storage   → retrospective on the books_v2 storage path resolution
/context why entities       → retrospective on Arabic HTML entity encoding decision
```
