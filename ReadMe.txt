Part 1: Things Needed Before You Start (Prerequisites)
To build and run this Tri-Tiered architecture, you need to gather these specific tools and keys before you write a single line of code.

1. The "Caveman Primitives" (Software to Install Locally):

Python 3.11+ (For the AI Backend and God Process).

Node.js 20+ (For the React Visual HQ).

Docker Desktop (Must be running in the background for the QA Agent's sandbox testing).

Ollama (Installed locally. Run ollama pull llama3 and ollama pull qwen2.5-coder to have your local swarm ready).

GitHub CLI (gh) (Installed and authenticated to your GitHub account).

Claude Code CLI (Optional, but highly recommended as a primitive tool for the God Agent).

2. The API Vault (Credentials to Generate in your .env):

1x Premium API Key: Anthropic (CLAUDE_API_KEY) or OpenAI (OPENAI_API_KEY) for the CEO and God Agent to utilize massive context windows.

5x Free Cloud API Keys: Google/Gemini generative keys (JULES_KEY_1 through JULES_KEY_5) to power the Cloud Laborers.

1x GitHub Personal Access Token (PAT): Must have read/write access to code, PRs, and Webhooks.


See Structure code as Part 2


PArt 3;
# 📎 Paperclip Reborn: The Visual AI Foundry

**Paperclip Reborn** is a local-first, self-healing, visual AI software development agency. It abandons fragile "chat-based" multi-agent loops in favor of **Caveman Primitives**, **Stigmergic Memory**, and a **Tri-Tiered Cognitive Architecture**, all managed via a 2D Virtual Headquarters.

## 🌟 Core Innovations

1. **The Caveman Primitives:** Agents are not restricted to rigid Python scripts. They are equipped with raw CLI tools (`gh`, `docker`, `bash`, `ollama`) which they strike together to forge dynamic workflows. Tools can be visually dragged and dropped into an agent's "Hands" via the UI.
2. **Stigmergic Memory:** Agents do not chat with each other (preventing context degradation and hallucination). They communicate exclusively by modifying the shared GitHub repository. The CEO leads by writing `ARCHITECTURE.md`, and the God Agent permanently upgrades workers by writing into `RULES.md`.
3. **Self-Healing Infrastructure:** The AI backend is wrapped in `god_process.py`. If the AI crashes its own framework, the **God Agent** catches the Python traceback, safely patches the framework's source code, and hot-restarts the server.
4. **Day/Night Shift Toggle:** 
   - **☀️ Day Shift (Boss Mode):** The app pauses at critical junctures for human GUI approval.
   - **🌙 Night Shift (God Mode):** The God Agent assumes `SUDO` privileges, autonomously resolving infinite loops and managing API limits while you sleep.

## 🏛️ Tri-Tiered Workforce

| Tier | Workforce | Brain (Model) | Role in the Foundry |
| :--- | :--- | :--- | :--- |
| **Tier 1** | CEO & God Agent | Premium (Claude/GPT-4o) | Massive context. Plans architecture, heals the app, upgrades rules. |
| **Tier 2** | Cloud Laborers | 5x Free Cloud APIs | Heavy generation. Natively reads the repo, writes code, submits PRs. Load-balanced locally. |
| **Tier 3** | Local Swarm | Ollama (Local) | Zero cost. Uses Docker to run PRs, acts as ruthless QA, and enforces repo hygiene. |

## 🚀 Boot Sequence
*Never run the AI backend directly. Always use the God Watchdog to enable self-healing.*
```bash
# Terminal 1: Start the Visual Office
cd visual_hq && npm install && npm run dev

# Terminal 2: Start the Self-Healing Backend
cd backend_engine && pip install -r requirements.txt && python ../god_process.py



Part 4 

---

### 📝 Part 4: The Master To-Do List (Execution Plan)

Do not try to build this all at once. Build it sequentially to ensure the foundation is stable before adding the complex AI layers.

#### **Phase 1: The Skeleton & Watchdog (Backend Base)**
- [ ] Initialize the Git repo and create the directory structure.
- [ ] Create `.env` and `backend_engine/requirements.txt`.
- [ ] Write `god_process.py`: Use `subprocess.Popen` to run a dummy `main.py`. Intentionally put a syntax error in `main.py` and write the logic for `god_process.py` to catch the `stderr` crash log.
- [ ] Setup the FastAPI server in `main.py` with a basic WebSocket endpoint `/ws/heartbeat`.

#### **Phase 2: Agent Anatomy & The Ledger**
- [ ] Create `ledger.db` and write `db_manager.py` to create two SQLite tables: `API_Usage` (tracks the 5 Jules accounts) and `Agent_Status` (tracks what each agent is doing).
- [ ] Write `agent_core.py`: Create the Python `Class BaseAgent:`. Give it properties for `soul` (system prompt), `brain` (current model), `hands` (equipped tools array), and a method `broadcast_heartbeat()` that pushes its status to the WebSocket.

#### **Phase 3: The Caveman Primitives (Tools)**
- [ ] Write `primitive_bash.py`: A Python function that takes a string command, runs it via `subprocess`, and returns the `stdout/stderr`. *(Crucial: Add a strict timeout parameter so agents don't freeze your OS).*
- [ ] Write `primitive_gh.py`: Use Python to trigger the `gh cli` to fetch the diff of a specific Pull Request or create a branch.
- [ ] Write `primitive_docker.py`: Write a function that spins up a lightweight Alpine/Ubuntu container, runs a bash command inside it, captures the test logs, and destroys the container.

#### **Phase 4: The Tri-Tier Logic**
- [ ] **Tier 2 (Cloud):** Write `jules_router.py`. Build a function that checks `ledger.db` for the Jules account with the lowest token usage today, grabs its API key, and sends a task to the Cloud Provider.
- [ ] **Tier 3 (Local):** Write `qa_agent.py`. Connect it to local Ollama. Equip it with `primitive_docker.py`.
- [ ] **Tier 1 (Execs):** Write `god_agent.py`. Connect it to the Premium API key. Give it file I/O tools to read/write framework Python files.

#### **Phase 5: The Visual HQ (Frontend)**
- [ ] Scaffold a React app (`npm create vite@latest visual_hq -- --template react`).
- [ ] Setup the WebSocket client hook (`useHeartbeat.js`) to listen to `ws://localhost:8000/ws/heartbeat`.
- [ ] Build the `OfficeMap.jsx` component to render visual desks for the Jules accounts, QA, CEO, and God Agent.
- [ ] Link the WebSocket data so that when `qa_agent.py` changes state to `[🔵 TESTING DOCKER]`, the QA desk on the React frontend visually animates.
- [ ] Build the Sidebar Dossier to manually change an agent's Model via UI dropdown.

#### **Phase 6: Integration & The Stigmergic Loop**
- [ ] Initialize a dummy target repository inside the `shared_workspace/` folder.
- [ ] Run a full end-to-end test loop: 
    1. CEO writes a task in `ARCHITECTURE.md`.
    2. Jules Router reads it, generates a python script, and submits a branch.
    3. QA pulls the branch into Docker, tests it, and broadcasts the terminal result back to Jules until it passes.

---









