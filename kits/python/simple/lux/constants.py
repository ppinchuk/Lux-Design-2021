import io
import sys
import getpass
import json
from os import path
from functools import partial
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
    RESEARCH_BASED = 'Research-Based'


class InputConstants:
    RESEARCH_POINTS = "rp"
    RESOURCES = "r"
    UNITS = "u"
    CITY = "c"
    CITY_TILES = "ct"
    ROADS = "ccd"
    DONE = "D_DONE"


class Directions:
    NORTH = "n"
    WEST = "w"
    SOUTH = "s"
    EAST = "e"
    CENTER = "c"


class UnitTypes:
    WORKER = 0
    CART = 1


class ResourceTypes:
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
        if u_type == UnitTypes.WORKER:
            return {cls.MOVE, cls.TRANSFER, cls.PILLAGE, cls.BUILD, cls.COLLECT, cls.MANAGE}
        elif u_type == UnitTypes.CART:
            return {cls.MOVE, cls.TRANSFER}
        else:
            return set()

    @classmethod
    def can_be_adjacent(cls):
        return {cls.TRANSFER, cls.COLLECT}


class LogicGlobals:
    game_state = None
    player = None
    opponent = None
    unlocked_coal = False
    unlocked_uranium = False
    cities = None
    pos_being_built = set()
    clusters_to_colonize = set()
    max_resource_cluster_amount = 0
    TBS_COM = None
    TBS_citytiles = set()
    RBS_rtype = None
    clusters_to_colonize_rbs = {}
    RBS_citytiles = set()
    RBS_cluster_carts = {}


UNIT_TYPE_AS_STR = {
    0: "WORKER",
    1: "CART"
}


ALL_DIRECTIONS = [
    Directions.NORTH, Directions.EAST,
    Directions.SOUTH, Directions.WEST
]

ALL_DIRECTIONS_AND_CENTER = [
    Directions.NORTH, Directions.EAST,
    Directions.SOUTH, Directions.WEST,
    Directions.CENTER
]

INFINITE_DISTANCE = 999

# def partial_print(*args):
#     return print(f"Turn {LogicGlobals.game_state.turn}", *args, file=sys.stderr)


if getpass.getuser() == 'Paul':
    print_out = io.StringIO()
    old_print = print
    log = partial(print, file=print_out)
    # print = partial(print, f"Turn {LogicGlobals.game_state.turn}", file=sys.stderr)
    print = lambda *args: old_print(f"Turn {LogicGlobals.game_state.turn}:", *args, file=sys.stderr)
else:
    log = partial(print, file=sys.__stderr__)
    print = print
