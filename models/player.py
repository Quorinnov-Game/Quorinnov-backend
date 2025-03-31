from sqlalchemy import Column, Integer, String
from database import Base

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    position = Column(String, nullable=False)  # ví dụ "e1"
    direction = Column(String, nullable=False)  # "up" hoặc "down"
    walls_left = Column(Integer, default=10)