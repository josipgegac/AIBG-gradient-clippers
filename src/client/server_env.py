import asyncio
import warnings

import gymnasium as gym
import numpy as np
import requests
from gymnasium import spaces

from src.client.move import convert_int_to_move
from src.client.web_client import AgentClient
from src.utils.config import config
from src.utils.parser import parse_state


def run_async(coro):
    """
    Runs async code from sync context, reusing loop if needed.
    Works around 'Event loop is closed' issues.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # In notebooks or frameworks like FastAPI, Jupyter, etc.
        return asyncio.ensure_future(coro)
    else:
        return loop.run_until_complete(coro)


class ServerEnv(gym.Env):
    """
    Custom Environment that follows gym interface.
    This is a simple env where the agent must learn to go always left.
    """

    def __init__(self, other_agent):
        super(ServerEnv, self).__init__()
        self.other_agent = other_agent
        self.old_score = None

        while True:
            try:
                response = requests.get("http://localhost:3000/api/reset")
                if response.status_code == 200:
                    break
            except Exception as _:
                pass
        self.action_space = spaces.Discrete(4)

        self.client_1 = AgentClient(uri="localhost", port=3000, user="g", agent=None)
        self.client_2 = AgentClient(uri="localhost", port=3000, user="o", agent=self.other_agent)
        self.game_state = None
        self.observation_space = spaces.Dict({
            "grid": spaces.Box(low=-np.inf, high=np.inf, shape=(config.C, config.H, config.W), dtype=np.float32),
            "side": spaces.Box(low=-np.inf, high=np.inf, shape=(config.S,), dtype=np.float32)
        })

        self.connect_and_get_state()
        self.wait_for_game_start()

    def connect_and_get_state(self):
        rand = np.random.rand()
        if rand < 0.5:
            run_async(self.client_1.connect())
            self.our_agent_name = self.client_1.name
            run_async(self.client_2.connect())
        else:
            run_async(self.client_2.connect())
            run_async(self.client_1.connect())
            self.our_agent_name = self.client_1.name
        self.game_state = run_async(self.client_1.get_state())

    def wait_for_game_start(self):
        counter = 0
        while True:
            try:
                response = requests.get("http://localhost:3000/api/ready")
                if response.status_code == 200 and response.json().get("status") == "ok":
                    break
            except Exception as e:
                print(e)
            counter += 1

            if counter > 15:
                warnings.warn("Force reset")
                self.reset(start_check=False)

    def reset(self, seed=None, options=None, start_check=True):
        print("Resetting the game server")
        run_async(self.client_1.disconnect())
        run_async(self.client_2.disconnect())

        # Reset the game server
        while True:
            try:
                response = requests.get("http://localhost:3000/api/reset")
                if response.status_code == 200:
                    break
            except Exception as _:
                pass

        # Reconnect clients
        self.client_1 = AgentClient(uri="localhost", port=3000, user="g", agent=None)
        self.client_2 = AgentClient(uri="localhost", port=3000, user="o", agent=self.other_agent)
        self.our_agent_name = self.client_1.name

        self.connect_and_get_state()
        if start_check:
            self.wait_for_game_start()

        observation = self._extract_observation(self.game_state)
        return observation, {}

    def step(self, action):
        action = convert_int_to_move[action]

        run_async(self.client_2.step_auto())
        run_async(self.client_1.step_manual(action))
        self.game_state = run_async(self.client_1.get_state())

        observation = self._extract_observation(self.game_state)

        terminated = self.game_state.get("winner") is not None
        truncated = False

        reward = 0
        if self.old_score is not None:
            new_score = 0
            if self.game_state["players"][0] == self.our_agent_name:
                new_score = self.game_state["players"][0]["score"]
            else:
                new_score = self.game_state["players"][1]["score"]

            reward = new_score - self.old_score
            self.old_score = new_score

        if terminated:
            if self.game_state["winner"] == self.our_agent_name:
                reward = reward + 50
            else:
                reward = reward - 100

        if self.old_score is None:
            if self.game_state["players"][0] == self.our_agent_name:
                self.old_score = self.game_state["players"][0]["score"]
            else:
                self.old_score = self.game_state["players"][1]["score"]

        return observation, reward, terminated, truncated, {}

    def _extract_observation(self, state):
        """
        Convert raw game state into a proper observation.
        You must customize this!
        """
        # Dummy: You should extract actual features from the state
        return parse_state(state, self.our_agent_name)

    def render(self):
        pass

    def close(self):
        run_async(self.client_1.disconnect())
        run_async(self.client_2.disconnect())
