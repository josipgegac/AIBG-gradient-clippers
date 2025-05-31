import random

from src.client import Move

VALID_DIRECTIONS = ["up", "down", "left", "right"]


def find_player_head(game_map, player_symbol):
    for i in range(len(game_map)):
        for j in range(len(game_map[i])):
            if game_map[i][j] and game_map[i][j].get('type') == 'snake-head' and game_map[i][j].get(
                    'playerName').lower() == player_symbol.lower():
                return {"x": i, "y": j}
    return {"x": 0, "y": 0}


def is_safe_move(game_map, pos):
    if (pos["x"] < 0 or pos["x"] >= len(game_map) or
            pos["y"] < 0 or pos["y"] >= len(game_map[0])):
        return False
    cell = game_map[pos["x"]][pos["y"]]
    return cell is None or (cell and cell.get('type') == 'apple')


def find_safe_direction(game_map, player_head):
    directions = [
        {"dx": -1, "dy": 0, "move": "up"},
        {"dx": 1, "dy": 0, "move": "down"},
        {"dx": 0, "dy": -1, "move": "left"},
        {"dx": 0, "dy": 1, "move": "right"}
    ]
    random.shuffle(directions)

    for direction in directions:
        new_pos = {
            "x": player_head["x"] + direction["dx"],
            "y": player_head["y"] + direction["dy"]
        }
        if is_safe_move(game_map, new_pos):
            return direction["move"]

    return random.choice(VALID_DIRECTIONS)


def find_closest_apple(game_map, player_head):
    rows, cols = len(game_map), len(game_map[0])
    queue = [(player_head["x"], player_head["y"], [])]
    visited = set()

    while queue:
        x, y, path = queue.pop(0)
        key = f"{x},{y}"

        if key in visited:
            continue
        visited.add(key)

        cell = game_map[x][y]
        if cell and cell.get('type') == 'apple':
            return path

        directions = [
            {"dx": -1, "dy": 0, "move": "up"},
            {"dx": 1, "dy": 0, "move": "down"},
            {"dx": 0, "dy": -1, "move": "left"},
            {"dx": 0, "dy": 1, "move": "right"}
        ]

        for direction in directions:
            new_x = x + direction["dx"]
            new_y = y + direction["dy"]

            if new_x < 0 or new_x >= rows or new_y < 0 or new_y >= cols:
                continue

            cell = game_map[new_x][new_y]
            if (cell is not None and
                    cell.get('type') != 'apple' and
                    (cell.get('type') == 'snake-head' or cell.get('type') == 'snake-body')):
                continue

            queue.append((new_x, new_y, path + [direction["move"]]))

    return None


class SimpleAgent:
    def move(self, state, **args):
        agent_id = args.get("agent_id", "Other agent")
        mode = args.get("mode", "other")

        direction = ""
        player_head = find_player_head(state['map'], agent_id.upper())
        if mode == "s":
            direction = find_safe_direction(state['map'], player_head)
        else:
            path = find_closest_apple(state['map'], player_head)
            if path and path[0]:
                next_pos = {
                    "x": player_head["x"],
                    "y": player_head["y"]
                }
                if path[0] == "up":
                    next_pos["x"] -= 1
                elif path[0] == "down":
                    next_pos["x"] += 1
                elif path[0] == "left":
                    next_pos["y"] -= 1
                elif path[0] == "right":
                    next_pos["y"] += 1

                direction = path[0] if is_safe_move(state['map'], next_pos) else find_safe_direction(state['map'],
                                                                                                     player_head)
            else:
                direction = find_safe_direction(state['map'], player_head)

        dir_to_enum_dict = {
            "up": Move.UP,
            "down": Move.DOWN,
            "left": Move.LEFT,
            "right": Move.RIGHT
        }
        return dir_to_enum_dict[direction]
