from sqlalchemy import Column, Integer, JSON
from database import Base

class State(Base):
    __tablename__ = "states"

    id = Column(Integer, primary_key=True, index=True)
    playerA = Column(JSON, default=[])  # ex: [{"player": (0,1)}, {"wall": (2,3)}]
    playerB = Column(JSON, default=[])
