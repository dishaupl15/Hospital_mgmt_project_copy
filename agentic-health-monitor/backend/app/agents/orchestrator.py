"""
app/agents/orchestrator.py
Coordinates all LLM agents. Routes call these functions — never agents directly.

Phase 1: AgentTrace on every step.
Phase 2: MedicalKnowledgeAgent + DiagnosisReasoningAgent inserted into pipeline.

Pipeline 1 (analyze_symptoms_workflow):
  SymptomInterpreter → SymptomSummarizer → ClarificationAgent → MedicalKnowledgeAgent → DiagnosisReasoningAgent (skipped here, runs in pipeline 2)

Pipeline 2 (final_assessment_workflow):
  MedicalKnowledgeAgent → DiagnosisReasoningAgent → RiskAgent → RecommendationAgent
"""
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.schemas.input_schema import SymptomFormInput
from app.schemas.output_schema import (
    AgentTrace,
    AnalyzeResponse,
    FinalAssessmentResponse,
    RagChunk,
    ConditionItem,
    SymptomInterpretationResult,
    DiagnosisResult,
    DiagnosedConditionResult,
)
from app.agents.symptom_agent import summarize_symptoms, interpret_symptoms
from app.agents.clarification_agent import generate_follow_up_questions
from app.agents.knowledge_agent import retrieve_medical_knowledge
from app.agents.diagnosis_agent import run_diagnosis
from app.agents.risk_agent import assess_risk
from app.agents.recommendation_agent import get_full_recommendation
from app.tools.rag_tool import retrieve_as_dicts

logger = logging.getLogger(__name__)


# ── Trace helpers ──────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def _log_start(agent_name: str, action: str) -> float:
    print(f"\n[AGENT START] {agent_name} — {action}")
    logger.info("[AGENT START] %s — %s", agent_name, action)
    return time.perf_counter()


def _log_complete(agent_name: str, summary: str, duration_ms: float) -> None:
    print(f"[AGENT COMPLETE] {agent_name} ({duration_ms}ms) — {summary}")
    logger.info("[AGENT COMPLETE] %s (%.0fms) — %s", agent_name, duration_ms, summary)


def _log_failed(agent_name: str, error: str, duration_ms: float) -> None:
    print(f"[AGENT FAILED] {agent_name} ({duration_ms}ms) — {error}")
    logger.error("[AGENT FAILED] %s (%.0fms) — %s", agent_name, duration_ms, error)


def _trace(
    agent_name: str,
    status: str,
    action: str,
    summary: str,
    duration_ms: float,
    used_fallback: bool = False,
) -> AgentTrace:
    return AgentTrace(
        agent_name=agent_name,
        status=status,
        action=action,
        summary=summary,
        duration_ms=duration_ms,
        timestamp=_now_iso(),
        used_fallback=used_fallback,
    )


# ── Pipeline 1: analyze_symptoms_workflow ─────────────────────────────────────

def analyze_symptoms_workflow(payload: SymptomFormInput) -> AnalyzeResponse:
    print("\n" + "="*60)
    print("[ORCHESTRATOR] analyze_symptoms_workflow CALLED")
    print(f"  patient  : {payload.name} | age={payload.age} | gender={payload.gender}")
    print(f"  symptoms : {payload.symptoms}")
    print(f"  duration : {payload.duration} | severity : {payload.severity}")
    print("="*60)

    traces: List[AgentTrace] = []
    interpretation_result: Optional[SymptomInterpretationResult] = None
    emergency_alert = False

    # ── Step 1: Symptom Interpreter ────────────────────────────────────────────
    action_1 = "Analyze symptom cluster, identify body system and risk level"
    t = _log_start("SymptomInterpreter", action_1)
    from app.agents.symptom_agent import SymptomInterpretation
    interp = SymptomInterpretation(
        possible_conditions=["unspecified condition"],
        body_system="general",
        risk_level="moderate",
        symptom_cluster=payload.symptoms[:120],
        is_emergency=False,
    )
    try:
        interp = interpret_symptoms(
            symptoms=payload.symptoms,
            age=payload.age,
            gender=payload.gender,
        )
        dur = _ms(t)
        used_fallback_1 = (
            interp.body_system == "general"
            and interp.possible_conditions == ["unspecified condition"]
        )
        emergency_alert = interp.is_emergency
        interpretation_result = SymptomInterpretationResult(
            possible_conditions=interp.possible_conditions,
            body_system=interp.body_system,
            risk_level=interp.risk_level,
            symptom_cluster=interp.symptom_cluster,
            is_emergency=interp.is_emergency,
        )
        summary_1 = (
            f"body_system={interp.body_system} | risk={interp.risk_level} | "
            f"emergency={interp.is_emergency} | conditions={interp.possible_conditions}"
        )
        _log_complete("SymptomInterpreter", summary_1, dur)
        traces.append(_trace("SymptomInterpreter", "completed", action_1, summary_1, dur, used_fallback_1))
    except Exception as exc:
        dur = _ms(t)
        _log_failed("SymptomInterpreter", str(exc), dur)
        traces.append(_trace("SymptomInterpreter", "failed", action_1, f"Error: {exc}", dur))

    if emergency_alert:
        print("[ORCHESTRATOR] ⚠️  EMERGENCY DETECTED — fast-path active")
        logger.warning("[ORCHESTRATOR] EMERGENCY DETECTED for symptoms: %s", payload.symptoms)

    # ── Step 2: Symptom Summarizer ─────────────────────────────────────────────
    action_2 = "Generate clinical summary and determine follow-up need"
    t = _log_start("SymptomSummarizer", action_2)
    summary = ""
    follow_up_needed = True
    try:
        summary, follow_up_needed, _ = summarize_symptoms(
            symptoms=payload.symptoms,
            duration=payload.duration,
            severity=payload.severity,
            bp=payload.bp,
            sugar=payload.sugar,
            temperature=payload.temperature,
            age=payload.age,
            gender=payload.gender,
            history=payload.history,
        )
        dur = _ms(t)
        used_fallback_2 = (
            "warrants clinical evaluation" in summary
            and "Follow-up questions have been generated" in summary
        )
        if emergency_alert:
            follow_up_needed = True
        summary_2 = f"follow_up_needed={follow_up_needed} | summary_len={len(summary)} chars"
        _log_complete("SymptomSummarizer", summary_2, dur)
        traces.append(_trace("SymptomSummarizer", "completed", action_2, summary_2, dur, used_fallback_2))
    except Exception as exc:
        dur = _ms(t)
        _log_failed("SymptomSummarizer", str(exc), dur)
        traces.append(_trace("SymptomSummarizer", "failed", action_2, f"Error: {exc}", dur))
        summary = f"Patient reports {payload.symptoms}, lasting {payload.duration} with {payload.severity} severity."
        follow_up_needed = True

    # ── Step 3: Clarification Agent ────────────────────────────────────────────
    questions: List[str] = []
    if follow_up_needed:
        action_3 = f"Generate targeted follow-up questions for body_system={interp.body_system}"
        t = _log_start("ClarificationAgent", action_3)
        try:
            questions = generate_follow_up_questions(
                symptoms=payload.symptoms,
                summary=summary,
                interpretation=interp,
            )
            dur = _ms(t)
            fallback_markers = [
                "Can you describe exactly where",
                "Did the symptoms start suddenly",
                "On a scale of 1-10",
            ]
            used_fallback_3 = any(
                any(q.startswith(m) for m in fallback_markers) for q in questions
            )
            summary_3 = f"{len(questions)} questions generated | sample: \"{questions[0][:60]}...\""
            _log_complete("ClarificationAgent", summary_3, dur)
            traces.append(_trace("ClarificationAgent", "completed", action_3, summary_3, dur, used_fallback_3))
        except Exception as exc:
            dur = _ms(t)
            _log_failed("ClarificationAgent", str(exc), dur)
            traces.append(_trace("ClarificationAgent", "failed", action_3, f"Error: {exc}", dur))
    else:
        print("[STEP 3] ClarificationAgent SKIPPED — follow_up_needed=False")
        logger.info("[ORCHESTRATOR] ClarificationAgent skipped")
        traces.append(_trace(
            "ClarificationAgent", "skipped",
            "Generate follow-up questions",
            "Skipped — concern level is LOW and follow-up not required",
            0.0,
        ))

    # ── Step 4: Medical Knowledge Agent ───────────────────────────────────────
    action_4 = f"Retrieve medical knowledge for symptoms + conditions={interp.possible_conditions}"
    t = _log_start("MedicalKnowledgeAgent", action_4)
    knowledge_context = "No relevant medical knowledge could be retrieved at this time."
    try:
        knowledge = retrieve_medical_knowledge(
            symptoms=payload.symptoms,
            possible_conditions=interp.possible_conditions,
            top_k=4,
        )
        dur = _ms(t)
        knowledge_context = knowledge.knowledge_context
        summary_4 = (
            f"chunks={knowledge.chunk_count} | sources={knowledge.sources} | "
            f"topics={knowledge.retrieved_topics}"
        )
        _log_complete("MedicalKnowledgeAgent", summary_4, dur)
        traces.append(_trace("MedicalKnowledgeAgent", "completed", action_4, summary_4, dur))
    except Exception as exc:
        dur = _ms(t)
        _log_failed("MedicalKnowledgeAgent", str(exc), dur)
        traces.append(_trace("MedicalKnowledgeAgent", "failed", action_4, f"Error: {exc}", dur))

    # ── Step 5: RAG Tool (for relevant_knowledge field in response) ────────────
    action_5 = "Retrieve raw RAG chunks for relevant_knowledge field"
    t = _log_start("RAGRetrieval", action_5)
    relevant_knowledge: List[RagChunk] = []
    try:
        raw_chunks = retrieve_as_dicts(payload.symptoms, top_k=3)
        relevant_knowledge = [
            RagChunk(
                id=str(c.get("id", "")),
                source=str(c.get("source", "unknown")),
                text=str(c.get("text", "")),
                score=float(c.get("score", 0.0)),
            )
            for c in raw_chunks
        ]
        dur = _ms(t)
        sources = [c.source for c in relevant_knowledge]
        summary_5 = f"{len(relevant_knowledge)} chunks retrieved | sources={sources}"
        _log_complete("RAGRetrieval", summary_5, dur)
        traces.append(_trace("RAGRetrieval", "completed", action_5, summary_5, dur))
    except Exception as exc:
        dur = _ms(t)
        _log_failed("RAGRetrieval", str(exc), dur)
        traces.append(_trace("RAGRetrieval", "failed", action_5, f"Error: {exc}", dur))

    print("\n[ORCHESTRATOR] analyze_symptoms_workflow COMPLETE")
    print("="*60 + "\n")

    return AnalyzeResponse(
        symptom_summary=summary,
        follow_up_needed=follow_up_needed,
        follow_up_questions=questions,
        relevant_knowledge=relevant_knowledge,
        interpretation=interpretation_result,
        emergency_alert=emergency_alert,
        agent_trace=traces,
    )


# ── Pipeline 2: final_assessment_workflow ─────────────────────────────────────

def final_assessment_workflow(
    original_data: SymptomFormInput,
    follow_up_answers: Dict[str, str],
    symptom_summary: Optional[str] = None,
) -> FinalAssessmentResponse:
    print("\n" + "="*60)
    print("[ORCHESTRATOR] final_assessment_workflow CALLED")
    print(f"  patient          : {original_data.name}")
    print(f"  symptoms         : {original_data.symptoms}")
    print(f"  follow_up_answers: {len(follow_up_answers)} answers")
    print("="*60)

    traces: List[AgentTrace] = []
    diagnosis_result: Optional[DiagnosisResult] = None

    # ── Step 1: Medical Knowledge Agent ───────────────────────────────────────
    action_1 = "Retrieve medical knowledge to ground diagnosis and risk reasoning"
    t = _log_start("MedicalKnowledgeAgent", action_1)
    medical_context = "No relevant medical knowledge could be retrieved at this time."
    knowledge_sources: List[str] = []
    knowledge_topics: List[str] = []
    try:
        knowledge = retrieve_medical_knowledge(
            symptoms=original_data.symptoms,
            possible_conditions=[],   # interpreter not re-run here; use symptoms alone
            top_k=4,
        )
        dur = _ms(t)
        medical_context = knowledge.knowledge_context
        knowledge_sources = knowledge.sources
        knowledge_topics = knowledge.retrieved_topics
        summary_1 = (
            f"chunks={knowledge.chunk_count} | sources={knowledge.sources} | "
            f"topics={knowledge.retrieved_topics}"
        )
        _log_complete("MedicalKnowledgeAgent", summary_1, dur)
        traces.append(_trace("MedicalKnowledgeAgent", "completed", action_1, summary_1, dur))
    except Exception as exc:
        dur = _ms(t)
        _log_failed("MedicalKnowledgeAgent", str(exc), dur)
        traces.append(_trace("MedicalKnowledgeAgent", "failed", action_1, f"Error: {exc}", dur))

    # ── Step 2: Diagnosis Reasoning Agent ─────────────────────────────────────
    action_2 = "Produce structured differential diagnosis from full patient case"
    t = _log_start("DiagnosisReasoningAgent", action_2)
    try:
        diag = run_diagnosis(
            symptoms=original_data.symptoms,
            body_system="general",          # interpreter output not stored in request; use general
            possible_conditions_from_interpreter=[],
            follow_up_answers=follow_up_answers,
            medical_context=medical_context,
            age=original_data.age,
            gender=original_data.gender,
            history=original_data.history,
            severity=original_data.severity,
        )
        dur = _ms(t)
        used_fallback_2 = (
            len(diag.possible_conditions) > 0
            and diag.possible_conditions[0].confidence == "low"
            and "consult a healthcare provider" in diag.possible_conditions[0].reason.lower()
        )
        diagnosis_result = DiagnosisResult(
            possible_conditions=[
                DiagnosedConditionResult(
                    name=c.name,
                    confidence=c.confidence,
                    reason=c.reason,
                    supporting_symptoms=c.supporting_symptoms,
                )
                for c in diag.possible_conditions
            ],
            reasoning_summary=diag.reasoning_summary,
            risk_factors=diag.risk_factors,
            sources=knowledge_sources,
            retrieved_topics=knowledge_topics,
        )
        summary_2 = (
            f"{len(diag.possible_conditions)} conditions | "
            f"risk_factors={len(diag.risk_factors)} | fallback={used_fallback_2}"
        )
        _log_complete("DiagnosisReasoningAgent", summary_2, dur)
        traces.append(_trace("DiagnosisReasoningAgent", "completed", action_2, summary_2, dur, used_fallback_2))
    except Exception as exc:
        dur = _ms(t)
        _log_failed("DiagnosisReasoningAgent", str(exc), dur)
        traces.append(_trace("DiagnosisReasoningAgent", "failed", action_2, f"Error: {exc}", dur))

    # ── Step 3: Risk Assessment Agent ─────────────────────────────────────────
    action_3 = "Assess risk level, possible conditions, and urgency from full case"
    t = _log_start("RiskAgent", action_3)
    conditions: List[ConditionItem] = []
    confidence = "Low"
    risk_level = "High"
    urgency = "Within 24 hours"
    explanation = ""
    try:
        conditions, confidence, risk_level, urgency, explanation = assess_risk(
            symptoms=original_data.symptoms,
            duration=original_data.duration,
            severity=original_data.severity,
            follow_up_answers=follow_up_answers,
            summary=symptom_summary or "",
        )
        dur = _ms(t)
        used_fallback_3 = (
            len(conditions) == 1
            and conditions[0].name == "Unspecified condition"
        )
        summary_3 = (
            f"risk={risk_level} | confidence={confidence} | urgency={urgency} | "
            f"conditions={[c.name for c in conditions]}"
        )
        _log_complete("RiskAgent", summary_3, dur)
        traces.append(_trace("RiskAgent", "completed", action_3, summary_3, dur, used_fallback_3))
    except Exception as exc:
        dur = _ms(t)
        _log_failed("RiskAgent", str(exc), dur)
        traces.append(_trace("RiskAgent", "failed", action_3, f"Error: {exc}", dur))
        conditions = [ConditionItem(name="Unspecified condition", score=0.5)]
        explanation = (
            f"Risk assessment could not be completed automatically. "
            f"Symptoms reported: {original_data.symptoms}. Please consult a healthcare provider."
        )

    # ── Step 4: Recommendation Agent ──────────────────────────────────────────
    action_4 = f"Generate patient-facing guidance for risk_level={risk_level}"
    t = _log_start("RecommendationAgent", action_4)
    rec: Dict = {}
    try:
        rec = get_full_recommendation(
            risk_level=risk_level,
            urgency=urgency,
            explanation=explanation,
            possible_conditions=conditions,
        )
        dur = _ms(t)
        used_fallback_4 = (
            "AI-generated assessment" in rec.get("disclaimer", "")
            and len(rec.get("next_steps", [])) <= 4
        )
        summary_4 = (
            f"recommendation_len={len(rec.get('recommendation', ''))} chars | "
            f"next_steps={len(rec.get('next_steps', []))} | fallback={used_fallback_4}"
        )
        _log_complete("RecommendationAgent", summary_4, dur)
        traces.append(_trace("RecommendationAgent", "completed", action_4, summary_4, dur, used_fallback_4))
    except Exception as exc:
        dur = _ms(t)
        _log_failed("RecommendationAgent", str(exc), dur)
        traces.append(_trace("RecommendationAgent", "failed", action_4, f"Error: {exc}", dur))
        rec = {
            "recommendation": "Please consult a healthcare provider promptly.",
            "next_steps": ["Seek medical attention as soon as possible."],
            "disclaimer": "This is an AI-generated assessment and does not replace professional medical advice.",
        }

    print("\n[ORCHESTRATOR] final_assessment_workflow COMPLETE")
    print("="*60 + "\n")

    return FinalAssessmentResponse(
        possible_conditions=conditions,
        confidence=confidence,
        risk_level=risk_level,
        urgency=urgency,
        explanation=explanation,
        recommendation=rec.get("recommendation", ""),
        next_steps=rec.get("next_steps", []),
        disclaimer=rec.get("disclaimer", ""),
        follow_up_answers=follow_up_answers,
        agent_trace=traces,
        diagnosis_result=diagnosis_result,
    )
