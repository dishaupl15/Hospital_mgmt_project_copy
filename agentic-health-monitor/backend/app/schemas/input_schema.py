"""
app/schemas/input_schema.py
Request body models for FastAPI routes.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.output_schema import ConditionItem, SymptomInterpretationResult


class SymptomFormInput(BaseModel):
    name: str = Field(description="Patient full name.")
    age: int = Field(gt=0, description="Patient age in years.")
    gender: str = Field(description="Patient gender.")
    symptoms: str = Field(description="Free-text symptom description.")
    duration: str = Field(description="How long symptoms have been present.")
    severity: str = Field(description="Self-reported severity: mild, moderate, or severe.")
    history: Optional[str] = Field(default=None, description="Relevant medical history.")
    bp: Optional[str] = Field(default=None, description="Blood pressure reading.")
    sugar: Optional[str] = Field(default=None, description="Blood sugar reading.")
    temperature: Optional[str] = Field(default=None, description="Body temperature.")


class FinalAssessmentRequest(BaseModel):
    original_data: SymptomFormInput
    follow_up_answers: Dict[str, str] = Field(
        description="Map of question text to patient answer."
    )
    symptom_summary: Optional[str] = Field(
        default=None,
        description="Clinical summary from the Symptom Agent, passed through from /analyze-symptoms.",
    )
    interpretation: Optional[SymptomInterpretationResult] = Field(
        default=None,
        description="Structured interpretation from symptom analysis, used to improve diagnosis and grounding.",
    )


class ReportCreate(SymptomFormInput):
    follow_up_answers: Dict[str, str]
    possible_conditions: List[ConditionItem]
    confidence: str
    risk_level: str
    urgency: str
    explanation: str
    recommendation: str
    user_id: Optional[str] = None


class RagQueryRequest(BaseModel):
    query: str = Field(description="Text to search against the medical knowledge base.")
    top_k: int = Field(default=3, ge=1, le=10)
