from sqlalchemy import Column, Integer, String
from database import Base

class Wall(Base):
    __tablename__ = "walls"

    id = Column(Integer, primary_key=True, index=True)
    x = Column(Integer, nullable=False)  # 0 đến 8
    y = Column(Integer, nullable=False)
    direction = Column(String, nullable=False)  # "horizontal" hoặc "vertical"