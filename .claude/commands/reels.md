# Reels Pipeline

Orchestrate the staged reel production pipeline. Request: $ARGUMENTS

Read `README.md` for full details on each stage before acting.

---

## Critical Rules

1. **Max 45 seconds.** Scripts must fit within 45 seconds.
2. **Never double-scale timestamps.** When Whisper runs on the sped-up avatar,
   timestamps are already correct.
3. **No scene overlays.** The `scenes` array must always be empty.
4. **B-roll must match speech.** Every segment must be semantically relevant.

---

## Commands

Parse `$ARGUMENTS` to determine the action:

- **`new <name> --script "text" --avatar <path>`** - Initialize pipeline
  (`python3 -m pipeline.agents.pipeline_state <name> --init --tool "..." --transcript ... --avatar ... --script "..."`)
- **`curate <reel-id>`** - Run Asset Curator, present manifest, wait for approval
- **`storyboard <reel-id>`** - Run Storyboard Agent, present timeline, wait for approval
- **`veo <reel-id>`** - Generate Veo clips if needed
- **`assemble <reel-id> [--render]`** - Build config + render
- **`review <reel-id>`** - Post-render QA check
- **`status <reel-id>`** - Show pipeline state
- **`full <reel-id>`** - Run all stages with gates, looping back on review failure
  (max 3 iterations)

---

## Working Directory

All scripts run from the reels project root:

```bash
python3 -m pipeline.agents.<agent_name> --reel-id <id> [options]
```

Stop and surface each quality gate (curate, storyboard, review) to the user
for approval before continuing to the next stage.
