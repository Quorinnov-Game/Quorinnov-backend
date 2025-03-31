from sqlalchemy import Column, Integer, String
from database import Base

class Board(Base):
    __tablename__ = "boards"
    id = Column(Integer, primary_key=True, index=True)
    state = Column(String)  # Có thể lưu JSON.stringify(board matrix)
