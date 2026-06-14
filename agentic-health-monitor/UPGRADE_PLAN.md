# UPGRADE_PLAN.md
# Agentic Health Monitor — Microsoft Agents League Hackathon Upgrade Plan
# Category: Reasoning Agents

---

## 1. CURRENT STATE ANALYSIS

### 1.1 What Exists and Works

After reading every file in the project, the current system is:

**Backend Agent Pipeline (fully functional):**
```
POST /analyze-symptoms
  Step 1 → symptom_agent.py :: interpret_symptoms()
             - LLM call to Groq (llama-3.3-70b-versatile)
             - Returns: body_system, possible_conditions, risk_level, is_emergency
  Step 2 → symptom_agent.py :: summarize_symptoms()
             - LLM call with RAG context injected
             - Returns: summary, concern_level, follow_up_needed
  Step 3 → clarification_agent.py :: generate_follow_up_questions()
             - LLM call grounded in interpretation output
             - Returns: 5 targeted questions as JSON array
             - Has 3-retry logic + body-system fallback
  Step 4 → rag_tool.py :: retrieve_as_dicts()
             - ChromaDB query, returns top-k chunks

POST /final-assessment
  Step 1 → risk_agent.py :: assess_risk()
             - LLM call with symptoms + follow-up answers + RAG context
             - Returns: conditions with scores, risk_level, urgency, explanation
  Step 2 → recommendation_agent.py :: get_full_recommendation()
             - LLM call on risk output
             - Returns: recommendation, next_steps, disclaimer
```

**Frontend (fully functional):**
- Login / Signup — local auth via localStorage (supabaseClient.js is mocked)
- SymptomForm → FollowUp → Report → History flow works end-to-end
- Dashboard with recharts risk trend visualization
- i18n (English, Hindi, Marathi)
- PDF download via jspdf
- Share report via backend token

**RAG System:**
- 4 medical docs: chest_pain, diabetes, fever, hypertension
- ChromaDB local vector store
- OpenAI embedding with bag-of-words fallback if no key

**Infrastructure:**
- SQLite local database (reports.db)
- FastAPI with lifespan events
- Supabase backend client exists but requires real credentials

---

### 1.2 What Is Missing / Weak for Hackathon

After analysis, the following gaps exist:

**Agent Architecture Gaps:**
1. No `agent_trace` — the pipeline runs but judges cannot SEE the reasoning chain
2. No memory/context — each session is stateless, agents don't accumulate reasoning
3. No `confidence_score` surfaced to the UI — it exists in the API but is hidden
4. No `agent_steps` returned in the API response — judges can't verify multi-agent behavior
5. No `is_emergency` flag surfaced to the UI for immediate visual alert
6. The orchestrator has good console print debugging but no structured trace object
7. No `body_system` displayed in UI — the interpreter result is invisible to users

**RAG Gaps:**
8. Only 4 medical docs — very narrow knowledge base
9. No stroke, hepatic, neurological, sepsis, or endocrine documents
10. The `retriever.py` file exists but is unused (only `vector_store.py` is used)
11. RAG results are passed to agents but not shown meaningfully in the UI

**UI/UX Gaps for Demo:**
12. No visual agent pipeline visualization (no step-by-step progress)
13. No emergency banner/alert when `is_emergency=true`
14. No `body_system` badge on FollowUp or Report pages
15. `symptom_summary` card on FollowUp exists but has no context about WHY questions were chosen
16. Report page doesn't explain agent reasoning clearly for a hackathon demo
17. No "Agent Reasoning Trace" panel that shows what each agent decided

**Technical/Completeness Gaps:**
18. `agent_schema.py` defines `ClarificationAgentOutput` with `priority` per question but `clarification_agent.py` doesn't use it — the schema is orphaned
19. `share.py` route uses `supabase_client.py` which requires real Supabase — will crash without credentials
20. `save_report.py` calls `save_assessment()` via Supabase — same issue
21. `supabase_db.py` will throw `RuntimeError` if credentials are missing
22. `AnalyzeResponse` schema does not include `interpretation` (body_system, conditions, risk_level) — Agent 1 output is lost after Step 1 and never reaches the frontend
23. No hackathon demo video, architecture diagram, or pitch materials

---

## 2. UPGRADE PLAN

### Phase 1 — Agent Transparency (Core Hackathon Value)
*Makes the multi-agent reasoning visible to judges and users.*

**1A. Add `AgentTrace` to API responses**

Modify `output_schema.py`:
- Add `AgentTrace` model with fields: `agent_name`, `input_summary`, `output_summary`, `duration_ms`, `used_fallback`
- Add `agent_steps: List[AgentTrace]` to `AnalyzeResponse` and `FinalAssessmentResponse`
- Add `interpretation` field to `AnalyzeResponse` so Agent 1 result reaches frontend

File to modify: `backend/app/schemas/output_schema.py`

**1B. Orchestrator records trace**

Modify `orchestrator.py`:
- Wrap each agent call with timing (`time.perf_counter`)
- Build `AgentTrace` objects after each step
- Attach `agent_steps` list to both response objects
- Propagate `interpretation` (body_system, conditions, risk_level, is_emergency) from Agent 1 into `AnalyzeResponse`

File to modify: `backend/app/agents/orchestrator.py`

**1C. Emergency fast-path**

Modify `orchestrator.py`:
- If `interpretation.is_emergency=True` after Step 1, immediately set `concern_level=CRITICAL`
- Add `emergency_alert` boolean field to `AnalyzeResponse`
- This ensures the UI can show a red emergency banner before the user even answers questions

---

### Phase 2 — Expand RAG Knowledge Base
*Gives agents grounded medical context for all 7 body systems.*

**2A. Add missing medical documents**

Create new files in `medical_docs/`:
- `stroke_guidelines.txt` — FAST signs, TIA vs stroke, time-to-treatment
- `liver_hepatic_guidelines.txt` — jaundice causes, hepatitis, liver failure signs
- `neurological_guidelines.txt` — headache red flags, meningitis, seizure
- `sepsis_guidelines.txt` — sepsis criteria (qSOFA), early warning signs
- `respiratory_guidelines.txt` — asthma, COPD, pneumonia, PE warning signs
- `endocrine_guidelines.txt` — diabetic ketoacidosis, thyroid storm, hypoglycemia
- `musculoskeletal_guidelines.txt` — fracture signs, compartment syndrome, DVT

Files to create: 7 new `.txt` files in `medical_docs/`

**2B. Force re-index on startup**

Modify `vector_store.py` or `main.py` lifespan:
- After adding new docs, call `build_collection(force_reindex=False)` on startup
- This ensures new docs are indexed without wiping existing data

---

### Phase 3 — Frontend Agent Visualization
*Makes the hackathon demo visually impressive and clearly shows multi-agent reasoning.*

**3A. Agent Steps Panel on FollowUp page**

Modify `FollowUp.jsx`:
- Display collapsible "Agent Reasoning" section showing:
  - Agent 1: Body system identified, possible conditions, risk level
  - Agent 2: Concern level, rationale
  - Agent 3: Why these questions were chosen
- Use `analysis.interpretation` and `analysis.agent_steps` from API response
- Color-code by risk (green=low, yellow=moderate, orange=high, red=emergency)

File to modify: `frontend/src/pages/FollowUp.jsx`

**3B. Emergency Alert Banner**

Modify `FollowUp.jsx`:
- If `analysis.emergency_alert=true`, show a full-width red banner at the top:
  "⚠️ EMERGENCY DETECTED — Please call emergency services immediately"
- Banner should be dismissible but prominent
- Should also trigger on Report page if `risk_level=Emergency`

Files to modify: `frontend/src/pages/FollowUp.jsx`, `frontend/src/pages/Report.jsx`

**3C. Body System Badge on FollowUp and Report**

Modify `FollowUp.jsx` and `Report.jsx`:
- Show a badge below the patient card: "🫀 Cardiac System" / "🧠 Neurological" / "🫁 Respiratory" etc.
- Use `analysis.interpretation.body_system` from the response
- Each system gets a unique icon and color

**3D. Agent Trace Panel on Report page**

Modify `Report.jsx`:
- Add expandable "How the AI reasoned" section at the bottom of the report
- Shows each agent step: name, what it received, what it concluded, duration
- This is the key demo feature for judges to see the reasoning chain

File to modify: `frontend/src/pages/Report.jsx`

**3E. Live Agent Progress on SymptomForm**

Modify `SymptomForm.jsx`:
- While analysis is loading, show animated step progress:
  "🔍 Interpreting symptoms..." → "📋 Summarizing case..." → "❓ Generating questions..." → "📚 Searching knowledge base..."
- Use timed UI states (simulated, since actual timing varies)

File to modify: `frontend/src/pages/SymptomForm.jsx`

---

### Phase 4 — Fix Backend Stability Issues
*Ensures the app runs without crashing regardless of external credentials.*

**4A. Make share routes work without Supabase**

Modify `routes/share.py`:
- Replace Supabase insert with SQLite-based shared reports table
- Add `shared_reports` table to `models.py` with `token`, `report_json`, `form_json`, `created_at`
- `share.py` uses `database.py` instead of `supabase_client.py`

Files to modify: `backend/app/routes/share.py`, `backend/app/db/models.py`, `backend/app/db/database.py`

**4B. Make save-report work without Supabase**

Modify `routes/save_report.py`:
- Remove the conditional Supabase call `if payload.user_id: save_assessment(...)`
- SQLite save is sufficient — remove Supabase dependency from this route

File to modify: `backend/app/routes/save_report.py`

**4C. Remove optional Supabase crash path**

Modify `core/supabase_client.py`:
- Change `RuntimeError` to a logged warning and return `None`
- All callers should handle `None` gracefully

File to modify: `backend/app/core/supabase_client.py`

---

### Phase 5 — Hackathon Presentation Materials
*Required for Microsoft Agents League submission.*

**5A. Architecture Diagram**

Create `ARCHITECTURE.md`:
- Mermaid diagram showing the full agent pipeline
- Shows: User → Frontend → API → Orchestrator → [Agent1 → Agent2 → Agent3 → RAG] → Response
- Shows: Final Assessment pipeline with Agent4, Agent5, RAG
- Shows: Data flow between agents (what each agent receives and passes forward)

File to create: `agentic-health-monitor/ARCHITECTURE.md`

**5B. Update README.md**

Modify `README.md`:
- Add "Hackathon Category: Reasoning Agents" badge
- Add agent architecture table with inputs/outputs
- Add demo GIF placeholder section
- Add "Why this is a Reasoning Agent" section explaining multi-step LLM reasoning
- Add quick-start section (single command if possible)

File to modify: `agentic-health-monitor/README.md`

**5C. Add `.env.example` completeness**

Modify `backend/.env.example`:
- Document all required and optional variables with descriptions
- Mark which are required vs optional

File to modify: `backend/.env.example`

---

## 3. FILE MODIFICATION SUMMARY

| File | Action | Phase |
|---|---|---|
| `backend/app/schemas/output_schema.py` | Add `AgentTrace`, `interpretation` to responses | 1A |
| `backend/app/agents/orchestrator.py` | Add timing, trace building, emergency fast-path | 1B, 1C |
| `medical_docs/stroke_guidelines.txt` | New file | 2A |
| `medical_docs/liver_hepatic_guidelines.txt` | New file | 2A |
| `medical_docs/neurological_guidelines.txt` | New file | 2A |
| `medical_docs/sepsis_guidelines.txt` | New file | 2A |
| `medical_docs/respiratory_guidelines.txt` | New file | 2A |
| `medical_docs/endocrine_guidelines.txt` | New file | 2A |
| `medical_docs/musculoskeletal_guidelines.txt` | New file | 2A |
| `backend/app/main.py` | Trigger RAG reindex on startup | 2B |
| `frontend/src/pages/FollowUp.jsx` | Agent steps panel, emergency banner, body system badge | 3A, 3B, 3C |
| `frontend/src/pages/Report.jsx` | Agent trace panel, emergency banner | 3B, 3D |
| `frontend/src/pages/SymptomForm.jsx` | Live agent progress animation | 3E |
| `frontend/src/i18n/locales/en.json` | Add translation keys for new UI | 3A–3E |
| `backend/app/db/models.py` | Add `SharedReport` SQLite model | 4A |
| `backend/app/db/database.py` | Add shared report CRUD functions | 4A |
| `backend/app/routes/share.py` | Replace Supabase with SQLite | 4A |
| `backend/app/routes/save_report.py` | Remove Supabase dependency | 4B |
| `backend/app/core/supabase_client.py` | Graceful None return instead of crash | 4C |
| `agentic-health-monitor/ARCHITECTURE.md` | New file — Mermaid diagram | 5A |
| `agentic-health-monitor/README.md` | Hackathon upgrade | 5B |
| `backend/.env.example` | Add all variable docs | 5C |

**Files NOT to modify:**
- `symptom_agent.py` — working correctly, good prompts
- `clarification_agent.py` — working correctly with retry logic
- `risk_agent.py` — working correctly
- `recommendation_agent.py` — working correctly
- `llm.py` — working correctly with retry
- `config.py` — working correctly
- `rag/embedder.py`, `rag/loader.py`, `rag/vector_store.py` — working correctly
- `tools/rag_tool.py` — working correctly
- `schemas/input_schema.py` — no changes needed
- `db/models.py` — only additive change (new table)
- All frontend pages except FollowUp, Report, SymptomForm

---

## 4. EXECUTION ORDER

Execute phases in this order to avoid breaking existing functionality:

```
Phase 4 first  → Fix crashes before adding features
Phase 2 next   → Expand knowledge base (no code risk, just new files)
Phase 1 next   → Add trace to schema + orchestrator
Phase 3 next   → Frontend changes depend on Phase 1 API changes
Phase 5 last   → Documentation after everything works
```

---

## 5. WHAT STAYS EXACTLY THE SAME

The following will NOT be changed under any circumstances:

- All 5 agent LLM prompts — they are working and well-tuned
- The agent pipeline sequence — interpret → summarize → clarify → rag → risk → recommend
- The clarification agent's 3-retry logic and body-system fallback
- The ChromaDB vector store implementation
- The SQLite database schema (only additive)
- The frontend auth flow (local localStorage-based, working)
- The i18n system structure
- The recharts Dashboard visualization
- The PDF generation service
- The React Router setup
- All Pydantic schemas (only additive changes)

---

## 6. WHAT THIS ACHIEVES FOR THE HACKATHON

After all phases are complete, the project will demonstrate:

| Hackathon Criterion | How It Is Met |
|---|---|
| Multi-agent architecture | 5 LLM agents with distinct roles + orchestrator |
| Agent reasoning transparency | `AgentTrace` in API + visual trace panel in UI |
| Reasoning chain | Interpreter → Summarizer → Clarifier → Risk → Recommendation |
| Real-world use case | Clinical triage and health monitoring |
| RAG integration | 11 medical documents, ChromaDB, grounded LLM responses |
| Emergency detection | Fast-path detection with UI banner |
| Structured outputs | All agents return validated Pydantic models |
| Retry and fallback | Every agent has retry logic and graceful fallback |
| Production quality | Auth, history, PDF export, share links, i18n |
| Demo-ready UI | Live progress, agent steps panel, body system visualization |
