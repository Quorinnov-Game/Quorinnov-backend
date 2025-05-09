from sqlalchemy import Column, Integer, String
from database import Base

class Board(Base):
    __tablename__ = "boards"

    id = Column(Integer, primary_key=True, index=True)
    width = Column(Integer, nullable=False, default=9)
    height = Column(Integer, nullable=False, default=9)
    state = Column(String, nullable=True)  # Có thể lưu JSON chuỗi hoặc matrix serialize