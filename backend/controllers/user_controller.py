from fastapi import APIRouter, Depends

from app.core.security import CurrentUser, get_current_user
from app.schemas import Me

router = APIRouter(tags=["usuario"])


@router.get("/me", response_model=Me, summary="Usuario autenticado (valida el token)")
def me(user: CurrentUser = Depends(get_current_user)):
    return Me(id=user.id, email=user.email)
