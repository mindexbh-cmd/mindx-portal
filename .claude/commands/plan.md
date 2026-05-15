---
description: Turn a vague request into a phased plan. Usage. /plan <description>
argument-hint: <description>
---

Delegate to `prompt-engineer-agent` to convert a high-level wish into a complete phased implementation plan.

Description: `$ARGUMENTS`

If `$ARGUMENTS` is empty, ask the operator for the description and stop — the agent needs something to plan.

## Invocation

```
Agent({
  subagent_type: "prompt-engineer-agent",
  description: "Plan: $ARGUMENTS",
  prompt: "Mode: A (deliver, don't execute).
           Request: $ARGUMENTS

           Follow your standard six-phase workflow:
             1. Understand (surface goal vs underlying need)
             2. Research (memory files + codebase)
             3. Plan (phases with agents, risk, rollback)
             4. Write (markdown plan to docs/plans/<slug>-<ts>.md)
             5. Validate (every reference resolves)
             6. Deliver (path + summary)

           Report: goal, phase summary, risk, time estimate, path."
})
```

## Output to the operator

Show:
1. The **goal statement** (1 sentence, in the operator's language)
2. The **phase summary** (one line per phase)
3. **Risk** (LOW / MEDIUM / HIGH) + worst case
4. **Time estimate** (be honest about uncertainty)
5. **Path** to the saved plan: `docs/plans/<slug>-<ts>.md`
6. **The question**: "Execute now, save for later, or refine first?"

## After the operator answers

- **"Execute now"** → invoke the coordinator (`/feature <description>`) or the appropriate specialist directly with the plan as context.
- **"Save for later"** → just confirm the path. The plan stays as a markdown file the operator can come back to.
- **"Refine"** → ask which phase / which concern needs revision, then re-invoke prompt-engineer-agent with the feedback.

## Examples

```
/plan أريد ميزة لإرسال تذكير دفع للأهالي
/plan الصفحة الرئيسية بطيئة على الموبايل
/plan add a way for teachers to export attendance as PDF
/plan ablation: drop the trip tables since nobody uses them
```
