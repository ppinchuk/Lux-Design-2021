from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, DIRECTIONS, Position
from lux.constants import Constants, ALL_DIRECTIONS, ALL_DIRECTIONS_AND_CENTER
from collections import Counter
import sys
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import math

### Define helper functions


def city_tile_to_build(pos, player, game_state):
    if pos is None or player.city_tile_count >= 5:
        return None
    for dir in [DIRECTIONS.CENTER] + ALL_DIRECTIONS:
        cell = game_state.map.get_cell_by_pos(pos.translate(dir, 1))
    # for x_add, y_add in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
    #     cell = game_state.map.get_cell(pos.x+x_add, pos.y+y_add)
        if not cell.has_resource() and cell.citytile is None:
            return cell
    return None


# this snippet finds all resources stored on the map and puts them into a list so we can search over them
def find_resources(game_state):
    resource_tiles: list[Cell] = []
    width, height = game_state.map_width, game_state.map_height
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
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


game_state = None
main_base_city_tile = None


def decide_unit_action(unit, player, resource_tiles, pos_units_will_move_to):
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
            new_city = city_tile_to_build(main_base_city_tile.pos, player, game_state)
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


def agent(observation, configuration):
    global game_state, main_base_city_tile

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])

    ### AI Code goes down here! ###
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height

    if main_base_city_tile is None:
        main_base_city_tile = find_closest_city_tile(Position(0, 0), player)
    # print(f"Base city is:", main_base_city_tile, file=sys.stderr)
    # if main_base_city_tile is not None:
    #     print(f"Base city is at:", main_base_city_tile.pos, file=sys.stderr)

    resource_tiles = find_resources(game_state)
    actions = []
    # pos_units_will_move_to = set(unit.pos for unit in player.units)
    proposed_unit_locations = {}

    for unit in player.units:
        action, direction, new_pos = decide_unit_action(
            unit, player, resource_tiles, set(v[1] for v in proposed_unit_locations.values())
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
                unit, player, resource_tiles, set(v[1] for v in proposed_unit_locations.values())
            )
            if action == 'move':
                actions.append(unit.move(direction))
            elif action == 'build':
                actions.append(unit.build_city())
        else:
            actions.append(unit.move(direction))


        # # if the unit is a worker (can mine resources) and can perform an action this turn
        # if unit.is_worker() and unit.can_act():
        #     # we want to mine only if there is space left in the worker's cargo
        #     if unit.get_cargo_space_left() > 0:
        #         # find the closest resource if it exists to this unit
        #         closest_resource_tile = find_closest_resources(unit.pos, player, resource_tiles)
        #         if closest_resource_tile is not None and closest_resource_tile.pos != unit.pos:
        #             # create a move action to move this unit in the direction of the closest resource tile and add to our actions list
        #             # TODO: Make sure two workers do not move onto the same time
        #             pos_to_check = {}
        #             for direction in ALL_DIRECTIONS:
        #                 new_pos = unit.pos.translate(direction, 1)
        #                 if not game_state.map.is_within_bounds(new_pos) or new_pos in pos_units_will_move_to:
        #                     continue
        #                 pos_to_check[direction] = new_pos
        #             dir_to_move = unit.pos.direction_to(closest_resource_tile.pos, pos_to_check=pos_to_check)
        #             if dir_to_move != DIRECTIONS.CENTER:
        #                 pos_units_will_move_to.add(pos_to_check[dir_to_move])
        #                 actions.append(unit.move(dir_to_move))
        #     else:
        #         new_city = city_tile_to_build(main_base_city_tile.pos, player, game_state)
        #         if new_city is not None:
        #             # print(f"New city is at:", new_city.pos, file=sys.stderr)
        #             if unit.pos != new_city.pos:
        #                 pos_to_check = {}
        #                 for direction in ALL_DIRECTIONS:
        #                     new_pos = unit.pos.translate(direction, 1)
        #                     if not game_state.map.is_within_bounds(new_pos):
        #                         continue
        #                     new_pos_cell = game_state.map.get_cell_by_pos(new_pos)
        #                     if new_pos_cell.citytile is None:
        #                         pos_to_check[direction] = new_pos
        #                 actions.append(unit.move(unit.pos.direction_to(new_city.pos, pos_to_check=pos_to_check)))
        #             else:
        #                 actions.append(unit.build_city())
        #         else:
        #             # find the closest citytile and move the unit towards it to drop resources to a citytile to fuel the city
        #             closest_city_tile = find_closest_city_tile(unit.pos, player)
        #             if closest_city_tile is not None:
        #                 # create a move action to move this unit in the direction of the closest resource tile and add to our actions list
        #                 actions.append(unit.move(unit.pos.direction_to(closest_city_tile.pos)))

    for _, city in player.cities.items():
        for city_tile in city.citytiles:
            if city_tile.can_act():
                if len(player.units) < player.city_tile_count:
                    actions.append(city_tile.build_worker())
                else:
                    actions.append(city_tile.research())

    return actions




