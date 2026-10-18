"""User routes."""
from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..models import User
from ..schemas import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
