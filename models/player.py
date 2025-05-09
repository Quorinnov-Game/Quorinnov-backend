from sqlalchemy import Column, Integer, String
from database import Base
from sqlalchemy.dialects.postgresql import JSON

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    color = Column(String, nullable=False)  # ví dụ "red" or "blue"
    name = Column(String, nullable=True)
    position = Column(JSON, nullable=False)  # ví dụ "e1"
    direction = Column(String, nullable=True)  # "up" hoặc "down"
    walls_left = Column(Integer, default=10)