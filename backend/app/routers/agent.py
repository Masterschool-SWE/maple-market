"""Agent invocation routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..agent import service
from ..auth import get_current_user
from ..database import get_session
from ..models import User
from ..schemas import AgentInvokeRequest, AgentInvokeResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/invoke", response_model=AgentInvokeResponse)
def invoke(
    req: AgentInvokeRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    try:
        reply = service.invoke_keeper(
            session,
            current_user,
            req.message,
            model=req.model,
            temperature=req.temperature,
            reasoning_effort=req.reasoning_effort,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Support is unavailable: {exc}") from exc

    return AgentInvokeResponse(reply=reply)
