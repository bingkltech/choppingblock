# ⚖️ RULES.md — The God Agent's Laws

> This file contains the **absolute laws of the codebase**, forged from past mistakes.
> Written exclusively by the God Agent. If RULES.md contradicts standard conventions, **RULES.md wins**.

---

## Rule 1: Type Hints Mandatory
All Python functions MUST include type hints for parameters and return values.

## Rule 2: No Naked Prints
Never use `print()` in production code. Use Python's `logging` module with appropriate levels.

## Rule 3: Timeout Everything
All subprocess calls, API requests, and Docker operations MUST have explicit timeouts.
Default: 30 seconds for API calls, 120 seconds for Docker operations.

## Rule 4: Fail Loud
Never swallow exceptions silently. Log the full traceback and broadcast the error via WebSocket heartbeat.

## Rule 5: Stigmergy Only
Agents do NOT communicate directly. All coordination happens through file modifications in this repository.
