import time
import warnings

import numpy as np
import json

import torch

from src.client import Move


def get_input_channel_indices_dict():
    input_channel_indices_dict = {
        # environment
        "empty": 0,
        "border": 1,
        # snakes
        "snake-body-self": 2,
        "snake-body-enemy": 3,
        "snake-head-self": 4,
        "snake-head-enemy": 5,
        # items
        "apple": 6,
        "golden-apple": 7,
        "katana": 8,
        "armour": 9,
        "shorten-self": 10,
        "shorten-enemy": 11,
        "shorten-both": 12,
        "tron-self": 13,
        "tron-enemy": 14,
        "tron-both": 15,
        "freeze": 16,
        "leap-self": 17,
        "leap-enemy": 18,
        "leap-both": 19,
        "nausea": 20,
        "reset-borders": 21
    }

    return input_channel_indices_dict


def get_active_items_indices_dict():
    active_items_indices_dict = {
        "golden-apple": 0,
        "katana": 1,
        "armour": 2,
        "tron-self": 3,
        "tron-enemy": 4,
        "tron-both": 5,
        "freeze": 6,
        "leap-self": 7,
        "leap-enemy": 8,
        "leap-both": 9,
    }
    return active_items_indices_dict


def parse_state(state, self_name="Gradient clipers", torch_device=None):

    game_map = state["map"]
    map_height = len(game_map)
    map_width = len(game_map[0])

    input_channel_indices = get_input_channel_indices_dict()
    n_channels = len(input_channel_indices)
    input_channels = np.zeros((n_channels,map_height,map_width))

    for row in range(map_height):
        for col in range(map_width):
            space = game_map[row][col]
            value = 1

            if space is None:
                channel_index = input_channel_indices["empty"]

            elif space["type"] in ["snake-body", "snake-head"]:
                if space["playerName"] == self_name:
                    channel_index = input_channel_indices[space["type"] + "-self"]
                else:
                    channel_index = input_channel_indices[space["type"] + "-enemy"]

            elif space["type"] in ["tron", "leap"]:
                channel_index = input_channel_indices[space["type"] + "-" + space["affect"]]

            elif space["type"].startswith("shorten"):
                channel_index = input_channel_indices["shorten-" + space["affect"]]
                value = space["type"].split("-")[1]

            else:
                if space["type"] not in input_channel_indices.keys():
                    continue
                channel_index = input_channel_indices[space["type"]]

            input_channels[channel_index, row, col] = value

    active_items_indices = get_active_items_indices_dict()

    active_items_durations = np.zeros((2,10))
    last_move_directions = np.zeros((2,4))
    self_score = None
    enemy_score = None
    normalised_self_head_position = [0,0]
    normalised_enemy_head_position = [0,0]
    good_next_moves = [0,0,0,0]

    if len(state["players"]) < 2:
        warnings.warn("Only one player!!!!!!!!!!!!!!!!!!!!!!!!")
        warnings.warn(str(state["players"]))

    for player in state["players"]:

        head_position = player["body"][0]
        head_row = head_position["row"]
        head_col = head_position["column"]
        normalised_head_position = [
            (head_position["row"] - map_height) / map_height,
            (head_position["column"] - map_width) / map_width
        ]

        if player["name"] == self_name:

            walls = ["border", "snake-body", "snake-head"]
            next_positions = [(head_row - 1, head_col),
                              (head_row + 1, head_col),
                              (head_row, head_col + 1),
                              (head_row, head_col - 1)]
            for i, (next_row, next_col) in enumerate(next_positions):
                if ((next_row >= 0) and (next_row < map_height) and
                    (next_col >= 0) and (next_col < map_width)):

                    space = game_map[next_row][next_col]
                    if (space is None) or (space["type"] not in walls):
                        good_next_moves[i] = 1


            player_index = 0
            self_score = player["score"]
            normalised_self_head_position = normalised_head_position
        else:
            player_index = 1
            enemy_score = player["score"]
            normalised_enemy_head_position = normalised_head_position

        direction_index = 0
        if player["lastMoveDirection"] == "up":
            direction_index = 0
        if player["lastMoveDirection"] == "down":
            direction_index = 1
        if player["lastMoveDirection"] == "left":
            direction_index = 2
        if player["lastMoveDirection"] == "right":
            direction_index = 3

        last_move_directions[player_index, direction_index] = 1

        for active_item in player["activeItems"]:
            if active_item["type"] in ["tron", "leap"]:
                item_index = active_items_indices[active_item["type"] + "-" + active_item["affect"]]
            else:
                if active_item["type"] not in active_items_indices.keys():
                    print(active_item["type"])
                    continue
                item_index = active_items_indices[active_item["type"]]

            active_items_durations[player_index, item_index] = active_item["duration"]

    if self_score is None or enemy_score is None:
        warnings.warn("Score is missing!!!!!!!!!!!!")
        warnings.warn(str(self_score))
        warnings.warn(str(enemy_score))
        if self_score is None:
            self_score = 0
        if enemy_score is None:
            enemy_score = 0

    score_value = np.tanh((self_score - enemy_score) / 500)

    side_channels = np.concatenate([active_items_durations.flatten(),
                                    last_move_directions.flatten(),
                                    [score_value],
                                    normalised_self_head_position,
                                    normalised_enemy_head_position,
                                    good_next_moves])
    if torch_device is not None:
        input_channels = torch.Tensor(input_channels).to(torch_device)
        side_channels = torch.Tensor(side_channels).to(torch_device)

    return {
        "grid": input_channels,
        "side": side_channels
    }

def get_legal_moves(state, distance, self_name="Gradient clipers"):
    game_map = state["map"]
    map_height = len(game_map)
    map_width = len(game_map[0])

    legal_moves = []

    for player in state["players"]:

        head_position = player["body"][0]
        head_row = head_position["row"]
        head_col = head_position["column"]
        normalised_head_position = [
            (head_position["row"] - map_height) / map_height,
            (head_position["column"] - map_width) / map_width
        ]

        if player["name"] == self_name:

            walls = ["border", "snake-body", "snake-head"]
            next_positions = {Move.UP: (head_row - distance, head_col),
                              Move.DOWN: (head_row + distance, head_col),
                              Move.RIGHT: (head_row, head_col + distance),
                              Move.LEFT: (head_row, head_col - distance)}
            for move, (next_row, next_col) in next_positions.items():
                if ((next_row >= 0) and (next_row < map_height) and
                    (next_col >= 0) and (next_col < map_width)):

                    space = game_map[next_row][next_col]
                    if (space is None) or (space["type"] not in walls):
                        legal_moves.append(move)

    return legal_moves

if __name__ == '__main__':
    filepath = "gamestateExample.json"
    with open(filepath, "r") as f:
        state = json.load(f)

    items = {}
    for row in state["map"]:
        for space in row:
            if space is None:
                items["empty"] = 1
            else:
                items[space["type"]] = 1


    print(items.keys())

    start_time = time.time()
    d = parse_state(state, self_name="BEST agent Uno")

    end_time = time.time()
    input_channels, side_channels = d["grid"], d["side"]
    input_channel_indices = get_input_channel_indices_dict()
    for channel, index in input_channel_indices.items():
        print(f"\n\nChannel: {channel}")
        for row in input_channels[index]:
            row = [str(int(item)) for item in row]
            print("".join(row))

    print("\n\nSide channels: ")
    print(side_channels)
    print(f"side channel size: {len(side_channels)}")
    print(end_time - start_time)

    print(get_legal_moves(state, self_name="BEST agent Uno"))
