"""
app/schemas/output_schema.py
Response models for FastAPI routes.
ConditionItem lives here as the single source of truth — imported by input_schema and agents.
"""
from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class AgentTrace(BaseModel):
    """Records the execution of a single agent in the pipeline."""
    agent_name: str
    status: Literal["started", "completed", "failed", "skipped"]
    action: str = Field(description="What the agent was asked to do.")
    summary: str = Field(description="What the agent produced or why it failed.")
    duration_ms: float = Field(default=0.0, description="Execution time in milliseconds.")
    timestamp: str = Field(description="ISO-format UTC timestamp when agent finished.")
    used_fallback: bool = Field(default=False, description="True if LLM failed and fallback was used.")


class SymptomInterpretationResult(BaseModel):
    """Structured output from the Symptom Interpreter Agent — surfaced in API responses."""
    possible_conditions: List[str]
    body_system: str
    risk_level: str
    symptom_cluster: str
    is_emergency: bool


# ── Phase 3 additions ─────────────────────────────────────────────────────────

class KnowledgeSourceItem(BaseModel):
    """Citation-ready knowledge source reference surfaced in API responses."""
    source: str
    topic: str
    category: Optional[str] = None
    condition: Optional[str] = None


# ── Phase 2 additions ─────────────────────────────────────────────────────────

class DiagnosedConditionResult(BaseModel):
    """One condition entry in the DiagnosisResult — surfaced in API responses."""
    name: str
    confidence: str = Field(description="high, moderate, or low")
    reason: str
    supporting_symptoms: List[str] = Field(default_factory=list)


class DiagnosisResult(BaseModel):
    """Structured output from the DiagnosisReasoningAgent — included in FinalAssessmentResponse."""
    possible_conditions: List[DiagnosedConditionResult] = Field(default_factory=list)
    reasoning_summary: str = ""
    risk_factors: List[str] = Field(default_factory=list)
    sources: List[str] = Field(
        default_factory=list,
        description="Knowledge sources retrieved by MedicalKnowledgeAgent.",
    )
    retrieved_topics: List[str] = Field(default_factory=list)


class ConditionItem(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=1.0)


class RagChunk(BaseModel):
    id: str
    source: str
    text: str
    score: float = Field(ge=0.0, le=1.0)


class AnalyzeResponse(BaseModel):
    # ── existing fields (unchanged) ───────────────────────────────────────────
    symptom_summary: str
    follow_up_needed: bool
    follow_up_questions: List[str]
    relevant_knowledge: List[RagChunk] = Field(default_factory=list)
    # ── Phase 1 additions ─────────────────────────────────────────────────────
    interpretation: Optional[SymptomInterpretationResult] = Field(
        default=None,
        description="Structured output from Symptom Interpreter Agent.",
    )
    emergency_alert: bool = Field(
        default=False,
        description="True when Symptom Interpreter detects a life-threatening emergency.",
    )
    agent_trace: List[AgentTrace] = Field(
        default_factory=list,
        description="Execution trace of every agent in this pipeline.",
    )
    # ── Phase 3 additions ─────────────────────────────────────────────────────
    knowledge_sources: List[KnowledgeSourceItem] = Field(
        default_factory=list,
        description="Citation-ready knowledge sources used in this analysis.",
    )


class FinalAssessmentResponse(BaseModel):
    # ── existing fields (unchanged) ───────────────────────────────────────────
    possible_conditions: List[ConditionItem]
    confidence: str
    risk_level: str
    urgency: str
    explanation: str
    recommendation: str
    next_steps: List[str] = Field(default_factory=list)
    disclaimer: str = ""
    follow_up_answers: Optional[Dict[str, str]] = None
    # ── Phase 1 additions ─────────────────────────────────────────────────────
    agent_trace: List[AgentTrace] = Field(
        default_factory=list,
        description="Execution trace of every agent in this pipeline.",
    )
    # ── Phase 2 additions ─────────────────────────────────────────────────────
    diagnosis_result: Optional[DiagnosisResult] = Field(
        default=None,
        description="Structured output from DiagnosisReasoningAgent.",
    )
    # ── Phase 3 additions ─────────────────────────────────────────────────────
    knowledge_sources: List[KnowledgeSourceItem] = Field(
        default_factory=list,
        description="Citation-ready knowledge sources used in this assessment.",
    )


class SaveReportResponse(BaseModel):
    success: bool
    message: str


class ReportItem(BaseModel):
    id: int
    name: str
    age: int
    gender: str
    symptoms: str
    duration: str
    severity: str
    history: Optional[str] = None
    bp: Optional[str] = None
    sugar: Optional[str] = None
    temperature: Optional[str] = None
    follow_up_answers: Dict[str, str]
    possible_conditions: List[ConditionItem]
    confidence: str
    risk_level: str
    urgency: str
    explanation: str
    recommendation: str
    created_at: datetime


class HistoryResponse(BaseModel):
    reports: List[ReportItem]


class RagResponse(BaseModel):
    chunks: List[RagChunk]
