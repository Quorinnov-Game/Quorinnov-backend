from sqlalchemy import Column, Integer, String, JSON
from database import Base

class Turn(Base):
    __tablename__ = "turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position = Column(JSON, nullable=False)
    walls = Column(JSON, nullable=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "position": self.position,
            "walls": self.walls
        }
