from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import User
from app.schemas.schemas import AIClassifyRequest, AIClassifyOut, AIAssistantRequest, AIAssistantOut
from app.utils.dependencies import get_current_user, require_roles
from app.ai.classifier import classify_report
from app.ai.assistant import get_assistant_reply
from app.ai.insights import crime_hotspots, category_trends, priority_breakdown

router = APIRouter(prefix="/api/ai", tags=["AI"])

@router.post("/classify", response_model=AIClassifyOut)
def classify(payload: AIClassifyRequest, current_user: User = Depends(get_current_user)):
    return classify_report(payload.description)

@router.post("/assistant", response_model=AIAssistantOut)
def assistant(payload: AIAssistantRequest, current_user: User = Depends(get_current_user)):
    return {"reply": get_assistant_reply(payload.message)}

@router.get("/insights")
def insights(db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer"))):
    return {
        "hotspots": crime_hotspots(db),
        "category_trends": category_trends(db),
        "priority_breakdown": priority_breakdown(db),
    }
