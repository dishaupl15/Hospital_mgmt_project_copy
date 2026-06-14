"""
app/agents/clarification_agent.py
Clarification Agent - generates symptom-specific follow-up questions via LLM.
Uses a simple JSON array output to eliminate all parsing failures.
"""
import json
import logging
from typing import List, Optional
from app.core.llm import chat_completion
from app.agents.symptom_agent import SymptomInterpretation

print("[IMPORT] clarification_agent.py loaded successfully")
logger = logging.getLogger(__name__)


_SYSTEM = """\
You are a clinical triage AI. Your ONLY job is to generate targeted follow-up questions.

You will receive:
- Patient symptoms
- Body system identified (cardiac, neurological, hepatic, respiratory, gastrointestinal, endocrine, etc.)
- Possible conditions
- Risk level

OUTPUT RULES:
1. Return ONLY a raw JSON array of strings. No object wrapper. No "questions" key. Just the array.
2. Generate exactly 5 questions.
3. Every question MUST be specific to the body_system and possible_conditions provided.
4. NEVER generate generic questions like "when did symptoms start" or "are symptoms worsening".
5. Questions must be clinically relevant to the identified system.

Body system question guidance:
- cardiac: pain radiation to arm/jaw, shortness of breath, sweating, pressure/tightness, prior heart disease
- neurological: FAST signs (face droop, arm weakness, speech), sudden onset, vision changes, severe headache
- hepatic: jaundice onset, urine color, stool color, right-side pain, alcohol use, hepatitis exposure
- respiratory: breathing at rest, cough character/color, wheezing, fever, prior lung conditions
- gastrointestinal: pain location, blood in stool/vomit, bowel changes, pain after eating, fever, travel
- endocrine: blood sugar readings, thirst/urination, weight changes, fatigue, diabetes/thyroid history
- musculoskeletal: injury/trauma, joint swelling, movement limitation, pain at rest vs movement

EXAMPLE OUTPUT FORMAT (cardiac case):
[
  "Does the chest pain spread to your left arm, jaw, neck, or back?",
  "Are you experiencing shortness of breath along with the chest pain?",
  "Are you sweating, feeling nauseous, or lightheaded right now?",
  "Do you feel pressure or squeezing in your chest rather than sharp pain?",
  "Have you ever been diagnosed with heart disease or had a heart attack before?"
]

Return ONLY the JSON array. No other text."""


def generate_follow_up_questions(
    symptoms: str,
    summary: str = "",
    interpretation: Optional[SymptomInterpretation] = None,
) -> List[str]:

    print("\n" + "="*55)
    print("[CLARIFICATION AGENT] Called")
    print("  symptoms : " + symptoms)

    if interpretation:
        inferred_body_system = _infer_body_system_from_symptoms(symptoms)
        if interpretation.body_system.lower() == "general" and inferred_body_system != "general":
            print("  inferred body_system from symptoms: " + inferred_body_system)
            interpretation = interpretation.model_copy(update={"body_system": inferred_body_system})

        print("  body_system : " + interpretation.body_system)
        print("  conditions  : " + str(interpretation.possible_conditions))
        print("  risk_level  : " + interpretation.risk_level)
        print("  emergency   : " + str(interpretation.is_emergency))
        context = (
            "Body system: " + interpretation.body_system + "\n"
            "Possible conditions: " + ", ".join(interpretation.possible_conditions) + "\n"
            "Risk level: " + interpretation.risk_level + "\n"
            "Emergency: " + str(interpretation.is_emergency) + "\n"
            "Symptom cluster: " + interpretation.symptom_cluster
        )
    else:
        print("  interpretation : None - will use symptom text only")
        context = "No structured interpretation available - use symptoms directly."

    user_message = (
        "Patient symptoms: " + symptoms + "\n\n"
        "Clinical interpretation:\n" + context + "\n\n"
        "Clinical summary: " + (summary or "Not available") + "\n\n"
        "Generate exactly 5 targeted follow-up questions for this specific case.\n"
        "Return ONLY the JSON array of 5 strings."
    )

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user_message},
    ]

    for attempt in range(1, 4):
        try:
            raw = chat_completion(messages, temperature=0.2, json_mode=False)
            print("[CLARIFICATION AGENT] LLM raw (attempt " + str(attempt) + "): " + raw[:200])

            cleaned = raw.strip()
            if "```" in cleaned:
                parts = cleaned.split("```")
                for part in parts:
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("["):
                        cleaned = part
                        break

            start = cleaned.find("[")
            end = cleaned.rfind("]")
            if start != -1 and end != -1:
                cleaned = cleaned[start:end + 1]

            questions = json.loads(cleaned)

            if not isinstance(questions, list):
                raise ValueError("Expected list, got " + str(type(questions)))

            questions = [str(q).strip() for q in questions if q and str(q).strip()]

            if len(questions) < 5:
                raise ValueError("Too few questions: " + str(len(questions)))

            if interpretation and interpretation.body_system.lower() != "general":
                focused_terms = _focus_terms_for_system(interpretation.body_system.lower())
                focused_count = sum(
                    any(term in q.lower() for term in focused_terms)
                    for q in questions
                )
                if focused_count < 3:
                    raise ValueError(
                        "Generated follow-up questions are too generic for body system " + interpretation.body_system
                    )

            print("[CLARIFICATION AGENT] OK - " + str(len(questions)) + " questions:")
            for i, q in enumerate(questions, 1):
                print("  " + str(i) + ". " + q)
            print("="*55)
            return questions[:5]

        except Exception as exc:
            print("[CLARIFICATION AGENT] Attempt " + str(attempt) + " failed: " + str(exc))
            logger.warning("[ClarificationAgent] attempt %d failed: %s", attempt, exc)

    print("[CLARIFICATION AGENT] All LLM attempts failed - using body-system fallback")
    fallback = _body_system_fallback(interpretation, symptoms)
    print("[CLARIFICATION AGENT] fallback (" + str(len(fallback)) + " questions):")
    for i, q in enumerate(fallback, 1):
        print("  " + str(i) + ". " + q)
    print("="*55)
    return fallback


def _infer_body_system_from_symptoms(symptoms: str) -> str:
    text = symptoms.lower()
    mappings = {
        "cardiac": ["chest pain", "shortness of breath", "sob", "palpitations", "left arm", "jaw", "pressure", "tightness", "sweating", "heart", "angina"],
        "neurological": ["weakness", "numb", "difficulty speaking", "slurred speech", "blurred vision", "seizure", "headache", "dizziness", "face droop", "numbness", "confusion", "tingling"],
        "hepatic": ["jaundice", "yellow", "dark urine", "pale stool", "liver", "right side pain", "itching", "abdominal pain", "upper right"],
        "respiratory": ["cough", "wheezing", "breathing", "breathless", "sputum", "chest tightness", "respiratory", "asthma", "pneumonia", "shortness"],
        "gastrointestinal": ["abdominal", "stomach", "nausea", "vomit", "diarrhea", "constipation", "bloody stool", "bloating", "heartburn", "indigestion", "gastric"],
        "endocrine": ["thirst", "urination", "blood sugar", "diabetes", "weight loss", "weight gain", "fatigue", "thyroid", "hormone", "cold intolerance"],
        "musculoskeletal": ["joint", "swelling", "back pain", "muscle", "injury", "trauma", "stiffness", "sprain", "strain", "bone"],
    }

    for system, keywords in mappings.items():
        if any(keyword in text for keyword in keywords):
            return system
    return "general"


def _focus_terms_for_system(system: str) -> list:
    return {
        "cardiac": ["chest", "heart", "arm", "jaw", "back", "pressure", "sweat", "palpitation"],
        "neurological": ["face", "arm", "leg", "speech", "vision", "headache", "weakness", "numb"],
        "hepatic": ["jaundice", "urine", "stool", "liver", "upper right", "alcohol"],
        "respiratory": ["breath", "cough", "wheeze", "sputum", "asthma", "lung", "fever"],
        "gastrointestinal": ["abdominal", "stomach", "nausea", "vomit", "diarrhea", "constipation", "bloating"],
        "endocrine": ["sugar", "diabetes", "thirst", "urination", "weight", "fatigue", "thyroid"],
        "musculoskeletal": ["joint", "swelling", "back", "muscle", "injury", "pain", "movement"],
    }.get(system, [])


def _body_system_fallback(
    interpretation: Optional[SymptomInterpretation],
    symptoms: str,
) -> List[str]:
    if not interpretation:
        inferred = _infer_body_system_from_symptoms(symptoms)
        interpretation = SymptomInterpretation(
            possible_conditions=["unspecified condition"],
            body_system=inferred,
            risk_level="moderate",
            symptom_cluster=symptoms[:120],
            is_emergency=False,
        )

    system = interpretation.body_system.lower()

    if "cardiac" in system:
        return [
            "Does the chest pain spread to your left arm, jaw, neck, or back?",
            "Are you experiencing shortness of breath along with the chest pain?",
            "Are you sweating, feeling nauseous, or lightheaded right now?",
            "Do you feel pressure or squeezing in your chest rather than sharp pain?",
            "Have you ever been diagnosed with heart disease or had a heart attack before?",
        ]

    if "neurological" in system:
        return [
            "Can you raise both arms - is one side weaker than the other?",
            "Is one side of your face drooping or feeling numb?",
            "Are you having difficulty speaking or finding the right words?",
            "Did the weakness or numbness come on suddenly within the last few hours?",
            "Are you experiencing a sudden severe headache unlike any before?",
        ]

    if "hepatic" in system or "liver" in system:
        return [
            "When did you first notice the yellowing of your skin or eyes?",
            "Is your urine dark brown or tea-colored?",
            "Is your stool pale, clay-colored, or white?",
            "Is the abdominal pain located on the upper right side?",
            "Have you consumed alcohol recently or been exposed to hepatitis?",
        ]

    if "respiratory" in system:
        return [
            "Are you having difficulty breathing even while sitting still?",
            "Is your cough producing mucus - if so, what color is it?",
            "Are you experiencing chest tightness or wheezing?",
            "Do you have a fever along with the breathing difficulty?",
            "Do you have a history of asthma, COPD, or other lung conditions?",
        ]

    if "gastrointestinal" in system:
        return [
            "Can you point to exactly where the abdominal pain is worst?",
            "Have you noticed any blood in your stool or vomit?",
            "Have you had diarrhea, constipation, or changes in bowel habits?",
            "Does the pain get worse after eating or is it constant?",
            "Have you eaten anything unusual or traveled recently?",
        ]

    if "endocrine" in system:
        return [
            "What was your most recent blood sugar reading?",
            "Are you experiencing excessive thirst or frequent urination?",
            "Have you noticed unexplained weight loss or gain recently?",
            "Are you feeling unusually fatigued or weak throughout the day?",
            "Do you have a history of diabetes or thyroid conditions?",
        ]

    if "musculoskeletal" in system:
        return [
            "Did you have any injury, fall, or trauma before the pain started?",
            "Is there any visible swelling, redness, or warmth around the painful area?",
            "Does the pain get worse with movement or is it present at rest too?",
            "Is the pain in one specific joint or spread across multiple areas?",
            "Have you had similar joint or muscle pain before?",
        ]

    return [
        "Can you describe exactly where the discomfort is located?",
        "Did the symptoms start suddenly or come on gradually?",
        "On a scale of 1-10, how severe are your symptoms right now?",
        "Have you taken any medication for these symptoms, and did it help?",
        "Do you have any known medical conditions or are you on regular medication?",
    ]
