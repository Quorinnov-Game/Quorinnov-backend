class Wall:
    """
    represent 1 (Wall) on board, with  (horizontal/vertical).
    """
    def __init__(self, row, col, orientation):
        """
        row, col: position of wall
        orientation: 'H' (horizontal) hoặc 'V' (vertical)
        """
        self.row = row
        self.col = col
        self.orientation = orientation

    def to_dict(self):
        return {
            "row": self.row,
            "col": self.col,
            "orientation": self.orientation
        }
