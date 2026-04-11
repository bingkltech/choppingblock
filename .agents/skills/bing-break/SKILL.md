---
name: bing-break
description: >
  The Granular Task Decomposition framework for AI agents working on ChoppingBlock.
  Prevents context exhaustion, hallucination, and amnesia by enforcing a strict
  6-phase workflow: Ground → Plan → Verify → Slice → Execute → Checkpoint.
  MANDATORY for any task touching 3+ modules or 6+ files.
---

# The Bing Break Framework v1

AI agents — whether running on local Ollama, Claude, Gemini, or any other
provider — are subject to context window limits, training-data bias, and session
amnesia. Assigning a monolithic task to any agent risks:

- **Hallucination** — referencing files, functions, or APIs that don't exist
- **Amnesia** — forgetting decisions from earlier in the conversation
- **Drift** — using patterns from training data instead of this repo's conventions
- **Context exhaustion** — losing focus as the window fills up

This framework prevents all four failure modes.

## When to Use This Skill

| Condition | Action |
|-----------|--------|
| Task touches **1 module, ≤3 files** | Just do it. No decomposition needed. |
| Task touches **2-3 modules, 3-6 files** | Break into **3-5 sub-tasks**. |
| Task touches **3+ modules, 6+ files** | **MANDATORY: Full Bing Break protocol.** |
| Task touches **4+ modules, 10+ files** | Write plan in `docs/plans/`, get CEO approval first. |

---

## The Protocol: Ground → Plan → Verify → Slice → Execute → Checkpoint

### Phase 1: GROUND (Load Context Fortress)

Before writing any code, load the repo's context system in this exact order:

```
1. Read README.md                              → Project overview, prerequisites, structure
2. Read backend_engine/shared_workspace/RULES.md → Absolute laws of the codebase (RULES.md WINS over conventions)
3. Read backend_engine/shared_workspace/ARCHITECTURE.md → CEO's current master plan
4. Read StructureCode.txt                       → Full repo file map — know where everything lives
5. Read .env.example                            → Required credentials and configuration
```

Then load the relevant **module-specific context**:

```
6. Read backend_engine/database/db_manager.py   → If task involves database/ledger
7. Read backend_engine/anatomy/agent_core.py     → If task involves agent state/heartbeat
8. Read backend_engine/anatomy/shift_manager.py  → If task involves BOSS/GOD mode
9. Read backend_engine/main.py                   → If task involves API routes or WebSocket
10. Read visual_hq/src/hooks/useHeartbeat.js     → If task involves frontend real-time data
```

**Why this order matters:** README gives you the big picture. RULES.md tells you
the absolute laws. ARCHITECTURE.md tells you what to build. The module files
give you verifiable facts to check against before writing code.

### Phase 2: PLAN (Design Before Coding)

With full context loaded:

1. **State the goal** in one sentence.
2. **Identify the ripple chain** — which modules will this touch?
   ```
   database → anatomy → caveman_tools → workforce → main.py → visual_hq
   ```
3. **Classify the task size** using the table above:
   - Tiny/Small → proceed directly to Execute
   - Medium → proceed to Slice (3-5 sub-tasks)
   - Large/Epic → proceed to Slice (8-15 sub-tasks), write plan in `docs/plans/`
4. **Check the Stigmergic Memory** — read `ARCHITECTURE.md` and `RULES.md` to
   understand why the current system looks the way it does.

**Output:** A mental (or written) task list with explicit module ordering.

### Phase 3: VERIFY (Anti-Hallucination Gate)

Before ANY sub-task execution:

1. **For every file you plan to modify** → verify it exists with `list_dir` or `view_file`
2. **For every class/function you plan to import** → check the actual source file
3. **For every database table you plan to query** → check `db_manager.py` table definitions
4. **For every API endpoint you plan to call** → check `main.py` route definitions
5. **For every agent you plan to reference** → check `db_manager.py` `seed_default_agents()`
6. **For every Caveman Primitive you plan to use** → check `caveman_tools/` directory

If something doesn't exist in the codebase, it might be:
- New (you need to create it)
- In the source but not imported (add the import)
- Hallucinated (drop it)

**This phase takes 30 seconds and saves hours of debugging.**

### Phase 4: SLICE (Decompose Into Sub-Tasks)

Convert your plan into atomic, ordered sub-tasks:

**Rules for slicing:**
1. **One concern per sub-task.** Never mix database + API route + React component in one task.
2. **Follow the dependency chain.** Database first, anatomy second, tools third, workforce fourth, API fifth, UI last.
3. **Each sub-task must be independently verifiable** with `python -m py_compile <file>` or `npm run build`.
4. **Name sub-tasks clearly** — "Add token_limit column to API_Usage" not "Do database stuff".

**Slicing template (for ChoppingBlock):**
```
Sub-task 1: [database]       — Create/modify SQLite schema + helpers in db_manager.py
Sub-task 2: [anatomy]        — Add/update BaseAgent properties or ShiftManager logic
Sub-task 3: [caveman_tools]  — Create/modify Caveman Primitive wrappers
Sub-task 4: [workforce]      — Create/modify Tier 1/2/3 agent implementations
Sub-task 5: [main.py]        — Create/modify API routes + WebSocket handlers
Sub-task 6: [visual_hq]      — Create/modify React components + hooks
Sub-task 7: [verification]   — Full typecheck + smoke test both servers
```

### Phase 5: EXECUTE (One Sub-Task at a Time)

For EACH sub-task:

1. **Re-read the relevant context** for that sub-task's module
2. **Execute the change** — keep edits minimal and focused
3. **Verify immediately:**
   ```bash
   # Backend changes
   python -m py_compile backend_engine/<file>.py   # Syntax check
   python backend_engine/database/db_manager.py     # If DB changed, test bootstrap

   # Frontend changes
   cd visual_hq && npm run build                    # Must compile with zero errors
   ```
4. **If verification fails:** Fix before proceeding. Never stack changes on broken code.
5. **Move to next sub-task** only after current one passes verification.

**Windows-specific:**
- Console emoji may cause `UnicodeEncodeError` — use ASCII in `print()`, emoji OK in `logging`
- Use `subprocess.run(..., shell=True)` on Windows for bash-like commands
- File paths use backslashes — always use `os.path.join()` not string concatenation
- Docker Desktop must be running for `primitive_docker.py` to work

### Phase 6: CHECKPOINT (Capture Progress)

After completing ALL sub-tasks:

```bash
# Backend verification
python -m py_compile backend_engine/main.py     # Must pass
python backend_engine/database/db_manager.py     # Must bootstrap clean

# Frontend verification
cd visual_hq && npm run build                    # Must exit 0

# Diff check
git diff --stat                                  # Verify only intended files changed

# Context refresh — update Stigmergic Memory if needed
# If you changed the project structure → update README.md + StructureCode.txt
# If you added new rules from mistakes → update RULES.md
# If you changed the plan → update ARCHITECTURE.md
```

---

## The Dependency Chain (ChoppingBlock Module Order)

Always build in this order — downstream modules depend on upstream ones:

```
database/db_manager.py          ← Foundation: tables, seed data, helpers
    ↓
anatomy/agent_core.py           ← Agent DNA: BaseAgent class
anatomy/shift_manager.py        ← BOSS/GOD mode logic
    ↓
caveman_tools/primitive_*.py    ← Raw CLI tool wrappers
    ↓
workforce/tier1_executives/     ← CEO + God Agent (Premium LLMs)
workforce/tier2_cloud_labor/    ← Jules Router + Antigravity (Free Cloud)
workforce/tier3_local_swarm/    ← QA + Ops (Local Ollama)
    ↓
main.py                         ← FastAPI server, WebSocket, REST endpoints
    ↓
visual_hq/src/                  ← React dashboard components
```

---

## Recovery Protocol (When Context Is Lost)

If you feel confused, lost, or are making circular edits:

1. **STOP** — do not write more code.
2. **Read `README.md`** — recover the big picture.
3. **Read `RULES.md`** — recover the absolute laws.
4. **Read `ARCHITECTURE.md`** — recover what you're building.
5. **Read `StructureCode.txt`** — recover where things live.
6. **Run verification** — find out what's actually broken:
   ```bash
   python -m py_compile backend_engine/main.py
   cd visual_hq && npm run build
   ```
7. **Slice the remaining work** into a new sub-task and start fresh.

---

## Failure Detection

If ANY of these happen, you have **failed context compaction**:

| Symptom | Diagnosis | Remedy |
|---------|-----------|--------|
| Editing the same file 5+ times | Context thrashing | STOP. Slice into sub-task. |
| Writing a 500+ line replacement block | Monolithic change | STOP. Break into 3-5 smaller edits. |
| Referencing a function that doesn't exist | Hallucination | Read the actual source file. |
| Import works but runtime crashes | Export/import mismatch | Read the module's `__init__.py`. |
| Backend hangs on startup | Port conflict or DB lock | Check `lsof -i :8000` / restart. |
| Frontend shows blank page | WebSocket connection failed | Check backend is running on :8000. |
| Agent heartbeat not updating | WebSocket broadcast broken | Read `main.py` broadcast function. |
| Reinventing a pattern that exists | Amnesia / drift | Read `RULES.md` + existing code. |

**The universal remedy:** STOP → SLICE → RECOVER → RESUME.
