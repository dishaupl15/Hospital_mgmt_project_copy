# Agentic Health Monitor

An AI-powered health assessment system built with FastAPI, React, and Groq LLM.

## Overview

Agentic Health Monitor is an AI-powered multi-agent clinical triage system that transforms user-reported symptoms into structured, explainable healthcare insights.

The system uses specialized AI agents to analyze symptoms, ask intelligent follow-up questions, assess risk levels, retrieve medical knowledge, and generate personalized recommendations.

Built for the Microsoft Agents League Hackathon under the **Reasoning Agents** category, the project demonstrates multi-agent orchestration, AI reasoning, Retrieval-Augmented Generation (RAG), and grounded healthcare intelligence.

> Note: This system is designed for healthcare decision support and early triage assistance. It does not replace professional medical diagnosis.

---

# Problem Statement

Healthcare users often struggle to understand symptoms and determine the urgency of seeking medical help.

Traditional symptom checkers:
- Provide generic responses
- Lack contextual reasoning
- Do not ask personalized follow-up questions
- May generate unreliable medical information

There is a need for an intelligent system that can reason through symptoms, gather missing context, assess risk, and provide explainable guidance.
---

# Solution

Agentic Health Monitor solves this problem using a multi-agent AI architecture.

The system divides healthcare reasoning into specialized agents:

1. Symptom Analysis Agent
   - Understands user symptoms
   - Extracts important medical information
   - Identifies affected body systems

2. Clarification Agent
   - Generates symptom-specific follow-up questions
   - Collects missing information

3. Medical Reasoning Agent
   - Performs multi-step reasoning
   - Maps symptoms with medical knowledge

4. Risk Assessment Agent
   - Evaluates severity
   - Generates risk levels:
     - Low
     - Medium
     - High

5. Recommendation Agent
   - Produces structured next-step guidance
   - Provides safety recommendations

---
# Features

## AI Multi-Agent Reasoning
- Specialized agents collaborate to analyze healthcare scenarios
- Each agent focuses on a specific reasoning task

## Intelligent Follow-up Questions
- Generates dynamic questions based on symptoms
- Supports symptom categories such as:
  - Cardiac
  - Neurological
  - Hepatic
  - Respiratory
  - General health

## Risk Assessment
- Evaluates symptom severity
- Provides explainable risk classification

## RAG-Based Medical Knowledge Retrieval
- Retrieves relevant healthcare information
- Improves response accuracy
- Reduces hallucination

## Patient Report Management
- Stores generated reports
- Allows previous assessment history tracking

---
# System Architecture
<img width="907" height="608" alt="image" src="https://github.com/user-attachments/assets/7144eecf-f6d6-4c40-ab76-298d1c949f51" />

Main components:

- Frontend Layer
  - React + Vite
  - User interaction interface

- Backend Layer
  - FastAPI APIs
  - Request processing
  - Agent orchestration

- AI Layer
  - Symptom Agent
  - Clarification Agent
  - Risk Agent
  - Recommendation Agent

- Knowledge Layer
  - Medical knowledge base
  - Vector search
  - Context retrieval

---

# Multi-Agent Workflow

User enters symptoms:

Example:
"I have fever, headache and body pain for 2 days."

Flow:

1. Symptom Agent extracts:
   - Symptoms
   - Duration
   - Severity
   - Context

2. Clarification Agent asks:
   - Additional relevant questions

3. Reasoning Agent:
   - Analyzes possible conditions

4. Risk Agent:
   - Calculates severity level

5. Recommendation Agent:
   - Generates final structured report


Output:

- Symptom summary
- Possible conditions
- Risk level
- Recommended next steps

---

# Microsoft Foundry IQ Integration

Microsoft Foundry IQ acts as the knowledge grounding layer of Agentic Health Monitor.

It enables AI agents to retrieve relevant healthcare information from curated knowledge sources before generating responses.

Foundry IQ helps the system:

- Retrieve trusted medical knowledge
- Provide context-aware responses
- Reduce AI hallucinations
- Improve explainability
- Support grounded reasoning

The agent workflow uses retrieved knowledge to generate more reliable healthcare insights.

Knowledge Flow:

Medical Knowledge Base
        ↓
Foundry IQ Retrieval
        ↓
AI Agents
        ↓
Explainable Clinical Report


---

# Responsible AI & Safety

This project follows responsible AI principles for healthcare applications.

Key considerations:

- Provides healthcare decision support, not medical diagnosis
- Encourages consultation with qualified healthcare professionals
- Uses synthetic/demo healthcare data only
- Avoids storing sensitive patient information
- Uses knowledge grounding to reduce incorrect outputs
- Provides transparent AI-generated reasoning
- Keeps humans in the loop for final decisions

---

# Tech Stack

## Backend

- FastAPI
- Python
- Groq LLM (llama-3.3-70b-versatile)
- Pydantic
- SQLite

## AI / Knowledge

- Multi-Agent Architecture
- Retrieval-Augmented Generation (RAG)
- ChromaDB Vector Database
- Microsoft Foundry IQ

## Frontend

- React
- Vite
- Tailwind CSS

---


## Project Structure

```
agentic-health-monitor/
├── backend/
│   ├── app/
│   │   ├── agents/        # LLM agents (symptom, clarification, risk, recommendation)
│   │   ├── core/          # LLM client, config
│   │   ├── routes/        # FastAPI routes
│   │   ├── schemas/       # Pydantic models
│   │   ├── rag/           # Embedder and vector store
│   │   └── tools/         # RAG tool
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── pages/         # SymptomForm, FollowUp, Report, History
    │   ├── components/
    │   └── services/      # API calls
    └── package.json
```

## Setup

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # Add your GROQ_API_KEY
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free Groq API key at: https://console.groq.com

## Usage

1. Open http://localhost:5173
2. Enter patient name, age, symptoms, duration, severity
3. AI analyzes symptoms and generates targeted follow-up questions
4. Answer questions to get full risk assessment and recommendations
5. View and save reports in history

## Agents

| Agent | Role |
|-------|------|
| SymptomInterpreter | Identifies body system and risk level |
| SymptomSummarizer | Generates clinical summary |
| ClarificationAgent | Generates symptom-specific follow-up questions |
| RiskAgent | Assesses risk and possible conditions |
| RecommendationAgent | Provides actionable recommendations |
