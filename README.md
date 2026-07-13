# AI-Powered CRM HCP System

This repository contains a full-stack Customer Relationship Management (CRM) healthcare professional (HCP) module designed specifically for pharmaceutical/medical field representatives. It features a premium, glassmorphism React UI and a Python FastAPI backend powered by an AI agent framework using LangGraph.

Representatives can log and edit HCP interactions via a **structured form** or interact using an **AI Assistant chat** that automatically parses text inputs, triggers database tools, updates form fields, and logs details.

---

## 🛠️ Technology Stack

- **Frontend**: React (Vite), Redux Toolkit (state management), Lucide Icons, Vanilla CSS (premium dark glassmorphism theme, Google Inter font).
- **Backend**: Python 3.13, FastAPI (API layer), SQLAlchemy (ORM), SQLite (local database).
- **AI Agent Framework**: LangGraph, LangChain Core, LangChain Groq (`gemma2-9b-it` or `llama-3.3-70b-versatile` model), MockAgent (automatic fallback during Groq quota exhaustion).

---
## Architecture

React (Vite)
    ↓
Redux Toolkit
    ↓
Axios
    ↓
FastAPI
    ↓
LangGraph
    ↓
LangChain Tools
    ↓
Groq LLM
    ↓
SQLAlchemy ORM
    ↓
SQLite

---
## 🗂️ Project Directory Structure

```text
crm-ai-assignment1/
│
├── backend/                   # Python FastAPI Backend
│   ├── .venv/                 # Python Virtual Environment
│   ├── .env                   # Configuration & API Keys
│   ├── requirements.txt       # Backend Python dependencies
│   ├── main.py                # FastAPI endpoints & CORS
│   ├── database.py            # SQLite connection, session & seeding
│   ├── models.py              # SQLAlchemy database schemas
│   ├── schemas.py             # Pydantic validation schemas
│   ├── agent.py               # LangGraph AI Agent & Custom Tools
│   └── test_agent.py          # Automated integration test script
│
├── frontend/                  # React Frontend
│   ├── src/
│   │   ├── assets/
│   │   ├── store/
│   │   │   ├── index.js       # Redux store config
│   │   │   └── crmSlice.js    # Store state slice & async thunks
│   │   ├── App.jsx            # Main React Dashboard Component
│   │   ├── index.css          # Premium glassmorphic styles
│   │   └── main.jsx           # React app entry point
│   ├── package.json           # Frontend JS dependencies
│   └── vite.config.js         # Vite configuration
│
└── README.md                  # Setup & execution guide (this file)
```

---

## ⚙️ Setup and Installation

### Prerequisites
- Node.js (v18 or higher)
- Python (3.10 to 3.13)

### 1. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv .venv
   
   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   # Windows Command Prompt
   .venv\Scripts\activate.bat
   # Linux/macOS
   source .venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create/Configure the environment variables in `backend/.env`:
   ```ini
   DATABASE_URL=sqlite:///./crm.db
   GROQ_API_KEY=your_groq_api_token_here
   ```
   > **Note**: If you don't have a Groq API token, you can leave `GROQ_API_KEY` blank. The backend will automatically fall back to an internal **Mock Agent** mode that simulates tool execution, entity extraction, and responses, keeping the app 100% functional.

5. Start the backend development server:
   ```bash
   python main.py
   ```
   The backend will start on **`http://localhost:8000`** and automatically initialize and seed the SQLite database with sample HCPs, clinical trials, and sample packages.

---

### 2. Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The frontend will start on **`http://localhost:5173/`**.

---

## 🧪 Running Automated Tests

To verify that the database seeding, LangGraph agent nodes, and tool-calling execution operate correctly, you can run the automated script from the `backend/` folder:

```bash
cd backend
.venv\Scripts\python test_agent.py
```

This script seeds the local database and queries the agent using tool-calling to ensure both mock/live agents trigger database operations successfully.

---

## 🤖 LangGraph Agent & Tools

The agent manages HCP logs dynamically using a compiled state graph. When the agent receives a text prompt, it uses tool-calling to execute database interactions, then outputs both an assistant text response and an updated JSON `form_state` block that synchronizes the React UI.

The agent implements six tools:
1. **`search_hcp`**: Queries doctor profiles from database matching name queries.
2. **`get_hcp_history`**: Fetches the recent past interactions list for the doctor to provide historical context.
3. **`search_materials`**: Searches through clinical trial papers, brochures, and drug starter samples.
4. **`log_interaction`** *(Required)*: Saves a new interaction record to the database, links materials/samples, and reduces sample stock quantity.
5. **`edit_interaction`** *(Required)*: Modifies fields (e.g. sentiment, topics) on an existing logged interaction.
6. **`schedule_followup`**: Schedules follow-up calendar tasks linked to the doctor's profile.
