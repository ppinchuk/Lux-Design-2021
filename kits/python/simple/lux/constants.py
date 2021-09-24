import io
import sys
import getpass
import json
from os import path
dir_path = path.dirname(__file__)


constants_path = path.abspath(
    path.join(dir_path, "strategy_hyperparameters.json")
)

with open(constants_path) as f:
    STRATEGY_HYPERPARAMETERS = json.load(f)


constants_path = path.abspath(path.join(dir_path, "game_constants.json"))
with open(constants_path) as f:
    GAME_CONSTANTS = json.load(f)

GAME_CONSTANTS["PARAMETERS"]["CYCLE_LENGTH"] = GAME_CONSTANTS["PARAMETERS"]["DAY_LENGTH"] + GAME_CONSTANTS["PARAMETERS"]["NIGHT_LENGTH"]


class StrategyTypes:
    STARTER = 'Starter'
    TIME_BASED = 'Time-Based'


class Constants:

    class INPUT_CONSTANTS:
        RESEARCH_POINTS = "rp"
        RESOURCES = "r"
        UNITS = "u"
        CITY = "c"
        CITY_TILES = "ct"
        ROADS = "ccd"
        DONE = "D_DONE"

    class DIRECTIONS:
        NORTH = "n"
        WEST = "w"
        SOUTH = "s"
        EAST = "e"
        CENTER = "c"

    class UNIT_TYPES:
        WORKER = 0
        CART = 1

    class RESOURCE_TYPES:
        WOOD = "wood"
        URANIUM = "uranium"
        COAL = "coal"


class ValidActions:
    MOVE = "move"
    TRANSFER = "transfer"
    PILLAGE = "pillage"
    BUILD = "build"
    COLLECT = "collect"
    MANAGE = "manage"

    @classmethod
    def for_unit(cls, u_type):
        if u_type == Constants.UNIT_TYPES.WORKER:
            return {cls.MOVE, cls.TRANSFER, cls.PILLAGE, cls.BUILD, cls.COLLECT, cls.MANAGE}
        elif u_type == Constants.UNIT_TYPES.CART:
            return {cls.MOVE, cls.TRANSFER}
        else:
            return set()

    @classmethod
    def can_be_adjacent(cls):
        return {cls.TRANSFER, cls.COLLECT}


class LogicGlobals:
    game_state = None
    player = None
    start_tile = None
    unlocked_coal = False
    unlocked_uranium = False
    cities = None
    pos_being_built = set()
    resource_cluster_to_defend = None
    clusters_to_colonize = set()
    max_resource_cluster_amount = 0
    TBS_COM = None
    TBS_citytiles = set()


UNIT_TYPE_AS_STR = {
    0: "WORKER",
    1: "CART"
}


ALL_DIRECTIONS = [
    Constants.DIRECTIONS.NORTH, Constants.DIRECTIONS.EAST,
    Constants.DIRECTIONS.SOUTH, Constants.DIRECTIONS.WEST
]

ALL_DIRECTIONS_AND_CENTER = [
    Constants.DIRECTIONS.NORTH, Constants.DIRECTIONS.EAST,
    Constants.DIRECTIONS.SOUTH, Constants.DIRECTIONS.WEST,
    Constants.DIRECTIONS.CENTER
]

if getpass.getuser() == 'Paul':
    print_out = io.StringIO()
else:
    print_out = sys.__stderr__

