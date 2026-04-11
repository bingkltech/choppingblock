# Session Handoff Template

> Fill this out at the END of your session. The next agent (or your next session)
> reads this to avoid amnesia.

## Task
<!-- One-sentence description of what you were working on -->

## Status
<!-- COMPLETED / IN PROGRESS / BLOCKED -->

## What Was Done
<!-- Bullet list of completed sub-tasks -->
- [ ] ...
- [ ] ...

## What Remains
<!-- Bullet list of remaining sub-tasks, in dependency order -->
- [ ] ...
- [ ] ...

## Key Decisions Made
<!-- Why did you choose X over Y? Future agents need this. -->
- Decision: ...
  - Why: ...
  - Alternative considered: ...

## Files Modified
<!-- List every file you touched -->
- `backend_engine/path/to/file.py` — what changed
- `visual_hq/src/path/to/file.jsx` — what changed

## Verification State
```
python -m py_compile main.py:   PASS / FAIL (describe errors)
npm run build:                   PASS / FAIL / NOT RUN
Backend server health:           OK / NOT TESTED
Frontend renders:                OK / NOT TESTED
WebSocket connected:             OK / NOT TESTED
```

## Stigmergic Memory Updates
<!-- Did you update the shared repo memory? -->
- [ ] `ARCHITECTURE.md` updated (if plan changed)
- [ ] `RULES.md` updated (if new rules were forged from mistakes)
- [ ] `README.md` updated (if structure changed)

## Blockers & Warnings
<!-- Anything the next agent needs to know -->
- ...

## Context Files to Re-Read
<!-- Which docs does the next agent need to load? -->
- `RULES.md` — if new rules were added
- `ARCHITECTURE.md` — if the plan changed
- `db_manager.py` — if schema was modified
- `main.py` — if new API endpoints were added
