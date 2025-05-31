import argparse
import asyncio
import random
import threading

import torch
from stable_baselines3 import PPO

from agents.simple_agent import SimpleAgent
from client import AgentClient
from src.client.move import convert_int_to_move
from src.utils import secrets
from src.utils.config import config
from src.utils.parser import parse_state, get_legal_moves


class ModelAgent:
    def __init__(self):
        self.name = "ModelAgent"
        self.model = PPO.load(f'{secrets.PROJECT_ROOT}/{config.BEST_MODEL_PATH}').policy
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def move(self, state, **kwargs):
        action = self.model(parse_state(state, self_name="Gradient clipers", torch_device=self.device))[0].item()
        move = convert_int_to_move[action]
        max_distance = 3
        for distance in range(max_distance, 0, -1):
            moves = get_legal_moves(state, self_name="Gradient clipers", distance=distance)
            if len(moves) != 0 and move not in moves:
                move = moves[random.randint(0, len(moves) - 1)]
                # move = moves[0]
        return move


def start_client(my_client):
    async def client_main():
        await my_client.connect()
        await my_client.run_loop()
        await my_client.disconnect()

    asyncio.run(client_main())


async def main():
    parser = argparse.ArgumentParser(description="Agent Client")
    parser.add_argument("--uri", type=str, default="localhost", help="WebSocket server URI")
    parser.add_argument("--port", type=int, default=3000, help="WebSocket server port")
    parser.add_argument("--user", type=str, default="g", help="User ID")
    parser.add_argument("-two", action="store_true", help="Use two users")
    args = parser.parse_args()

    if args.two:
        agent_1 = SimpleAgent()
        client_1 = AgentClient(uri=args.uri, port=args.port, user="k", agent=agent_1, verbose=True)

        agent_2 = SimpleAgent()
        client_2 = AgentClient(uri=args.uri, port=args.port, user="l", agent=agent_2, verbose=True)

        thread_1 = threading.Thread(target=start_client, args=(client_1,))
        thread_2 = threading.Thread(target=start_client, args=(client_2,))

        thread_1.start()
        thread_2.start()

        thread_1.join()
        thread_2.join()
    else:
        agent = ModelAgent()
        client = AgentClient(uri=args.uri, port=args.port, user=args.user, agent=agent)

        thread = threading.Thread(target=start_client, args=(client,))
        thread.start()
        thread.join()


if __name__ == "__main__":
    asyncio.run(main())
