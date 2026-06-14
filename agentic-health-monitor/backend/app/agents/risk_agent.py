"""
app/agents/risk_agent.py
Risk Assessment Agent - reasons over symptoms + follow-up answers + RAG context.
"""
import logging
from typing import Dict, List, Literal, Tuple
from pydantic import BaseModel, Field, field_validator
from app.core.llm import chat_structured
from app.tools.rag_tool import retrieve_as_context
from app.schemas.output_schema import ConditionItem

logger = logging.getLogger(__name__)


class PossibleCondition(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str


class RiskAssessmentOutput(BaseModel):
    possible_conditions: List[PossibleCondition]
    confidence: Literal["Low", "Moderate", "High"]
    risk_level: Literal["Low", "Medium", "High", "Emergency"]
    urgency: Literal["Routine monitoring", "Within 3 days", "Within 24 hours", "Immediate"]
    explanation: str

    @field_validator("possible_conditions")
    @classmethod
    def sort_and_limit(cls, v):
        return sorted(v, key=lambda c: c.score, reverse=True)[:3]


_SYSTEM = """\
You are a clinical risk assessment AI. Reason over the full patient case.

Rules:
- Never state a definitive diagnosis. Use: may suggest, consistent with, could indicate.
- Acknowledge overlapping symptoms and uncertainty in the explanation.
- When information is incomplete, balance caution with the likelihood of mild illness. Do not over-triage every case.
- Use retrieved medical context to ground your reasoning.
- Prioritize accurate risk level assignment over always choosing the highest severity.

Risk levels: Emergency=life-threatening, High=24h, Medium=3 days, Low=home care.

You MUST respond with ONLY this exact JSON structure, no extra text:
{
  "possible_conditions": [
    {"name": "<condition name>", "score": <0.0-1.0>, "reasoning": "<why this condition fits>"},
    {"name": "<condition name>", "score": <0.0-1.0>, "reasoning": "<why this condition fits>"}
  ],
  "confidence": "<Low|Moderate|High>",
  "risk_level": "<Low|Medium|High|Emergency>",
  "urgency": "<Routine monitoring|Within 3 days|Within 24 hours|Immediate>",
  "explanation": "<2-3 sentence clinical explanation>"
}"""


_EMERGENCY_TERMS = [
    "chest pain",
    "shortness of breath",
    "difficulty breathing",
    "sudden weakness",
    "numbness",
    "slurred speech",
    "severe abdominal pain",
    "heavy bleeding",
    "possible stroke",
    "possible heart attack",
    "loss of consciousness",
    "sepsis",
    "anaphylaxis",
]

_HIGH_RISK_TERMS = [
    "severe",
    "worst ever",
    "sudden onset",
    "uncontrolled",
    "fainting",
    "blood in",
    "bleeding",
    "vomit",
    "dehydration",
    "rapid heart",
    "palpitations",
]

_MEDIUM_RISK_TERMS = [
    "moderate",
    "persistent",
    "worsening",
    "fever",
    "nausea",
    "dizziness",
    "weakness",
]

_LOW_RISK_TERMS = [
    "mild",
    "occasional",
    "minor",
    "improving",
    "better",
    "stable",
]


def _normalize_text(*parts: str) -> str:
    return " ".join(part.strip().lower() for part in parts if part).strip()


def _contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _infer_risk_from_case(
    symptoms: str,
    duration: str,
    severity: str,
    answers: str,
    summary: str,
) -> tuple[str, str, str]:
    content = _normalize_text(symptoms, duration, severity, answers, summary)
    severity_key = severity.strip().lower()

    if _contains_any(content, _EMERGENCY_TERMS):
        return "Emergency", "Immediate", "High"

    if severity_key in ["critical", "severe", "high"] or _contains_any(content, _HIGH_RISK_TERMS):
        return "High", "Within 24 hours", "Moderate"

    if severity_key in ["moderate", "medium"] or _contains_any(content, _MEDIUM_RISK_TERMS):
        return "Medium", "Within 3 days", "Moderate"

    if severity_key in ["low", "mild"] or _contains_any(content, _LOW_RISK_TERMS):
        return "Low", "Routine monitoring", "Low"

    return "Medium", "Within 3 days", "Moderate"


def _infer_condition_from_symptoms(symptoms: str, summary: str) -> str:
    content = _normalize_text(symptoms, summary)
    if _contains_any(content, ["chest pain", "pressure", "tightness", "shortness of breath", "palpitations"]):
        return "Possible cardiac or respiratory condition"
    if _contains_any(content, ["nausea", "vomiting", "diarrhea", "abdominal pain", "stomach pain", "indigestion"]):
        return "Possible gastrointestinal condition"
    if _contains_any(content, ["headache", "dizziness", "confusion", "weakness", "numbness"]):
        return "Possible neurological condition"
    if _contains_any(content, ["fever", "cough", "chills", "sore throat", "shortness of breath"]):
        return "Possible infection or respiratory condition"
    if _contains_any(content, ["joint", "muscle", "back pain", "sprain", "strain"]):
        return "Possible musculoskeletal condition"
    return "Unspecified condition"


def assess_risk(
    symptoms: str,
    duration: str,
    severity: str,
    follow_up_answers: Dict[str, str],
    summary: str = "",
) -> Tuple[List[ConditionItem], str, str, str, str]:
    rag_context = retrieve_as_context(symptoms, top_k=3)

    answers_text = "\n".join(
        "  Q: " + q + "\n  A: " + a for q, a in follow_up_answers.items()
    ) or "None provided."

    user_message = (
        "Symptoms: " + symptoms + "\n"
        "Duration: " + duration + " | Severity: " + severity + "\n\n"
        "Follow-up Answers:\n" + answers_text + "\n\n"
        "Clinical Summary:\n" + (summary or "Not available.") + "\n\n"
        "Relevant Medical Context:\n" + rag_context + "\n\n"
        "Assess the full case and return the risk JSON."
    )
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user_message},
    ]

    try:
        result: RiskAssessmentOutput = chat_structured(
            messages=messages,
            output_model=RiskAssessmentOutput,
            temperature=0.2,
        )
        conditions = [ConditionItem(name=c.name, score=c.score) for c in result.possible_conditions]
        logger.info("[RiskAgent] risk=%s | confidence=%s | urgency=%s", result.risk_level, result.confidence, result.urgency)
        print("[RISK AGENT] risk=" + result.risk_level + " | confidence=" + result.confidence + " | urgency=" + result.urgency)
        print("  conditions : " + str([c.name for c in conditions]))
        return conditions, result.confidence, result.risk_level, result.urgency, result.explanation

    except Exception as exc:
        logger.warning("[RiskAgent] LLM failed (%s) - using safe fallback.", exc)
        print("[RISK AGENT] FAILED: " + str(exc) + " - fallback used")
        risk_level, urgency, confidence = _infer_risk_from_case(
            symptoms=symptoms,
            duration=duration,
            severity=severity,
            answers=answers_text,
            summary=summary,
        )
        condition_name = _infer_condition_from_symptoms(symptoms, summary)
        explanation = {
            "Emergency": (
                "The reported symptoms are potentially life-threatening and require immediate medical attention. "
                "Seek emergency care right away."
            ),
            "High": (
                "The case appears concerning and should be evaluated by a clinician within 24 hours. "
                "Please seek prompt medical attention."
            ),
            "Medium": (
                "The symptoms are not clearly life-threatening but warrant evaluation within a few days if they persist or worsen. "
                "Monitor the situation closely."
            ),
            "Low": (
                "The presentation appears to be mild and may be monitored at home unless symptoms worsen. "
                "Seek care if new concerning signs develop."
            ),
        }[risk_level]
        return (
            [ConditionItem(name=condition_name, score=0.6)],
            confidence,
            risk_level,
            urgency,
            explanation,
        )
