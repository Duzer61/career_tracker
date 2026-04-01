from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.crud import get_cards
from app.db.database import SessionDep
from app.db.models import User
from app.schemas import CardResponse

router = APIRouter(prefix="/api/board", tags=["board"])


@router.get("", response_model=list[CardResponse])
async def get_board(db: SessionDep, current_user: User = Depends(get_current_user)):
    """
    ...
    """
    cards = await get_cards(db, current_user)
    cards_responses = [CardResponse.from_orm(card) for card in cards]
    return cards_responses


@router.post("/create-card")
async def create_card():
    pass
