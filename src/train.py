import time

from stable_baselines3 import PPO, A2C
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.env_util import make_vec_env

from src.agents.simple_agent import SimpleAgent
from src.client.server_env import ServerEnv
from src.model.CustomCombinedExtractor import CustomCombinedExtractor
from src.utils import secrets
from src.utils.config import config

agent = SimpleAgent()

vec_env = make_vec_env(ServerEnv, n_envs=1, env_kwargs=dict(other_agent=agent))

total_timesteps=2048
checkpoint_callback = CheckpointCallback(
    save_freq=total_timesteps,
    save_path=f'{secrets.PROJECT_ROOT}/{config.MODEL_PATH}/logs/{str(time.asctime(time.localtime())).replace(":", "_")}/',
    name_prefix='rl_model'
)
policy_kwargs = dict(
    features_extractor_class=CustomCombinedExtractor,
    features_extractor_kwargs={},
    net_arch=[256, 256]  # Shared layers after feature extraction
)

NUM_EPOCHS = 1000
model = PPO("MultiInputPolicy", vec_env, ent_coef=0.1, policy_kwargs=policy_kwargs, verbose=1).learn(total_timesteps=total_timesteps * NUM_EPOCHS, callback=checkpoint_callback)

model.save(config.MODEL_PATH)
