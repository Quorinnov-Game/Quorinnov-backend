# models/board.py
from sqlalchemy import Column, Integer, ForeignKey, String
from database import Base

class Board(Base):
    __tablename__ = "boards"

    id = Column(Integer, primary_key=True)
    width = Column(Integer, default=9)
    height = Column(Integer, default=9)
    state_id = Column(Integer, ForeignKey("states.id"))
    winner = Column(String, nullable=True)
