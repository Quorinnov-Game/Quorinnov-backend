from sqlalchemy import Column, Integer, String, JSON
from database import Base

class Turn(Base):
    __tablename__ = "turns"

    id = Column(Integer, primary_key=True, autoincrement=True)  # acts as turn number
    move = Column(JSON, nullable=False)  # will store a dict like {"wall": [x, y]} or {"player": [x, y]}