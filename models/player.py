from sqlalchemy import Column, Integer, String
from database import Base

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    position = Column(String)  # ví dụ: "4,2"
    direction = Column(String)  # "N", "S", "E", "W"
