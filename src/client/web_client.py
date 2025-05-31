import json

import websockets

from .move import Move


# class AgentClient:
#     def __init__(self, uri, port, user, agent):
#         self.uri = uri
#         self.port = port
#         self.user = user
#         self.agent = agent
#
#     async def run_server(self):
#         uri = f"ws://{self.uri}:{self.port}?id={self.user}"
#         print(f"Connecting to {uri}")
#
#         try:
#             async with websockets.connect(uri) as ws:
#                 initial_message = await ws.recv()
#                 print(f"Initial message: {initial_message}")
#
#                 while True:
#                     state_raw = await ws.recv()
#                     state = json.loads(state_raw)
#                     print(f"Received state: {state}")
#
#                     if state["winner"] is not None:
#                         print(f"Game over!")
#                         break
#
#                     move = self.agent.move(state, agent_id=self.user)
#                     move_json = self.get_move_json(move)
#
#                     print(f"Sending move: {move_json}")
#                     await ws.send(move_json)
#         except ConnectionClosed:
#             print("Disconnected from WebSocket server")
#         except Exception as e:
#             print(f"Error: {e}")
#
#     def get_move_json(self, direction: Move):
#         return json.dumps({
#             "playerId": self.user,
#             "direction": str(direction),
#        })


class AgentClient:
    def __init__(self, uri, port, user, agent, verbose=False):
        self.uri = f"ws://{uri}:{port}?id={user}"
        self.user = user
        self.agent = agent
        self.ws = None
        self.latest_state = None
        self.verbose = verbose
        self.name = None

    async def connect(self):
        self.ws = await websockets.connect(self.uri)

        initial_message_raw = await self.ws.recv()
        initial_message = json.loads(initial_message_raw)
        if self.verbose:
            print(f"Initial message: {initial_message}")

        self.name = initial_message["name"]

    async def get_state(self):
        if not self.ws:
            raise RuntimeError("WebSocket is not connected.")
        if self.verbose:
            print("Waiting for state...")
        state_raw = await self.ws.recv()
        state = json.loads(state_raw)
        if self.verbose:
            print(f"State received: {state}")
        return state

    async def step_auto(self):
        state = await self.get_state()

        if state.get("winner") is not None:
            print("Game over!")
            return True

        move = self.agent.move(state)
        move_json = self.get_move_json(move)

        if self.verbose:
            print(f"Sending manual move: {move_json}")

        await self.ws.send(move_json)
        return False

    async def step_manual(self, move: Move):
        move_json = self.get_move_json(move)

        if self.verbose:
            print(f"Sending manual move: {move_json}")

        await self.ws.send(move_json)

    def get_move_json(self, direction: Move):
        return json.dumps({
            "playerId": self.user,
            "direction": str(direction),
        })

    async def disconnect(self):
        if self.ws:
            await self.ws.close()
            if self.verbose:
                print("Disconnected from WebSocket server")

    async def run_loop(self):
        if not self.ws:
            raise RuntimeError("WebSocket is not connected.")

        while True:
            is_done = await self.step_auto()
            if is_done:
                break