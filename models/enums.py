from enum import Enum

class Direction(str, Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"

class Orientation(str, Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"