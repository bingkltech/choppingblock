# 📎 ChoppingBlock: The Agency-Centric Foundry

We are entering the era of Generative Engineering. ChoppingBlock is a zero-human-coding company dedicated to the total automation of the software lifecycle. Our proprietary AI stack interprets natural language requirements to build scalable, enterprise-grade software without a single keystroke from a human programmer.

---

## 🌟 Core Innovations

1. **The Agency Roster:** The foundry integrates a dynamic, department-based workforce of over 184 specialized AI agents (Engineering, Marketing, Design, Product).
2. **The Caveman Primitives:** Agents are equipped with raw CLI tools (`gh`, `docker`, `bash`, `ollama`, `jules`) which they use to forge dynamic workflows.
3. **Stigmergic Memory:** Agents communicate exclusively by modifying the shared GitHub repository or reading SKILL.md definition files. The CEO leads by writing `ARCHITECTURE.md`, and the God Agent oversees system health.
4. **Self-Healing Infrastructure:** The AI backend is wrapped in `god_process.py`. If the AI crashes its own framework, the **God Agent** catches the Python traceback, safely patches the framework's source code, and hot-restarts the server.

---

## 🎒 Part 1: Prerequisites

To build and run this Agency architecture, gather these specific tools and keys before writing a single line of code.

### 1. The "Caveman Primitives" (Local Dependencies)
- **Python 3.11+** (For the AI Backend and God Process)
- **Node.js 20+** (For the React Visual HQ)
- **Docker Desktop** (Must be running in the background for QA sandboxes)
- **Ollama** (Installed locally for swarm deployment)
- **GitHub CLI (`gh`)** (Installed and authenticated)

### 2. The API Vault (Credentials to generate in your `.env`)
- **1x Premium API Key:** Anthropic (`CLAUDE_API_KEY`) or OpenAI (`OPENAI_API_KEY`) for executive oversight.
- **5x Free Cloud API Keys:** Google/Gemini keys (`JULES_KEY_1` through `JULES_KEY_5`) for the coding agents.
- **1x GitHub Personal Access Token (PAT)**

---

## 🏛️ Part 2: Detailed Code Structure

```plaintext
choppingblock/
│
├── README.md                         # The Master Documentation
├── .env                              # API Keys
│
├── god_process.py                    # 👑 THE WATCHDOG
│
├── backend_engine/                   # 🧠 THE NERVOUS SYSTEM
│   ├── database/                     # SQLite ledger and metrics
│   ├── anatomy/                      # Base classes and Orchestrator
│   ├── caveman_tools/                # CLI wrappers
│   ├── routers/                      # FastAPI endpoints
│   └── workforce/                    # 🏢 THE AGENCY DEPARTMENTS
│       ├── executives/               # CEO & God Agent
│       ├── system_agents/            # Jules, QA, Ops
│       └── agency/                   # AgencyWorker (loads 184 dynamic agents)
│
└── visual_hq/                        # 👁️ THE VIRTUAL OFFICE (React)
    ├── package.json
    ├── src/
    │   ├── App.jsx
    │   ├── components/
    │   │   ├── AgentManager.jsx      # The Dashboard viewing all 184 agents
    │   │   ├── TaskQueue.jsx         # Live task queue view
    │   │   └── ...
    │   └── hooks/
```

---

## 🏢 Part 3: The Agency Workforce

| Department | Workforce | Brain (Model) | Role in the Foundry |
| :--- | :--- | :--- | :--- |
| **Executives** | CEO & God Agent | Premium (Claude/GPT-4o) | Planning, architecture, self-healing |
| **Agency Agents** | 184 Specialized Agents | Gemini / Various | Dynamic execution of specific domain tasks (Engineering, Design, Marketing, etc.) |
| **System Ops** | Jules, QA, Ops | Cloud & Local Swarm | PR Merging, Docker Testing, General Cloud Operations |

---

## 🚀 Part 4: Boot Sequence

*Never run the AI backend directly. Always use the God Watchdog to enable self-healing.*

```bash
# Terminal 1: Start the Visual Office
cd visual_hq
npm install
npm run dev

# Terminal 2: Start the Self-Healing Backend
cd backend_engine
pip install -r requirements.txt
python ../god_process.py
```
