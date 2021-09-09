from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, DIRECTIONS, Position, ResourceCluster
from lux.constants import Constants, ALL_DIRECTIONS, ALL_DIRECTIONS_AND_CENTER, ValidActions
from collections import Counter, UserDict
from functools import partial
from itertools import chain
import sys
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import math

### Define helper functions


class MemDict(UserDict):
    # adapted from https://stackoverflow.com/a/22552713/10615276
    """ Dictionary that memorizes key-value pairs after retrieving them. """

    def __call__(self, key):
        return self[key]

    def __missing__(self, key):
        result = self[key] = self.get_value(key)
        return result

    @staticmethod
    def get_value(key):
        raise NotImplementedError


class PositionToCluster(MemDict):
    @staticmethod
    def get_value(pos):
        if LogicGlobals.clusters is None:
            raise ValueError("No clusters found!")
        for cluster in LogicGlobals.clusters:
            if pos in cluster.resource_positions:
                return cluster
        return None


POSITION_TO_CLUSTER = PositionToCluster()


def city_tile_to_build(pos, game_state):
    if pos is None:
        return None
    if LogicGlobals.resource_cluster_to_defend is None:
        resource_pos = find_closest_resources(pos, prefer_upgrades=True)
        # print(f"Resource position: {resource_pos.pos}", file=sys.stderr)
        LogicGlobals.resource_cluster_to_defend = POSITION_TO_CLUSTER[resource_pos.pos]
        # print(f"Resource cluster pos to defend: {resource_cluster.pos_to_defend}", file=sys.stderr)

    for pos in LogicGlobals.resource_cluster_to_defend.pos_to_defend:
        cell = game_state.map.get_cell_by_pos(pos)
        if cell.citytile is None and pos not in LogicGlobals.pos_being_built:
            return cell.pos
    return None


# this snippet finds all resources stored on the map and puts them into a list so we can search over them
def find_resources(game_state):
    resource_tiles = []
    for cell in game_state.map.cells():
        if cell.has_resource():
            resource_tiles.append(cell)
    return resource_tiles


# the next snippet finds the closest resources that we can mine given position on a map
def find_closest_resources(pos, prefer_upgrades=False):
    closest_dist = math.inf
    closest_resource_tile = None
    for resource_tile in LogicGlobals.resource_tiles:
        if prefer_upgrades:
            if resource_tile.resource.type == Constants.RESOURCE_TYPES.WOOD:
                if resource_tile.resource.amount < 500 or LogicGlobals.unlocked_coal:
                    continue
            if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL:
                if not LogicGlobals.unlocked_coal or LogicGlobals.unlocked_uranium:
                    continue
        else:
            # we skip over resources that we can't mine due to not having researched them
            if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not LogicGlobals.unlocked_coal: continue
            if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not LogicGlobals.unlocked_uranium: continue
            if resource_tile.resource.type == Constants.RESOURCE_TYPES.WOOD and resource_tile.resource.amount < 500: continue
        dist = resource_tile.pos.distance_to(pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_resource_tile = resource_tile
    return closest_resource_tile


def find_closest_city_tile(pos, player):
    closest_city_tile = None
    if len(player.cities) > 0:
        closest_dist = math.inf
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile
    return closest_city_tile


def _check_for_cluster(game_map, position, resource_set, resource_type):
    for step in ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)):
        new_position = position.shift_by(*step)
        if game_map.is_within_bounds(new_position) and new_position not in resource_set:
            new_cell = game_map.get_cell_by_pos(new_position)
            if new_cell.resource is not None and new_cell.resource.type == resource_type:
                resource_set.add(new_position)
                _check_for_cluster(game_map, new_position, resource_set, resource_type)

    return resource_set


def find_clusters(game_state):
    resource_pos_found = set()
    resource_clusters = []
    for cell in game_state.map.cells():
        if cell.has_resource() and cell.pos not in resource_pos_found:
            new_cluster_pos = _check_for_cluster(game_state.map, cell.pos, {cell.pos}, cell.resource.type)
            resource_pos_found = resource_pos_found | new_cluster_pos
            new_cluster = ResourceCluster(cell.resource.type)
            new_cluster.add_resource_positions(*new_cluster_pos)
            resource_clusters.append(new_cluster)

    return resource_clusters


# if our cluster is separate from other base, build around them.
# Prefer 2x2 clusters


def set_unit_task(unit, game_state):
    if not unit.can_act():
        return

    new_city_pos = city_tile_to_build(LogicGlobals.start_tile.pos, game_state)
    if new_city_pos is not None:
        unit.set_task(action=ValidActions.BUILD, target=new_city_pos)
        LogicGlobals.pos_being_built.add(new_city_pos)

    # if unit.is_worker():
    #     # TODO: Update plan to move off of first city tile
    #     # we want to mine only if there is space left in the worker's cargo
    #     if unit.cargo_space_left() > 0:
    #         # find the closest resource if it exists to this unit
    #         closest_resource_tile = find_closest_resources(unit.pos)
    #         if closest_resource_tile is not None:
    #             unit.set_task(action=ValidActions.COLLECT, target=closest_resource_tile.pos)
    #         # TODO: Else, do something here!!
    #     else:
    #         new_city_pos = city_tile_to_build(LogicGlobals.start_tile.pos, game_state)
    #         if new_city_pos is not None:
    #             unit.set_task(action=ValidActions.BUILD, target=new_city_pos)
    #         # TODO: Else, do something here!!
    #         else:
    #             # find the closest citytile and move the unit towards it to drop resources to a citytile to fuel the city
    #             closest_city_tile = find_closest_city_tile(unit.pos, player)
    #             if closest_city_tile is not None:
    #                 unit.set_task(action=ValidActions.MOVE, target=closest_city_tile.pos)
    #             # TODO: Else, do something here!!


BEING_BUILT_BY = {}


class LogicGlobals:
    game_state = Game()
    start_tile = None
    clusters = None
    resource_tiles = None
    unlocked_coal = False
    unlocked_uranium = False
    pos_being_built = set()
    resource_cluster_to_defend = None


def agent(observation, configuration):

    ### Do not edit ###
    if observation["step"] == 0:
        # LogicGlobals.game_state = Game()
        LogicGlobals.game_state._initialize(observation["updates"])
        LogicGlobals.game_state._update(observation["updates"][2:])
        LogicGlobals.game_state.id = observation.player
    else:
        LogicGlobals.game_state._update(observation["updates"])

    ### AI Code goes down here! ###
    player = LogicGlobals.game_state.players[observation.player]
    opponent = LogicGlobals.game_state.players[(observation.player + 1) % 2]
    width, height = LogicGlobals.game_state.map.width, LogicGlobals.game_state.map.height

    if LogicGlobals.game_state.turn == 0:
        LogicGlobals.clusters = find_clusters(LogicGlobals.game_state)
        if LogicGlobals.start_tile is None:
            LogicGlobals.start_tile = find_closest_city_tile(Position(0, 0), player)

    LogicGlobals.resource_tiles = find_resources(LogicGlobals.game_state)
    LogicGlobals.unlocked_coal = player.researched_coal()
    LogicGlobals.unlocked_uranium = player.researched_uranium()

    for c in LogicGlobals.clusters:
        c.update_state(game_map=LogicGlobals.game_state.map)

    if LogicGlobals.resource_cluster_to_defend is not None and (all(LogicGlobals.game_state.map.get_cell_by_pos(p).citytile is not None for p in LogicGlobals.resource_cluster_to_defend.pos_to_defend) or LogicGlobals.resource_cluster_to_defend.total_amount <= 0):
        LogicGlobals.resource_cluster_to_defend = None

    actions = []
    blocked_positions = set()

    # Not sure if this is good or not
    for cell in LogicGlobals.game_state.map.cells():
        if cell.has_resource() and cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
            if cell.resource.amount < 500:
                blocked_positions = blocked_positions | cell.pos.adjacent_positions()
            else:
                blocked_positions = blocked_positions - cell.pos.adjacent_positions()

    for unit in opponent.units:
        # TODO: This may cause issues in the endgame
        blocked_positions = blocked_positions | unit.pos.adjacent_positions()

    for unit in player.units:
        unit.check_for_task_completion(game_map=LogicGlobals.game_state.map)
        blocked_positions.add(unit.pos)

    LogicGlobals.pos_being_built = {
        u.current_task[1] for u in player.units if
        u.current_task is not None and u.current_task[0] == ValidActions.BUILD
    }

    for unit in player.units:
        if unit.current_task is None:
            set_unit_task(unit, LogicGlobals.game_state)

    for unit in player.units:
        action, __ = unit.propose_action(player.units, find_closest_resources)
        # print(f"Unit at {unit.pos} proposed action {action}", file=sys.stderr)
        if action == ValidActions.MOVE:
            blocked_positions.discard(unit.pos)

    proposed_positions = {}
    for unit in player.units:
        action, target = unit.propose_action(
            player.units, find_closest_resources
        )
        if action is None:
            continue
        elif action == ValidActions.BUILD:
            actions.append(unit.build_city())
        elif action == ValidActions.TRANSFER:
            actions.append(unit.transfer(*target))
            unit.did_just_transfer = True
        elif action == ValidActions.PILLAGE:
            actions.append(unit.pillage())
        elif action == ValidActions.MOVE:
            blocked_positions.discard(unit.pos)

            pos_to_check = {}
            for direction in ALL_DIRECTIONS:
                new_pos = unit.pos.translate(direction, 1)
                pos_contains_citytile = LogicGlobals.game_state.map.get_cell_by_pos(new_pos).citytile is not None
                if not LogicGlobals.game_state.map.is_within_bounds(new_pos) or new_pos in blocked_positions or (pos_contains_citytile and unit.should_avoid_citytiles):
                    continue
                pos_to_check[direction] = new_pos
            if not pos_to_check:
                continue
            dir_to_move = unit.pos.direction_to(target, pos_to_check=pos_to_check)
            new_pos = pos_to_check[dir_to_move]
            proposed_positions.setdefault(new_pos, []).append((unit, dir_to_move))

    for pos, units in proposed_positions.items():
        unit, direction = max(units, key=lambda pair: pair[0].turns_spent_waiting_to_move)
        actions.append(unit.move(direction))
        unit.turns_spent_waiting_to_move = 0
        for other_unit in units:
            if other_unit[0].id != unit.id:
                other_unit[0].turns_spent_waiting_to_move += 1

    for _, city in player.cities.items():
        for city_tile in city.citytiles:
            if city_tile.can_act():
                if len(player.units) < player.city_tile_count:
                    actions.append(city_tile.build_worker())
                else:
                    actions.append(city_tile.research())

    # DEBUG STUFF

    actions.append(
        annotate.sidetext(
            f"Found {len(LogicGlobals.clusters)} clusters",
        )
    )
    actions.append(
        annotate.sidetext(
            "Cluster - N_resource - N_defend",
        )
    )
    for cluster in LogicGlobals.clusters:
        actions.append(
            annotate.sidetext(
                f"[{cluster.min_loc[0]:2d}; {cluster.min_loc[1]:2d}] - {cluster.total_amount:4d} - {cluster.n_to_block:1d}",
            )
        )
        # for pos in cluster.resource_positions:
        #     actions.append(annotate.circle(pos.x, pos.y))
        # for pos in cluster.pos_to_defend:
        #     actions.append(annotate.x(pos.x, pos.y))

    for unit in player.units:
        if unit.current_task is None:
            actions.append(
                annotate.sidetext(
                    f"{unit.id}: None"
                )
            )
        else:
            actions.append(
                annotate.sidetext(
                    f"{unit.id}: {unit.current_task[0]} at {unit.current_task[1]} ".replace(',', ';').replace('(','[').replace(')', ']')
                )
            )

    actions.append(annotate.text(15, 15, "A"))

    return actions




