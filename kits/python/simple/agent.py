from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, DIRECTIONS, Position, ResourceCluster
from lux.constants import Constants, ALL_DIRECTIONS, ALL_DIRECTIONS_AND_CENTER
from collections import Counter, UserDict
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


def city_tile_to_build(pos, player, game_state):
    if pos is None or player.city_tile_count >= 5:
        return None
    for dir in [DIRECTIONS.CENTER] + ALL_DIRECTIONS:
        new_pos = pos.translate(dir, 1)
        if game_state.map.is_within_bounds(new_pos):
            cell = game_state.map.get_cell_by_pos(new_pos)
    # for x_add, y_add in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
    #     cell = game_state.map.get_cell(pos.x+x_add, pos.y+y_add)
            if not cell.has_resource() and cell.citytile is None:
                return cell
    return None


# this snippet finds all resources stored on the map and puts them into a list so we can search over them
def find_resources(game_state):
    resource_tiles = []
    for cell in game_state.map.cells():
        if cell.has_resource():
            resource_tiles.append(cell)
    return resource_tiles


# the next snippet finds the closest resources that we can mine given position on a map
def find_closest_resources(pos, player, resource_tiles):
    closest_dist = math.inf
    closest_resource_tile = None
    for resource_tile in resource_tiles:
        # we skip over resources that we can't mine due to not having researched them
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
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


def decide_unit_action(unit, player, game_state, resource_tiles, pos_units_will_move_to):
    if unit.is_worker() and unit.can_act():
        # we want to mine only if there is space left in the worker's cargo
        if unit.get_cargo_space_left() > 0:
            # find the closest resource if it exists to this unit
            closest_resource_tile = find_closest_resources(unit.pos, player, resource_tiles)
            if closest_resource_tile is not None and closest_resource_tile.pos != unit.pos:
                # create a move action to move this unit in the direction of the closest resource tile and add to our actions list
                # TODO: Make sure two workers do not move onto the same time
                pos_to_check = {}
                for direction in ALL_DIRECTIONS:
                    new_pos = unit.pos.translate(direction, 1)
                    if not game_state.map.is_within_bounds(new_pos) or new_pos in pos_units_will_move_to:
                        continue
                    pos_to_check[direction] = new_pos
                dir_to_move = unit.pos.direction_to(closest_resource_tile.pos, pos_to_check=pos_to_check)
                if dir_to_move != DIRECTIONS.CENTER:
                    return 'move', dir_to_move, unit.pos.translate(dir_to_move, 1)
        else:
            new_city = city_tile_to_build(LogicGlobals.main_base_city_tile.pos, player, game_state)
            if new_city is not None:
                # print(f"New city is at:", new_city.pos, file=sys.stderr)
                if unit.pos != new_city.pos:
                    pos_to_check = {}
                    for direction in ALL_DIRECTIONS:
                        new_pos = unit.pos.translate(direction, 1)
                        if not game_state.map.is_within_bounds(new_pos):
                            continue
                        new_pos_cell = game_state.map.get_cell_by_pos(new_pos)
                        if new_pos_cell.citytile is None:
                            pos_to_check[direction] = new_pos
                    dir_to_move = unit.pos.direction_to(new_city.pos, pos_to_check=pos_to_check)
                    return 'move', dir_to_move, unit.pos.translate(dir_to_move, 1)
                else:
                    return 'build', None, unit.pos
            else:
                # find the closest citytile and move the unit towards it to drop resources to a citytile to fuel the city
                closest_city_tile = find_closest_city_tile(unit.pos, player)
                if closest_city_tile is not None:
                    dir_to_move = unit.pos.direction_to(closest_city_tile.pos)
                    # create a move action to move this unit in the direction of the closest resource tile and add to our actions list
                    return 'move', dir_to_move, unit.pos.translate(dir_to_move, 1)
    return None, None, None


class LogicGlobals:
    game_state = Game()
    main_base_city_tile = None
    clusters = None


def agent(observation, configuration):
    # global game_state, main_base_city_tile

    ### Do not edit ###
    if observation["step"] == 0:
        # LogicGlobals.game_state = Game()
        LogicGlobals.game_state._initialize(observation["updates"])
        LogicGlobals.game_state._update(observation["updates"][2:])
        LogicGlobals.game_state.id = observation.player
    else:
        LogicGlobals.game_state._update(observation["updates"])

    if LogicGlobals.game_state.turn == 0:
        LogicGlobals.clusters = find_clusters(LogicGlobals.game_state)

    for c in LogicGlobals.clusters:
        c.update_state(game_map=LogicGlobals.game_state.map)

    ### AI Code goes down here! ###
    player = LogicGlobals.game_state.players[observation.player]
    opponent = LogicGlobals.game_state.players[(observation.player + 1) % 2]
    width, height = LogicGlobals.game_state.map.width, LogicGlobals.game_state.map.height

    if LogicGlobals.main_base_city_tile is None:
        LogicGlobals.main_base_city_tile = find_closest_city_tile(Position(0, 0), player)
    # if main_base_city_tile is not None:
    #     print(f"Base city is at:", main_base_city_tile.pos, file=sys.stderr)

    resource_tiles = find_resources(LogicGlobals.game_state)
    actions = []
    # pos_units_will_move_to = set(unit.pos for unit in player.units)
    proposed_unit_locations = {}

    for unit in player.units:
        action, direction, new_pos = decide_unit_action(
            unit, player, LogicGlobals.game_state, resource_tiles, set(v[1] for v in proposed_unit_locations.values())
        )
        if action == 'move':
            proposed_unit_locations[unit.id] = (direction, new_pos)
        elif action == 'build':
            actions.append(unit.build_city())

    duplicate_pos = set(pos for pos, count in Counter(proposed_unit_locations.values()).items() if count > 1) - set(city_tile.pos for city in player.cities.values() for city_tile in city.citytiles)
    fixed_pos = {}
    for unit_id, (direction, pos) in proposed_unit_locations.items():
        unit = [u for u in player.units if u.id == unit_id][0]
        if pos in duplicate_pos and pos in fixed_pos:
            action, direction, new_pos = decide_unit_action(
                unit, player, LogicGlobals.game_state, resource_tiles, set(v[1] for v in proposed_unit_locations.values())
            )
            if action == 'move':
                actions.append(unit.move(direction))
            elif action == 'build':
                actions.append(unit.build_city())
        else:
            actions.append(unit.move(direction))

    for _, city in player.cities.items():
        for city_tile in city.citytiles:
            if city_tile.can_act():
                if len(player.units) < player.city_tile_count:
                    actions.append(city_tile.build_worker())
                else:
                    actions.append(city_tile.research())

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
        for pos in cluster.resource_positions:
            actions.append(annotate.circle(pos.x, pos.y))
        for pos in cluster.pos_to_defend:
            if pos.x == 19 and pos.y == 4:
                print("FOUND A CLUSTER WITH WEIRD POSITION", file=sys.stderr)
            actions.append(annotate.x(pos.x, pos.y))

    actions.append(annotate.text(15, 15, "Some message to convey"))

    return actions




