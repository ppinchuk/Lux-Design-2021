import io
import sys
import getpass
import json
from os import path
from functools import partial
from collections import deque
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
    unlock_coal_memory = deque(maxlen=2)
    unlock_uranium_memory = deque(maxlen=2)
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
    radius_for_clusters = 0
    main_city_close_to_coal = None
    CLUSTER_ID_TO_BUILDERS = {}
    CLUSTER_ID_TO_MANAGERS = {}
    RESOURCES_BEING_COLLECTED = {}

    @classmethod
    def reset(cls):
        cls.game_state = None
        cls.player = None
        cls.opponent = None
        cls.unlocked_coal = False
        cls.unlocked_uranium = False
        cls.unlock_coal_memory = deque(maxlen=2)
        cls.unlock_uranium_memory = deque(maxlen=2)
        cls.cities = None
        cls.pos_being_built = set()
        cls.clusters_to_colonize = set()
        cls.max_resource_cluster_amount = 0
        cls.TBS_COM = None
        cls.TBS_citytiles = set()
        cls.RBS_rtype = None
        cls.clusters_to_colonize_rbs = {}
        cls.RBS_citytiles = set()
        cls.RBS_cluster_carts = {}
        cls.radius_for_clusters = 0
        cls.main_city_close_to_coal = None
        cls.CLUSTER_ID_TO_BUILDERS = {}
        cls.CLUSTER_ID_TO_MANAGERS = {}
        cls.RESOURCES_BEING_COLLECTED = {}

    @classmethod
    def just_unlocked_new_resource(cls):
        if cls.game_state is None:
            raise ValueError("Game state must be set!")
        if cls.game_state.turn < 2:
            return False
        return sum(cls.unlock_coal_memory) == 1 or sum(cls.unlock_uranium_memory) == 1

    @classmethod
    def add_as_builder(cls, u_id, cluster_id):
        cls.remove_as_manager(u_id, cluster_id)
        cls.CLUSTER_ID_TO_BUILDERS[cluster_id] = cls.CLUSTER_ID_TO_BUILDERS.get(cluster_id, set()) | {u_id}

    @classmethod
    def add_as_manager(cls, u_id, cluster_id):
        cls.remove_as_builder(u_id, cluster_id)
        cls.CLUSTER_ID_TO_MANAGERS[cluster_id] = cls.CLUSTER_ID_TO_MANAGERS.get(cluster_id, set()) | {u_id}

    @classmethod
    def remove_as_builder(cls, u_id, cluster_id):
        cls.CLUSTER_ID_TO_BUILDERS[cluster_id] = cls.CLUSTER_ID_TO_BUILDERS.get(cluster_id, set()) - {u_id}

    @classmethod
    def remove_as_manager(cls, u_id, cluster_id):
        cls.CLUSTER_ID_TO_MANAGERS[cluster_id] = cls.CLUSTER_ID_TO_MANAGERS.get(cluster_id, set()) - {u_id}


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


def is_turn_during_night(turn):
    return GAME_CONSTANTS["PARAMETERS"]["DAY_LENGTH"] - turn % GAME_CONSTANTS["PARAMETERS"]["CYCLE_LENGTH"] <= 0


if getpass.getuser() == 'Paul':
    print_out = io.StringIO()
    old_print = print
    print = log = partial(print, file=print_out)
else:
    log = partial(print, file=sys.__stderr__)
    print = print
