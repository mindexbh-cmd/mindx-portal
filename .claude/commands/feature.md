---
description: Build a feature end-to-end via the coordinator pipeline. Usage. /feature <description>
argument-hint: <description>
---

Delegate the entire feature pipeline to `mindex-coordinator-agent`.

Feature description: `$ARGUMENTS`

If `$ARGUMENTS` is empty, ask for the description and stop — coordinator needs context.

1. **Invoke the coordinator** in a single Agent call:
   ```
   Agent({
     subagent_type: "mindex-coordinator-agent",
     description: "Feature pipeline: <short title>",
     prompt: "Plan and ship the following feature end-to-end. <full $ARGUMENTS>.
              Use the standard pipeline:
                code-architect (placement + shape)
                → data-protector (if any DB change)
                → implementation (the coordinator may delegate to general-purpose for the code, OR write it directly)
                → ui-designer + arabic-quality + mobile-first (parallel)
                → ux-employee + real-user-tester
                → documentation-keeper (CHANGELOG / API.md)
              When all reviewers approve, recommend (do NOT execute) the safe_deploy step.
              Report the aggregated verdict in your standard format."
   })
   ```

2. **Surface the coordinator's report verbatim.** Don't summarise its specialist sections — that loses actionable detail.

3. **Final deployment step.** If the coordinator approves:
   - Show the recommended `python scripts/safe_deploy.py --feature <slug>` command
   - Ask the user "ship it?" rather than running it automatically — deploys to prod are a human gate

4. **If the coordinator rejects.** Show the fix list and ask the user how to proceed (fix-and-retry vs defer vs scope down).
