import json
from os import path
dir_path = path.dirname(__file__)
constants_path = path.abspath(path.join(dir_path, "game_constants.json"))
with open(constants_path) as f:
    GAME_CONSTANTS = json.load(f)

GAME_CONSTANTS["PARAMETERS"]["CYCLE_LENGTH"] = GAME_CONSTANTS["PARAMETERS"]["DAY_LENGTH"] + GAME_CONSTANTS["PARAMETERS"]["NIGHT_LENGTH"]