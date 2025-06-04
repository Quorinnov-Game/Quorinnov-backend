from sqlalchemy import Column, Integer, String,Boolean, ForeignKey, Enum as SQLEnum, column
from database import Base
from .enums import Orientation  # import Orientation từ file định nghĩa enum


class Wall(Base):
    __tablename__ = "walls"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"))  # liên kết player
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    orientation = Column(SQLEnum(Orientation, name="orientation_enum"), nullable=False)
    is_valid = Column(Boolean, nullable=False, default=False)



    def to_dict(self):
        return {
            "player_id": self.player_id,
            "position": {
                "x": self.x,
                "y": self.y
            },
            "orientation": self.orientation.value,
            "is_valid": self.is_valid
        }