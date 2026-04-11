import os
import requests
import json

# ==========================================
# 🧠 THE SOUL (SYSTEM PROMPT)
# ==========================================
ANTIGRAVITY_SOUL = """
[IDENTITY]
You are Antigravity (antigravity.google), an elite Tier-2 Cloud Laborer and Lead Developer within the Paperclip Reborn Foundry.
You are a pure execution engine. You do not have a conversational interface. You DO NOT greet, explain your thought process, or apologize. 
You speak exclusively in raw code, CLI commands (bash, git, gh), and file modifications.

[OPERATIONAL PARADIGM: STIGMERGY]
You operate in a shared Git repository. Your memory and context exist within this environment. Your actions are governed by two physical files:
1. `ARCHITECTURE.md`: Written by the CEO. This defines the project plan. Do not deviate from it.
2. `RULES.md`: Written by the God Agent. These are the absolute laws of the codebase, forged from your past mistakes. If RULES.md contradicts standard programming conventions, RULES.md wins.

[YOUR WORKFLOW & CAVEMAN TOOLS]
When you receive a Task payload:
1. INGEST: Read the provided repo context, `ARCHITECTURE.md`, and `RULES.md`.
2. BRANCH: Output the CLI commands to branch off `main` (e.g., `git checkout -b feature/name`).
3. EXECUTE: Write complete, production-ready code. Output the exact bash commands to write the files (e.g., using `cat << 'EOF' > filepath`). NEVER use placeholders.
4. PUSH: Output the commands to commit, push, and use the `gh` CLI to open a Pull Request.

[THE QA VERIFICATION LOOP]
You do not have merge privileges. When you submit your PR, a Tier-3 Local QA Agent will test it in a Docker sandbox.
If your code fails, the QA Agent will reply with a RAW TERMINAL STACK TRACE. 
If you receive a stack trace:
- DO NOT argue. 
- DO NOT explain why the code failed. 
- DO NOT output filler text like "I apologize, I will fix this."
- SIMPLY read the error, output the CLI commands to fix the code, and push the updated commit.
"""

class CloudLaborer:
    def __init__(self, account_name: str, api_key_env_var: str):
        self.account_name = account_name
        self.api_key = os.getenv(api_key_env_var, "YOUR_GEMINI_API_KEY_HERE")
        
    def execute_task(self, task_description: str, repo_context: str):
        """
        Wakes up Antigravity, injects its Soul, and gives it the Stigmergic context.
        """
        print(f"[{self.account_name}] 🔵 Waking up... Ingesting Stigmergic Context.")
        
        # Structure the payload for the Cloud API (Google Gemini syntax)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={self.api_key}"
        
        user_payload = f"""
        [CURRENT REPO CONTEXT (Stigmergy)]
        {repo_context}
        
        [YOUR TASK]
        {task_description}
        """

        payload = {
            "system_instruction": {
                "parts": [{"text": ANTIGRAVITY_SOUL}]
            },
            "contents": [{
                "role": "user", 
                "parts": [{"text": user_payload}]
            }],
            "generationConfig": {
                "temperature": 0.1, # Extremely low temp for strict, logical, deterministic coding
                "topP": 0.95
            }
        }
        
        headers = {"Content-Type": "application/json"}
        
        print(f"[{self.account_name}] 🟡 Equipping Caveman Tools. Generating Code...")
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            # Extract the raw output (which will be CLI commands based on the Soul)
            result_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            
            print(f"[{self.account_name}] 🟢 Task Complete. Outputting Execution Commands:\n")
            return result_text
            
        except Exception as e:
            print(f"[{self.account_name}] 🔴 FATAL API ERROR: {str(e)}")
            # In the full app, the God Agent catches this
            return None

# ==========================================
# 🧪 THE FIRST TEST (Run this file directly)
# ==========================================
if __name__ == "__main__":
    # Initialize Antigravity (Ensure your environment variable is set!)
    antigravity = CloudLaborer(account_name="antigravity.google", api_key_env_var="JULES_KEY_1")
    
    # 1. Mocking Stigmergy (What it natively reads from the repo)
    mock_stigmergy = """
    File: ARCHITECTURE.md
    - We are using Python 3.11+. The core backend runs on FastAPI.
    
    File: RULES.md
    - Always include type hints. 
    - Never use print() in production, use standard logging.
    """
    
    # 2. The First Task assigned by the CEO
    mock_task = "Create a new file called `api_ledger.db` initialization script (`db_manager.py`) using SQLite3. It must have a table to track API usage for 5 accounts."
    
    # 3. Dispatch the task
    output = antigravity.execute_task(mock_task, mock_stigmergy)
    print(output)
