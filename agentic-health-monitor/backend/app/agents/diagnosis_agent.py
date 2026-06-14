"""
app/agents/diagnosis_agent.py
DiagnosisReasoningAgent — reasons over the full patient picture to produce
a structured differential diagnosis with confidence and supporting evidence.

Follows the same coding style as risk_agent.py and recommendation_agent.py.
Never claims a definitive diagnosis — always uses "possible condition" language.
"""
import logging
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator
from app.core.llm import chat_structured

logger = logging.getLogger(__name__)


# ── Output models ──────────────────────────────────────────────────────────────

class DiagnosedCondition(BaseModel):
    name: str = Field(description="Name of the possible condition.")
    confidence: Literal["low", "moderate", "high"]
    reason: str = Field(description="Short user-friendly explanation of why this condition is possible.")
    supporting_symptoms: List[str] = Field(
        description="Symptoms from the patient's report that support this condition.",
        default_factory=list,
    )

    @field_validator("supporting_symptoms")
    @classmethod
    def limit_symptoms(cls, v: List[str]) -> List[str]:
        return v[:5]


class DiagnosisOutput(BaseModel):
    possible_conditions: List[DiagnosedCondition]
    reasoning_summary: str = Field(
        description="2-3 sentence plain-language summary of the overall diagnostic reasoning."
    )
    risk_factors: List[str] = Field(
        description="Patient-specific risk factors identified from the case.",
        default_factory=list,
    )

    @field_validator("possible_conditions")
    @classmethod
    def sort_and_limit(cls, v: List[DiagnosedCondition]) -> List[DiagnosedCondition]:
        order = {"high": 0, "moderate": 1, "low": 2}
        return sorted(v, key=lambda c: order.get(c.confidence, 3))[:4]

    @field_validator("risk_factors")
    @classmethod
    def limit_risk_factors(cls, v: List[str]) -> List[str]:
        return v[:5]


# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM = """\
You are a clinical diagnostic reasoning AI. Your role is to analyze the full patient case
and produce a structured differential diagnosis.

Rules:
- NEVER say "the patient has [disease]". Always say "possible condition", "may suggest", "consistent with".
- Base reasoning on ALL available evidence: symptoms, body system, follow-up answers, medical context.
- Assign confidence (high/moderate/low) based on how well the symptoms match each condition.
- List only the supporting symptoms that are actually present in this patient's report.
- Keep reason short and patient-friendly (1-2 sentences max per condition).
- Identify real risk factors specific to this patient (age, history, vitals, symptom severity).
- reasoning_summary must synthesize the full picture in plain language.

You MUST respond with ONLY this exact JSON structure, no extra text:
{
  "possible_conditions": [
    {
      "name": "<condition name>",
      "confidence": "<high|moderate|low>",
      "reason": "<1-2 sentence user-friendly explanation>",
      "supporting_symptoms": ["<symptom1>", "<symptom2>"]
    }
  ],
  "reasoning_summary": "<2-3 sentence plain-language summary>",
  "risk_factors": ["<risk factor 1>", "<risk factor 2>"]
}"""


# ── Agent function ─────────────────────────────────────────────────────────────

def run_diagnosis(
    symptoms: str,
    body_system: str,
    possible_conditions_from_interpreter: List[str],
    follow_up_answers: Dict[str, str],
    medical_context: str,
    age: Optional[int] = None,
    gender: Optional[str] = None,
    history: Optional[str] = None,
    severity: Optional[str] = None,
) -> DiagnosisOutput:
    """
    DiagnosisReasoningAgent — combines interpreter output, follow-up answers,
    and retrieved medical knowledge to produce a structured differential diagnosis.

    Returns DiagnosisOutput on success, or a safe fallback on LLM failure.
    Never raises — always returns a usable result.
    """
    answers_text = "\n".join(
        "  Q: " + q + "\n  A: " + a for q, a in follow_up_answers.items()
    ) or "No follow-up answers provided."

    conditions_hint = ", ".join(possible_conditions_from_interpreter) if possible_conditions_from_interpreter else "Unknown"

    user_message = (
        "Patient Information:\n"
        "- Age: " + str(age or "Not provided") + "\n"
        "- Gender: " + str(gender or "Not provided") + "\n"
        "- Severity: " + str(severity or "Not provided") + "\n"
        "- Medical History: " + str(history or "None reported") + "\n\n"
        "Reported Symptoms: " + symptoms + "\n"
        "Body System Identified: " + body_system + "\n"
        "Initial Possible Conditions (from interpreter): " + conditions_hint + "\n\n"
        "Follow-up Answers:\n" + answers_text + "\n\n"
        "Relevant Medical Knowledge:\n" + (medical_context or "No medical context available.") + "\n\n"
        "Analyze the full case and return the diagnostic reasoning JSON."
    )

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user_message},
    ]

    try:
        result: DiagnosisOutput = chat_structured(
            messages=messages,
            output_model=DiagnosisOutput,
            temperature=0.2,
        )
        logger.info(
            "[DiagnosisAgent] conditions=%s | risk_factors=%d",
            [c.name for c in result.possible_conditions],
            len(result.risk_factors),
        )
        print("[DIAGNOSIS AGENT] OK — " + str(len(result.possible_conditions)) + " conditions")
        for c in result.possible_conditions:
            print("  " + c.confidence.upper() + " | " + c.name + " — " + c.reason[:80])
        return result

    except Exception as exc:
        logger.warning("[DiagnosisAgent] LLM failed (%s) — using safe fallback.", exc)
        print("[DIAGNOSIS AGENT] FAILED: " + str(exc) + " — fallback used")
        return _fallback(symptoms, possible_conditions_from_interpreter, body_system)


def _infer_conditions(symptoms: str, body_system: str, conditions: List[str]) -> List[str]:
    normalized = symptoms.lower()
    if conditions:
        return conditions[:3]
    if body_system == "gastrointestinal" or any(k in normalized for k in ["nausea", "vomit", "diarrhea", "abdominal pain", "stomach pain"]):
        return ["Possible gastrointestinal upset", "Possible food-related illness"]
    if body_system == "cardiac" or any(k in normalized for k in ["chest pain", "pressure", "palpitations", "shortness of breath"]):
        return ["Possible cardiac-related condition", "Possible respiratory strain"]
    if body_system == "neurological" or any(k in normalized for k in ["headache", "dizziness", "confusion", "numbness", "weakness"]):
        return ["Possible neurological condition", "Possible migraine or tension headache"]
    if body_system == "respiratory" or any(k in normalized for k in ["cough", "wheeze", "shortness of breath", "sore throat"]):
        return ["Possible respiratory infection", "Possible upper airway irritation"]
    if body_system == "musculoskeletal" or any(k in normalized for k in ["joint", "muscle", "back pain", "sprain", "strain"]):
        return ["Possible musculoskeletal strain", "Possible mild inflammation"]
    if body_system == "endocrine" or any(k in normalized for k in ["fatigue", "thirst", "urination", "weight"]):
        return ["Possible metabolic or endocrine imbalance"]
    return ["Unspecified condition"]


def _fallback(
    symptoms: str,
    conditions: List[str],
    body_system: str,
) -> DiagnosisOutput:
    """Safe fallback — builds a minimal DiagnosisOutput without any LLM call."""
    inferred = _infer_conditions(symptoms, body_system, conditions)
    fallback_conditions = [
        DiagnosedCondition(
            name=name,
            confidence="low",
            reason=(
                "This condition is suggested based on the symptom pattern and body system, "
                "but a healthcare provider is needed to confirm it."
            ),
            supporting_symptoms=[symptoms[:60]] if symptoms else [],
        )
        for name in inferred[:3]
    ]
    return DiagnosisOutput(
        possible_conditions=fallback_conditions,
        reasoning_summary=(
            "Automated diagnostic reasoning could not be completed at this time. "
            "Based on the reported symptoms, these are possible areas to explore: "
            + ", ".join(inferred[:2])
            + ". Please consult a qualified healthcare provider for a proper evaluation."
        ),
        risk_factors=[
            "Symptom severity and duration were used to estimate risk, but clinical evaluation is needed."
        ],
    )
