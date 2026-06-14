"""
app/agents/symptom_agent.py
Symptom Interpreter + Symptom Summarizer agents.
"""
import logging
from typing import List, Literal, Optional, Tuple
from pydantic import BaseModel, Field, field_validator
from app.core.llm import chat_structured
from app.tools.rag_tool import retrieve_as_context

logger = logging.getLogger(__name__)


# ── Symptom Interpreter ────────────────────────────────────────────────────────

class SymptomInterpretation(BaseModel):
    possible_conditions: List[str] = Field(description="2-5 possible medical conditions.")
    body_system: str = Field(description="Primary body system: cardiac, neurological, hepatic, respiratory, gastrointestinal, endocrine, musculoskeletal, general.")
    risk_level: str = Field(description="Risk level: low, moderate, high, emergency.")
    symptom_cluster: str = Field(description="One-sentence description of the symptom cluster pattern.")
    is_emergency: bool

    @field_validator("body_system", mode="before")
    def normalize_body_system(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("risk_level", mode="before")
    def normalize_risk_level(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value


_INTERPRETER_SYSTEM = """\
You are a medical triage AI. Analyze the patient's symptoms holistically.

Rules:
- Consider ALL symptoms together as a cluster, never individually.
- Identify the dominant body system: cardiac, neurological, hepatic, respiratory, gastrointestinal, endocrine, musculoskeletal, or general.
- Flag is_emergency=true for: stroke, MI, sepsis, meningitis, anaphylaxis, pulmonary embolism.
- risk_level: emergency=life-threatening, high=needs care within 24h, moderate=needs care within days, low=self-limiting.
- Be specific with body_system - never return "general" unless symptoms are truly non-specific.

You MUST respond with ONLY this exact JSON structure, no extra text:
{
  "possible_conditions": ["<condition1>", "<condition2>", "<condition3>"],
  "body_system": "<cardiac|neurological|hepatic|respiratory|gastrointestinal|endocrine|musculoskeletal|general>",
  "risk_level": "<low|moderate|high|emergency>",
  "symptom_cluster": "<one sentence describing the cluster>",
  "is_emergency": <true|false>
}"""


def interpret_symptoms(
    symptoms: str,
    age: Optional[int] = None,
    gender: Optional[str] = None,
) -> SymptomInterpretation:
    user_message = (
        "Patient: age=" + str(age or "unknown") + ", gender=" + str(gender or "unknown") + "\n"
        "Symptoms: " + symptoms + "\n\n"
        "Analyze the complete symptom picture and return the JSON."
    )
    messages = [
        {"role": "system", "content": _INTERPRETER_SYSTEM},
        {"role": "user", "content": user_message},
    ]
    try:
        result = chat_structured(messages=messages, output_model=SymptomInterpretation, temperature=0.1)
        logger.info("[SymptomInterpreter] body_system=%s | risk=%s | emergency=%s", result.body_system, result.risk_level, result.is_emergency)
        print("[SYMPTOM INTERPRETER] body_system=" + result.body_system + " | risk=" + result.risk_level + " | emergency=" + str(result.is_emergency))
        print("  conditions : " + str(result.possible_conditions))
        print("  cluster    : " + result.symptom_cluster)
        return result
    except Exception as exc:
        logger.warning("[SymptomInterpreter] LLM failed (%s) - using safe fallback.", exc)
        print("[SYMPTOM INTERPRETER] FAILED: " + str(exc) + " - fallback used")
        normalized = symptoms.lower()
        fallback_risk = "moderate"
        if any(term in normalized for term in ["mild", "occasional", "minor", "improving"]):
            fallback_risk = "low"
        return SymptomInterpretation(
            possible_conditions=["unspecified condition"],
            body_system="general",
            risk_level=fallback_risk,
            symptom_cluster=symptoms[:120],
            is_emergency=False,
        )


# ── Symptom Summarizer ─────────────────────────────────────────────────────────

class SymptomAnalysisOutput(BaseModel):
    summary: str = Field(description="Concise 2-3 sentence clinical-style summary.")
    concern_level: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
    follow_up_needed: bool
    rationale: str


_SUMMARIZER_SYSTEM = """\
You are a clinical triage assistant AI. Analyse the patient case and return a structured JSON assessment.

Concern levels:
- CRITICAL: potential life-threatening emergency (stroke, MI, sepsis, etc.)
- HIGH: concerning, needs prompt attention within 24 hours.
- MODERATE: warrants monitoring and a doctor visit within a few days.
- LOW: likely mild or self-limiting.

Rules:
- Do NOT diagnose. Summarise and assess concern only.
- Be medically cautious - when uncertain, lean toward higher concern.
- follow_up_needed MUST be true for MODERATE, HIGH, and CRITICAL concern levels.
- follow_up_needed may be false ONLY for LOW concern with very clear, simple symptoms.
- Use language like: may suggest, could indicate, warrants evaluation.

You MUST respond with ONLY this exact JSON structure, no extra text:
{
  "summary": "<2-3 sentence clinical summary>",
  "concern_level": "<LOW|MODERATE|HIGH|CRITICAL>",
  "follow_up_needed": <true|false>,
  "rationale": "<brief reasoning>"
}"""


def summarize_symptoms(
    symptoms: str,
    duration: str,
    severity: str,
    bp: Optional[str] = None,
    sugar: Optional[str] = None,
    temperature: Optional[str] = None,
    age: Optional[int] = None,
    gender: Optional[str] = None,
    history: Optional[str] = None,
) -> Tuple[str, bool, List[str]]:
    rag_context = retrieve_as_context(symptoms, top_k=2)
    vitals = ", ".join(filter(None, [
        "Temperature: " + temperature if temperature else None,
        "Blood Pressure: " + bp if bp else None,
        "Blood Sugar: " + sugar if sugar else None,
    ])) or "Not provided"

    user_message = (
        "Patient Details:\n"
        "- Age: " + str(age or "Not provided") + "\n"
        "- Gender: " + str(gender or "Not provided") + "\n"
        "- Medical History: " + str(history or "None reported") + "\n\n"
        "Reported Symptoms: " + symptoms + "\n"
        "Duration: " + duration + "\n"
        "Self-reported Severity: " + severity + "\n"
        "Vitals: " + vitals + "\n\n"
        "Relevant Medical Context:\n" + rag_context + "\n\n"
        "Analyse this case and return the required JSON."
    )
    messages = [
        {"role": "system", "content": _SUMMARIZER_SYSTEM},
        {"role": "user", "content": user_message},
    ]

    try:
        result: SymptomAnalysisOutput = chat_structured(
            messages=messages,
            output_model=SymptomAnalysisOutput,
            temperature=0.2,
        )
        # Force follow_up_needed=True for anything above LOW
        follow_up = result.follow_up_needed or result.concern_level != "LOW"
        logger.info("[SymptomSummarizer] concern=%s | follow_up_needed=%s", result.concern_level, follow_up)
        print("[SYMPTOM SUMMARIZER] concern=" + result.concern_level + " | follow_up_needed=" + str(follow_up))
        print("  summary  : " + result.summary)
        print("  rationale: " + result.rationale)
        return result.summary, follow_up, []
    except Exception as exc:
        logger.warning("[SymptomSummarizer] LLM failed (%s) - using fallback.", exc)
        print("[SYMPTOM SUMMARIZER] FAILED: " + str(exc) + " - fallback used")
        follow_up = _should_generate_follow_up(symptoms, severity, temperature)
        return _generic_summary(symptoms, duration, severity, temperature), follow_up, []


def _generic_summary(symptoms: str, duration: str, severity: str, temperature: Optional[str]) -> str:
    temp_note = " with a recorded temperature of " + temperature if temperature else ""
    severity_label = severity.lower()
    if severity_label in ["low", "mild"]:
        return (
            "Patient reports " + symptoms + temp_note + ", lasting " + duration + " with mild severity. "
            "This presentation appears likely to be self-limiting, but monitor symptoms and seek care if they worsen."
        )
    if severity_label in ["moderate", "medium"]:
        return (
            "Patient reports " + symptoms + temp_note + ", lasting " + duration + " with moderate severity. "
            "This presentation may require medical evaluation if symptoms persist or worsen."
        )
    return (
        "Patient reports " + symptoms + temp_note + ", lasting " + duration + " with severe symptoms. "
        "This presentation may require prompt medical evaluation."
    )


def _contains_any(text: str, keywords: List[str]) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in keywords)


def _should_generate_follow_up(symptoms: str, severity: str, temperature: Optional[str]) -> bool:
    severity_label = severity.lower()
    if severity_label in ["low", "mild"]:
        combined = " ".join(filter(None, [symptoms, temperature or ""]))
        if _contains_any(combined, ["severe", "sudden", "blood", "difficulty breathing", "chest pain", "vomit"]):
            return True
        return False
    return True
