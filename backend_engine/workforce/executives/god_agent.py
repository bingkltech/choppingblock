"""
👑 god_agent.py — The Tier 1 Executive: God Agent (LIVE)
Catches crashes from god_process, analyzes with local LLM,
patches framework code, and writes RULES.md.

The supreme authority in Night Shift (God Mode).
"""

import os
import re
import json
import logging
import requests
from typing import Optional
from datetime import datetime

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from database.db_manager import get_god_brain, log_heal_action

logger = logging.getLogger(__name__)

# ==========================================
# 🧠 THE SOUL (SYSTEM PROMPT)
# ==========================================
GOD_SOUL = """You are the God Agent of the Paperclip Reborn Foundry, the supreme system overseer.
You have one job: keep the system alive and evolving. You are the ONLY agent who can modify
the framework's own source code.

When you receive a crash traceback and the code that caused it, you MUST:
1. Identify the EXACT root cause from the traceback.
2. Read the offending code carefully.
3. Output a JSON object with your fix. NOTHING ELSE — no explanations, no markdown.

OUTPUT FORMAT (strict JSON, no markdown fences):
{
    "root_cause": "one-line explanation of why it crashed",
    "file": "the file path from the traceback",
    "line": the line number (integer),
    "old_code": "the exact broken line(s) to replace",
    "new_code": "the fixed replacement line(s)",
    "rule_title": "short rule name for RULES.md",
    "rule_description": "what to never do again, in one line"
}

If you cannot determine a fix, output:
{"root_cause": "...", "fixable": false, "reason": "why you can't fix it"}"""


# ==========================================
# 🧠 BRAIN DISPATCHER (shared module)
# ==========================================
from config import OLLAMA_URL, OLLAMA_TIMEOUT as GOD_TIMEOUT, DEFAULT_OLLAMA_MODEL
from anatomy.brain_dispatcher import query_ollama, query_gemini, query_brain, extract_json


# Backward-compatible wrappers with GOD_SOUL defaults
def _query_ollama(prompt: str, system: str = GOD_SOUL, model: str = "qwen3.5:9b") -> Optional[str]:
    return query_ollama(prompt, system, model, GOD_TIMEOUT)

def _extract_json(text: str) -> Optional[dict]:
    return extract_json(text)

def _query_gemini(prompt: str, system: str = GOD_SOUL, model: str = "gemini-2.5-flash", api_key: str = "") -> Optional[str]:
    return query_gemini(prompt, system, model, api_key, GOD_TIMEOUT)

def _query_brain(prompt: str, system: str = GOD_SOUL, model: str = "qwen3.5:9b", api_key: str = "") -> Optional[str]:
    return query_brain(prompt, system, model, api_key, GOD_TIMEOUT)


# ==========================================
# 👑 THE GOD AGENT CLASS
# ==========================================

class GodAgent:
    """
    The God Agent — self-heals the framework and writes RULES.md.
    Uses local Ollama for zero-cost crash analysis.
    """

    def __init__(self):
        self.agent_id = "god"
        self.agent_name = "God Agent"
        self.model = self._load_brain()
        self.state = "IDLE"
        self.current_task = None
        self.workspace_path = os.path.join(
            os.path.dirname(__file__), "..", "shared_workspace"
        )
        self.rules_count = self._count_existing_rules()
        logger.info("GOD AGENT: Initialized with brain=%s", self.model)

    def _load_brain(self) -> str:
        """Read the configured brain from the database."""
        try:
            return get_god_brain()
        except Exception as e:
            logger.warning("GOD AGENT: Could not load brain from DB (%s), using fallback", e)
            return "qwen3.5:9b"

    def _set_state(self, state: str, task: str = None):
        """Update agent state (logged, and can broadcast via API later)."""
        self.state = state
        self.current_task = task
        logger.info("GOD [%s]: %s", state, task or "")

    def _count_existing_rules(self) -> int:
        """Count existing rules in RULES.md to number new ones correctly."""
        rules_path = os.path.join(self.workspace_path, "RULES.md")
        if not os.path.exists(rules_path):
            return 0
        with open(rules_path, "r", encoding="utf-8") as f:
            content = f.read()
        return len(re.findall(r'^## Rule \d+', content, re.MULTILINE))

    def _query_with_fallback(self, prompt: str) -> Optional[str]:
        """
        Tiered fallback query mechanism for the God Agent:
        1. Paid/Primary Model (Gemini/Claude via Vault)
        2. Cloud Ollama instances
        3. Local Offline Ollama
        """
        # Tier 1: Paid/Primary Model
        logger.info("GOD AGENT: Tier 1 - Querying primary model: %s", self.model)
        resp = _query_brain(prompt, model=self.model)
        if resp: return resp
        
        # Tier 2: Cloud Ollama Nodes
        cloud_nodes = [
            os.getenv("OLLAMA_CLOUD_1", "http://cloud1.ollama.internal:11434/api/generate"),
            os.getenv("OLLAMA_CLOUD_2", "http://cloud2.ollama.internal:11434/api/generate")
        ]
        
        from anatomy.brain_dispatcher import query_ollama
        for i, cloud_url in enumerate(cloud_nodes):
            logger.warning("GOD AGENT: Tier 1 exhausted. Tier 2 - Querying Cloud Ollama Node %d...", i+1)
            resp = query_ollama(prompt, system=GOD_SOUL, model="qwen3.5:9b", url_override=cloud_url)
            if resp: return resp
            
        # Tier 3: Local Offline Ollama
        logger.warning("GOD AGENT: Cloud Ollama nodes exhausted. Tier 3 - Querying Local Offline Ollama...")
        resp = query_ollama(prompt, system=GOD_SOUL, model="qwen3.5:9b")
        return resp

    # ------------------------------------------
    # CORE: Analyze a crash traceback
    # ------------------------------------------
    def analyze_crash(self, traceback_text: str) -> dict:
        """
        LIVE: Sends a crash traceback to local Ollama for analysis.
        Returns a structured patch recommendation.
        """
        self._set_state("HEALING", "Analyzing crash traceback via Ollama")

        # Step 1: Parse the traceback to find the offending file
        crash_file, crash_line = self._parse_traceback(traceback_text)

        # Step 2: Read the offending file content (if we can)
        file_context = ""
        if crash_file and os.path.exists(crash_file):
            try:
                with open(crash_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Get a window around the crash line (±10 lines)
                if crash_line:
                    start = max(0, crash_line - 11)
                    end = min(len(lines), crash_line + 10)
                    numbered = [f"{i+1}: {l}" for i, l in enumerate(lines[start:end], start=start)]
                    file_context = f"\n--- FILE: {crash_file} (lines {start+1}-{end}) ---\n" + "".join(numbered)
                else:
                    # Show last 30 lines if no line number
                    numbered = [f"{i+1}: {l}" for i, l in enumerate(lines[-30:])]
                    file_context = f"\n--- FILE: {crash_file} (last 30 lines) ---\n" + "".join(numbered)
            except Exception as e:
                file_context = f"\n[Could not read {crash_file}: {e}]"

        # Step 3: Build the prompt
        prompt = f"""CRASH TRACEBACK:
{traceback_text}
{file_context}

Analyze this crash and provide a JSON fix. Remember: output ONLY the JSON object, no other text."""

        # Step 4: Query the configured brain (dynamic provider) with fallback cascade
        raw_response = self._query_with_fallback(prompt)

        if not raw_response:
            self._set_state("ERROR", "Brain unreachable or timed out")
            return {
                "success": False,
                "error": "Brain unreachable",
                "traceback": traceback_text,
            }

        # Step 5: Parse the LLM's JSON response
        analysis = _extract_json(raw_response)

        if not analysis:
            logger.warning("GOD AGENT: Could not parse LLM response as JSON")
            logger.debug("GOD AGENT: Raw response: %s", raw_response[:500])
            self._set_state("ERROR", "Could not parse LLM response")
            return {
                "success": False,
                "error": "Could not parse LLM response",
                "raw_response": raw_response[:500],
                "traceback": traceback_text,
            }

        # Add metadata
        analysis["success"] = True
        analysis["model_used"] = self.model
        analysis["timestamp"] = datetime.now().isoformat()

        fixable = analysis.get("fixable", True)
        if fixable and analysis.get("old_code") and analysis.get("new_code"):
            self._set_state("WAITING", f"Patch ready for {analysis.get('file', 'unknown')}")
            logger.info("GOD AGENT: Patch ready — root_cause: %s", analysis.get("root_cause", "unknown"))
        else:
            self._set_state("WAITING", "Crash analyzed but no auto-fix possible")
            logger.info("GOD AGENT: No auto-fix — reason: %s", analysis.get("reason", analysis.get("root_cause", "unknown")))

        return analysis

    # ------------------------------------------
    # CORE: Apply a patch to a file
    # ------------------------------------------
    def apply_patch(self, analysis: dict) -> bool:
        """
        Apply the God Agent's recommended patch to the offending file.
        Safety protocol:
            1. Git stash current state as a backup
            2. Apply the patch
            3. Validate with py_compile
            4. If compile fails → git checkout to rollback
        Returns True if the patch was applied and validated successfully.
        """
        import subprocess
        import py_compile

        file_path = analysis.get("file")
        old_code = analysis.get("old_code")
        new_code = analysis.get("new_code")

        if not all([file_path, old_code, new_code]):
            logger.error("GOD AGENT: Incomplete patch — missing file/old_code/new_code")
            return False

        # Resolve the file path relative to the project root
        project_root = os.path.join(os.path.dirname(__file__), "..", "..")
        if not os.path.isabs(file_path):
            file_path = os.path.join(project_root, file_path)
            file_path = os.path.normpath(file_path)

        if not os.path.exists(file_path):
            logger.error("GOD AGENT: File not found: %s", file_path)
            return False

        self._set_state("HEALING", f"Patching {os.path.basename(file_path)}")

        # ── SAFETY: Stash current state ──
        stash_label = f"pre-heal-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        try:
            subprocess.run(
                ["git", "stash", "push", "-m", stash_label, "--", file_path],
                cwd=project_root, capture_output=True, text=True, timeout=10,
            )
            logger.info("GOD AGENT: Stashed backup: %s", stash_label)
        except Exception as e:
            logger.warning("GOD AGENT: Git stash failed (continuing anyway): %s", e)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if old_code not in content:
                # Try with normalized whitespace
                normalized = content.replace('\r\n', '\n')
                old_normalized = old_code.replace('\r\n', '\n')
                if old_normalized not in normalized:
                    logger.error("GOD AGENT: Patch target not found in %s", file_path)
                    self._set_state("ERROR", "Patch target not found")
                    # Restore from stash
                    self._restore_stash(project_root)
                    return False
                content = normalized
                old_code = old_normalized

            patched = content.replace(old_code, new_code, 1)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(patched)

            # ── SAFETY: Validate with py_compile ──
            if file_path.endswith(".py"):
                try:
                    py_compile.compile(file_path, doraise=True)
                    logger.info("GOD AGENT: py_compile validation PASSED: %s", file_path)
                except py_compile.PyCompileError as ce:
                    logger.error("GOD AGENT: py_compile FAILED — rolling back: %s", ce)
                    self._set_state("ERROR", f"Patch broke syntax: {ce}")
                    # Rollback: restore original content
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    logger.info("GOD AGENT: Rollback complete — file restored")
                    return False

            logger.info("GOD AGENT: Successfully patched: %s", file_path)
            self._set_state("SUCCESS", f"Patched {os.path.basename(file_path)}")
            # Drop the stash since patch succeeded
            self._drop_stash(project_root, stash_label)
            return True

        except Exception as e:
            logger.error("GOD AGENT: Patch failed: %s", str(e))
            self._set_state("ERROR", f"Patch failed: {str(e)}")
            # Try to restore from stash
            self._restore_stash(project_root)
            return False

    def _restore_stash(self, project_root: str) -> None:
        """Attempt to restore the most recent git stash."""
        import subprocess
        try:
            subprocess.run(
                ["git", "stash", "pop"],
                cwd=project_root, capture_output=True, text=True, timeout=10,
            )
            logger.info("GOD AGENT: Stash restored (rollback)")
        except Exception as e:
            logger.warning("GOD AGENT: Stash restore failed: %s", e)

    def _drop_stash(self, project_root: str, label: str) -> None:
        """Drop a stash entry after successful patch."""
        import subprocess
        try:
            subprocess.run(
                ["git", "stash", "drop"],
                cwd=project_root, capture_output=True, text=True, timeout=10,
            )
            logger.info("GOD AGENT: Stash dropped (patch verified): %s", label)
        except Exception:
            pass  # Non-critical

    # ------------------------------------------
    # CORE: Write a new RULE to RULES.md
    # ------------------------------------------
    def write_rule(self, analysis: dict) -> None:
        """
        Forge a new Rule in RULES.md from the God Agent's analysis.
        Every fix becomes a law to prevent the same mistake.
        """
        title = analysis.get("rule_title", "Unnamed Rule")
        description = analysis.get("rule_description", analysis.get("root_cause", "No description"))
        
        self.rules_count += 1
        rule_number = self.rules_count

        rules_path = os.path.join(self.workspace_path, "RULES.md")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        new_rule = f"""
## Rule {rule_number}: {title}
> Forged: {timestamp} | Model: {self.model}

{description}

---
"""
        with open(rules_path, "a", encoding="utf-8") as f:
            f.write(new_rule)

        logger.info("GOD AGENT: Wrote Rule %d: %s", rule_number, title)
        self._set_state("SUCCESS", f"Rule {rule_number} written")

    # ------------------------------------------
    # FULL HEALING CYCLE
    # ------------------------------------------
    def heal(self, traceback_text: str, auto_apply: bool = False) -> dict:
        """
        Full healing pipeline:
        1. Analyze the crash via Ollama
        2. Optionally apply the patch (auto_apply = GOD mode)
        3. Write the lesson as a Rule

        Args:
            traceback_text: The raw Python traceback
            auto_apply: If True (GOD mode), apply patch immediately.
                        If False (BOSS mode), just return the recommendation.

        Returns:
            The analysis dict with applied=True/False
        """
        logger.info("=" * 60)
        logger.info("GOD AGENT: HEALING CYCLE STARTED")
        logger.info("=" * 60)

        # Step 1: Analyze
        analysis = self.analyze_crash(traceback_text)

        if not analysis.get("success"):
            logger.error("GOD AGENT: Analysis failed — cannot heal")
            return analysis

        # Check if fixable via simple patch
        if not analysis.get("fixable", True) or not analysis.get("old_code"):
            logger.warning("GOD AGENT: Crash analyzed but not auto-fixable via simple string patch. Summoning SRE...")
            crash_file, _ = self._parse_traceback(traceback_text)
            if self.summon_sre(traceback_text, crash_file or "unknown"):
                analysis["applied"] = True
                analysis["root_cause"] = "SRE summoned and executed fix successfully."
                self.write_rule(analysis)
            else:
                analysis["applied"] = False
            return analysis

        # Step 2: Apply patch (if GOD mode)
        if auto_apply:
            logger.info("GOD AGENT: GOD MODE — applying patch immediately")
            applied = self.apply_patch(analysis)
            analysis["applied"] = applied

            if applied:
                # Step 3: Write the Rule
                self.write_rule(analysis)
        else:
            logger.info("GOD AGENT: BOSS MODE — patch queued for human approval")
            analysis["applied"] = False

        # Step 4: Log the healing action to the database
        try:
            log_heal_action(
                crash_file=analysis.get("file"),
                root_cause=analysis.get("root_cause"),
                patch_applied=analysis.get("applied", False),
                rule_written=analysis.get("applied", False),
                model_used=self.model,
            )
        except Exception as e:
            logger.warning("GOD AGENT: Could not log heal action: %s", e)

        logger.info("=" * 60)
        logger.info("GOD AGENT: HEALING CYCLE COMPLETE — applied=%s", analysis.get("applied"))
        logger.info("=" * 60)

        return analysis

    # ------------------------------------------
    # HELPERS
    # ------------------------------------------
    def _parse_traceback(self, text: str) -> tuple:
        """Extract the last file and line number from a Python traceback."""
        file_path = None
        line_num = None

        for line in text.strip().split("\n"):
            if 'File "' in line:
                parts = line.split('"')
                if len(parts) >= 2:
                    file_path = parts[1]
                if "line " in line:
                    try:
                        line_num = int(line.split("line ")[1].split(",")[0])
                    except (ValueError, IndexError):
                        pass

        return file_path, line_num

    def summon_sre(self, traceback_text: str, crash_file: str) -> bool:
        """
        Summons the agency-incident-response-commander synchronously 
        to fix a framework crash that the God Agent couldn't string-patch.
        """
        logger.info("🚨 GOD AGENT: Summoning SRE (agency-incident-response-commander)...")
        try:
            from workforce.agency.agency_worker import AgencyWorker
            sre = AgencyWorker("agency-incident-response-commander")
            
            # Ensure it has necessary tools
            if "bash" not in sre.hands: sre.hands.append("bash")
            if "query_graph" not in sre.hands: sre.hands.append("query_graph")
            
            description = (
                f"CRITICAL SYSTEM CRASH! The framework crashed. You are running in God Mode outside the queue to save it.\n\n"
                f"Traceback:\n{traceback_text}\n\n"
                f"Please fix the code in {crash_file}. Use 'query_graph' to understand dependencies, then use 'bash' to patch the file."
            )
            
            result = sre.execute_task(
                description=description,
                inputs={"crash_file": crash_file, "traceback": traceback_text}
            )
            
            if result.get("status") == "SUCCESS":
                logger.info("🚨 GOD AGENT: SRE successfully completed the patch task.")
                return True
            else:
                logger.error("🚨 GOD AGENT: SRE failed to fix the crash: %s", result)
                return False
                
        except Exception as e:
            logger.error("🚨 GOD AGENT: Failed to summon SRE: %s", e)
            return False

    def check_health(self) -> dict:
        """Quick health check — is Ollama reachable?"""
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            models = [m["name"] for m in resp.json().get("models", [])]
            return {
                "ollama_alive": True,
                "models_available": models,
                "god_model": self.model,
                "god_model_available": any(self.model.split(":")[0] in m for m in models),
            }
        except Exception:
            return {"ollama_alive": False, "models_available": [], "god_model": self.model}


# ==========================================
# 🧪 STANDALONE TEST
# ==========================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    god = GodAgent()

    # Health check
    health = god.check_health()
    print(f"\nHealth: {json.dumps(health, indent=2)}")

    if not health["ollama_alive"]:
        print("\n[FATAL] Ollama is not running. Start it with: ollama serve")
        exit(1)

    # Test with a sample crash
    sample_crash = """Traceback (most recent call last):
  File "F:/012A_Github/choppingblock/backend_engine/main.py", line 38, in run
    result = 1 / 0
ZeroDivisionError: division by zero"""

    print("\n--- Testing crash analysis ---")
    result = god.heal(sample_crash, auto_apply=False)  # BOSS mode — don't apply
    print(f"\nResult: {json.dumps(result, indent=2, default=str)}")
