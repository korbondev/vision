from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional
from core import constants as core_cst
import os
import bittensor as bt
from core.bittensor_overrides import synapse as bto_synapse
import argparse

bt.synapse = bto_synapse

if not hasattr(BaseModel, "model_dump"):
    setattr(BaseModel, "model_dump", getattr(BaseModel, "dict"))
if not hasattr(BaseModel, "model_copy"):
    setattr(BaseModel, "model_copy", getattr(BaseModel, "copy"))


def _get_env_file_from_cli_config() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env_file", type=str, default=None)
    args, _ = parser.parse_known_args()
    env_file = args.env_file

    if not env_file:
        parser.error("You didn't specify an env file! Use --env_file to specify it.")

    return env_file


env_file = _get_env_file_from_cli_config()
if not os.path.exists(env_file):
    bt.logging.error(f"Could not find env file: {env_file}")
load_dotenv(env_file, verbose=True)


class Config(BaseModel):
    hotkey_name: str = os.getenv(core_cst.HOTKEY_PARAM, "default")
    wallet_name: str = os.getenv(core_cst.WALLET_NAME_PARAM, "default")

    subtensor_network: str = os.getenv(core_cst.SUBTENSOR_NETWORK_PARAM, "test")
    subtensor_chainendpoint: Optional[str] = os.getenv(core_cst.SUBTENSOR_CHAINENDPOINT_PARAM, None)

    external_server_url: str = os.getenv(core_cst.EXTERNAL_SERVER_ADDRESS_PARAM, None)

    api_server_port: Optional[int] = os.getenv(core_cst.API_SERVER_PORT_PARAM, None)

    is_validator: bool = False


config = Config()
