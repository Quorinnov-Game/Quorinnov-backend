from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from services import game_service
from database import get_db

router = APIRouter()

@router.post("/board")
def create_board(state: str, db: Session = Depends(get_db)):
    return game_service.create_board(db, state)

@router.post("/player")
def create_player(name: str, position: str, direction: str, db: Session = Depends(get_db)):
    return game_service.create_player(db, name, position, direction)

@router.post("/wall")
def create_wall(x: int, y: int, direction: str, db: Session = Depends(get_db)):
    return game_service.create_wall(db, x, y, direction)
