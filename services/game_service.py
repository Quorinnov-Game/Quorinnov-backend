from sqlalchemy.orm import Session
from models.board import Board
from models.player import Player
from models.wall import Wall

def create_board(db: Session, state: str):
    board = Board(state=state)
    db.add(board)
    db.commit()
    db.refresh(board)
    return board

def create_player(db: Session, name: str, position: str, direction: str):
    player = Player(name=name, position=position, direction=direction)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player

def create_wall(db: Session, x: int, y: int, direction: str):
    wall = Wall(x=x, y=y, direction=direction)
    db.add(wall)
    db.commit()
    db.refresh(wall)
    return wall
