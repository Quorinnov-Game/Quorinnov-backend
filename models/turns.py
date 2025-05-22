from sqlalchemy import Column, Integer, String
from database import Base

class Turn(Base):
    __tablename__ = "turns"

    id = Column(Integer, primary_key=True, index=True)  # also turn_number
    player1_action = Column(String, nullable=True)
    player2_action = Column(String, nullable=True)
