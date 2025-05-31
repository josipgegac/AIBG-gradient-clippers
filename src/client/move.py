from enum import Enum

class Move(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"

    def __str__(self):
        return self.value


convert_int_to_move = {
    0: Move.UP,
    1: Move.DOWN,
    2: Move.LEFT,
    3: Move.RIGHT
}