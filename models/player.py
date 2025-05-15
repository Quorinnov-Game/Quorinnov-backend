from sqlalchemy import Column, Integer, String, Boolean
from database import Base
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON
from .enums import Direction  # import Direction từ file định nghĩa enum


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    color = Column(String, nullable=False)  # e.g., "red" or "blue"
    name = Column(String, nullable=True)
    position = Column(JSON, nullable=False)  # {"x": 4, "y": 3}
    wallsRemaining = Column(Integer, default=10)  # rename từ walls_left
    isWinner = Column(Boolean, default=False)
    isPlayer = Column(Boolean, default=True)
    direction = Column(SQLEnum(Direction, name="direction_enum", create_type=False), nullable=True)


def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "position": self.position,
            "wallsRemaining": self.wallsRemaining,
            "isWinner": self.isWinner,
            "isPlayer": self.isPlayer,
            "direction": self.direction.value if self.direction else None

        }