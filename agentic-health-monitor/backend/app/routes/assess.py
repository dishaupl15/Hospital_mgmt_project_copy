import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.input_schema import FinalAssessmentRequest
from app.schemas.output_schema import FinalAssessmentResponse
from app.agents.orchestrator import final_assessment_workflow

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/final-assessment", response_model=FinalAssessmentResponse, status_code=status.HTTP_200_OK)
def final_assessment(payload: FinalAssessmentRequest):
    try:
        return final_assessment_workflow(
            original_data=payload.original_data,
            follow_up_answers=payload.follow_up_answers,
            symptom_summary=payload.symptom_summary,
            interpretation=payload.interpretation,
        )
    except Exception as exc:
        logger.error("final_assessment failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Final assessment failed. Please try again.",
        )
