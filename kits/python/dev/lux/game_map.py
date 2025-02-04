from typing import List
import math
import sys
from functools import partial
from random import shuffle
import getpass

from .constants import ALL_DIRECTIONS, print, log, STRATEGY_HYPERPARAMETERS, ResourceTypes, Directions, LogicGlobals, StrategyTypes, INFINITE_DISTANCE, GAME_CONSTANTS, ValidActions, is_turn_during_night


MAX_DISTANCE_FROM_EDGE = STRATEGY_HYPERPARAMETERS['MAX_DISTANCE_FROM_EDGE']


class Resource:
    def __init__(self, r_type: str, amount: int):
        self.type = r_type
        self.amount = amount

    @property
    def fuel_amount(self):
        return GAME_CONSTANTS['PARAMETERS']['RESOURCE_TO_FUEL_RATE'][self.type.upper()] * self.amount

    @property
    def can_harvest(self):
        if self.type.upper() == ResourceTypes.WOOD:
            return  True
        if self.type.upper() == ResourceTypes.COAL and LogicGlobals.player.researched_coal():
            return True
        if self.type.upper() == ResourceTypes.URANIUM and LogicGlobals.player.researched_uranium():
            return True
        return False


class ResourceCluster:
    def __init__(self, r_type: str, positions):
        self.type = r_type
        self._resource_positions = dict()
        self.total_amount = -1
        self.pos_to_defend = []
        self.pos_defended = []
        self.pos_defended_by_player = []
        self.min_loc = None
        self.max_loc = None
        self.center_pos = None
        self.current_score = 0
        self.n_workers_spawned = 0
        self.n_workers_sent_to_colonize = 0
        self.city_ids = set()
        self.sort_position = None
        self.needs_defending_from_opponent = False
        self.cart_id = None

        for pos in positions:
            self._resource_positions[pos] = None
        self.id = self._hash = hash(tuple(self._resource_positions.keys()))

    def __repr__(self) -> str:
        return f"ResourceCluster({self.type}, {self.center_pos}, {self.id})"

    def __eq__(self, other) -> bool:
        return self.resource_positions == other.resource_positions

    def __hash__(self):
        return self._hash

    def calculate_score(self, player, opponent, scaling_factor=1):
        # From list 'L' of clusters with type (wood, coal, uranium) and number of resources in cluster:
        # 1.) Iterate through 'L'  and compare type to number of research points and if compatible, add the number of resources of cluster to list 'K'
        # 2.) Reorder 'K' by number of resources
        # 3.) Divide all by value of first item
        # 4.) If cluster has any cities formed then divide by number of cities - 1 otherwise
        # 5.) Divide by distance to OUR nearest city outside of cluster
        # 6.) Multiply by distance to nearest opponent city or worker
        # 7.) Send worker to cluster with highest value

        self.current_score = self.total_amount / scaling_factor
        self.current_score /= max(1, len(self.pos_defended))
        self.current_score /= min(
            [1]
            +
            [self.center_pos.distance_to(pos) for pos in player.city_pos]
        )
        self.current_score *= min(
            [1]
            +
            [self.center_pos.distance_to(pos) for pos in opponent.city_pos]
            +
            [self.center_pos.distance_to(unit.pos) for unit in opponent.units]
        )
        return self.current_score

    def _set_research_based_pos_to_defend(self, game_map):
        self.pos_to_defend = set()
        if self.id in LogicGlobals.clusters_to_colonize_rbs:
            for x in range(self.min_loc[0] - 1, self.max_loc[0] + 2):
                for y in range(self.min_loc[1] - 1, self.max_loc[1] + 2):
                    if game_map.is_loc_within_bounds(x, y):
                        if game_map.get_cell(x, y).is_empty():
                            self.pos_to_defend.add(Position(x, y))

    def _set_smart_positions(self, game_map):
        self.pos_to_defend = set()
        if self.min_loc[1] < MAX_DISTANCE_FROM_EDGE:
            if self.min_loc[0] >= MAX_DISTANCE_FROM_EDGE:
                self.pos_to_defend = self.pos_to_defend | {
                    Position(self.min_loc[0] - 1, y)
                    for y in range(0, self.min_loc[1] + 1)
                    if game_map.is_loc_within_bounds(self.min_loc[0] - 1, y)
                }
            if self.max_loc[0] < game_map.width - MAX_DISTANCE_FROM_EDGE:
                self.pos_to_defend = self.pos_to_defend | {
                    Position(self.max_loc[0] + 1, y)
                    for y in range(0, self.min_loc[1] + 1)
                    if game_map.is_loc_within_bounds(self.max_loc[0] + 1, y)
                }
        else:
            self.pos_to_defend = self.pos_to_defend | {
                Position(x, self.min_loc[1] - 1)
                for x in range(self.min_loc[0], self.max_loc[0] + 1)
                if game_map.is_loc_within_bounds(x, self.min_loc[1] - 1)
            }

        if self.max_loc[1] > game_map.height - MAX_DISTANCE_FROM_EDGE - 1:
            if self.min_loc[0] >= MAX_DISTANCE_FROM_EDGE:
                self.pos_to_defend = self.pos_to_defend | {
                    Position(self.min_loc[0] - 1, y)
                    for y in range(self.max_loc[1], game_map.height)
                    if game_map.is_loc_within_bounds(self.min_loc[0] - 1, y)
                }
            if self.max_loc[0] < game_map.width - MAX_DISTANCE_FROM_EDGE:
                self.pos_to_defend = self.pos_to_defend | {
                    Position(self.max_loc[0] + 1, y)
                    for y in range(self.max_loc[1], game_map.height)
                    if game_map.is_loc_within_bounds(self.max_loc[0] + 1, y)
                }
        else:
            self.pos_to_defend = self.pos_to_defend | {
                Position(x, self.max_loc[1] + 1)
                for x in range(self.min_loc[0], self.max_loc[0] + 1)
                if game_map.is_loc_within_bounds(x, self.max_loc[1] + 1)
            }

        if self.min_loc[0] < MAX_DISTANCE_FROM_EDGE:
            if self.min_loc[1] >= MAX_DISTANCE_FROM_EDGE:
                self.pos_to_defend = self.pos_to_defend | {
                    Position(x, self.min_loc[1] - 1)
                    for x in range(0, self.min_loc[0] + 1)
                    if game_map.is_loc_within_bounds(x, self.min_loc[1] - 1)
                }
            if self.max_loc[1] < game_map.height - MAX_DISTANCE_FROM_EDGE:
                self.pos_to_defend = self.pos_to_defend | {
                    Position(x, self.max_loc[1] + 1)
                    for x in range(0, self.min_loc[0] + 1)
                    if game_map.is_loc_within_bounds(x, self.max_loc[1] + 1)
                }
        else:
            self.pos_to_defend = self.pos_to_defend | {
                Position(self.min_loc[0] - 1, y)
                for y in range(self.min_loc[1], self.max_loc[1] + 1)
                if game_map.is_loc_within_bounds(self.min_loc[0] - 1, y)
            }

        if self.max_loc[0] > game_map.width - MAX_DISTANCE_FROM_EDGE - 1:
            if self.min_loc[1] >= MAX_DISTANCE_FROM_EDGE:
                self.pos_to_defend = self.pos_to_defend | {
                    Position(x, self.min_loc[1] - 1)
                    for x in range(self.max_loc[0], game_map.width)
                    if game_map.is_loc_within_bounds(x, self.min_loc[1] - 1)
                }
            if self.max_loc[1] < game_map.height - MAX_DISTANCE_FROM_EDGE:
                self.pos_to_defend = self.pos_to_defend | {
                    Position(x, self.max_loc[1] + 1)
                    for x in range(self.max_loc[0], game_map.width)
                    if game_map.is_loc_within_bounds(x, self.max_loc[1] + 1)
                }
        else:
            self.pos_to_defend = self.pos_to_defend | {
                Position(self.max_loc[0] + 1, y)
                for y in range(self.min_loc[1], self.max_loc[1] + 1)
                if game_map.is_loc_within_bounds(self.max_loc[0] + 1, y)
            }

        p = Position(self.min_loc[0] - 1, self.min_loc[1] - 1)
        if game_map.is_within_bounds(p) and p.distance_to(Position(0, 0)) > MAX_DISTANCE_FROM_EDGE:
            self.pos_to_defend.add(p)

        p = Position(self.min_loc[0] - 1, self.max_loc[1] + 1)
        if game_map.is_within_bounds(p) and p.distance_to(Position(0, game_map.height - 1)) > MAX_DISTANCE_FROM_EDGE:
            self.pos_to_defend.add(p)

        p = Position(self.max_loc[0] + 1, self.min_loc[1] - 1)
        if game_map.is_within_bounds(p) and p.distance_to(Position(game_map.width - 1, 0)) > MAX_DISTANCE_FROM_EDGE:
            self.pos_to_defend.add(p)

        p = Position(self.max_loc[0] + 1, self.max_loc[1] + 1)
        if game_map.is_within_bounds(p) and p.distance_to(
                Position(game_map.width - 1, game_map.height - 1)) > MAX_DISTANCE_FROM_EDGE:
            self.pos_to_defend.add(p)

    def _set_basic_positions(self, game_map):
        self.pos_to_defend = set()
        for r_pos in self._resource_positions:
            for pos in r_pos.adjacent_positions(include_center=True, include_diagonals=True):
                if game_map.is_within_bounds(pos) and not game_map.get_cell_by_pos(pos).has_resource():
                    self.pos_to_defend.add(pos)

    def update_state(self, game_map, opponent):
        cells = {
            game_map.get_cell_by_pos(p)
            for p in self._resource_positions.keys()
            if game_map.is_within_bounds(p)
        }

        cells = {
            c for c in cells if c.resource is not None
        }

        self.total_amount = sum(
            cell.resource.amount for cell in cells  # if cell.resource is not None
        ) if cells else 0

        x_vals = [p.x for p in self._resource_positions.keys()]
        y_vals = [p.y for p in self._resource_positions.keys()]

        self.min_loc = (min(x_vals), min(y_vals))
        self.max_loc = (max(x_vals), max(y_vals))
        self.center_pos = Position(
            (self.max_loc[0] - self.min_loc[0]) // 2 + self.min_loc[0],
            (self.max_loc[1] - self.min_loc[1]) // 2 + self.min_loc[1],
        )
        self._set_basic_positions(game_map)

        # if LogicGlobals.player.current_strategy == StrategyTypes.RESEARCH_BASED:
        #     self._set_research_based_pos_to_defend(game_map)
        # else:
        #     if not cells:
        #         self._resource_positions = dict()
        #     elif not self.pos_to_defend or len(cells) != len(self._resource_positions):
        #
        #         self._resource_positions = dict()
        #         for cell in cells:
        #             self._resource_positions[cell.pos] = None
        #
        #         x_vals = [p.x for p in self._resource_positions.keys()]
        #         y_vals = [p.y for p in self._resource_positions.keys()]
        #
        #         self.min_loc = (min(x_vals), min(y_vals))
        #         self.max_loc = (max(x_vals), max(y_vals))
        #         self.center_pos = Position(
        #             (self.max_loc[0] - self.min_loc[0]) // 2 + self.min_loc[0],
        #             (self.max_loc[1] - self.min_loc[1]) // 2 + self.min_loc[1],
        #         )
        #
        #         # self._set_smart_positions(game_map)
        #         self._set_basic_positions(game_map)
        #
        #     log(f"Num to block for cluster at {self.center_pos}: {self.n_to_block}")
        #
        #
        #     # opponent_x_vals, opponent_y_vals = [], []
        #     # for unit in opponent.units:
        #     #     opponent_x_vals.append(unit.pos.x)
        #     #     opponent_y_vals.append(unit.pos.y)
        #     # for p in opponent.city_pos:
        #     #     opponent_x_vals.append(p.x)
        #     #     opponent_y_vals.append(p.y)
        #     # opponent_med_pos = Position(
        #     #     statistics.median(opponent_x_vals),
        #     #     statistics.median(opponent_y_vals),
        #     # )
        #     # self.pos_to_defend = sorted(
        #     #     self.pos_to_defend, key=opponent_med_pos.distance_to
        #     # )
        #
        #
        if self.sort_position is None:
            opponent_positions = opponent.city_pos | opponent.unit_pos
            if opponent_positions and (not opponent_positions & self.pos_to_defend):
                # closest_opponent_pos = min(
                #     opponent_positions,
                #     key=lambda p: (self.center_pos.distance_to(p), LogicGlobals.x_mult * p.x, LogicGlobals.y_mult * p.y)
                # )
                closest_opponent_pos = min(
                    opponent_positions,
                    key=lambda p: (self.center_pos.tile_distance_to(p, positions_to_avoid=self.resource_positions), LogicGlobals.x_mult * p.x, LogicGlobals.y_mult * p.y)
                )
            else:
                to_search_pos = LogicGlobals.player.city_pos | LogicGlobals.player.unit_pos
                if not to_search_pos:
                    to_search_pos = {Position(0, 0)}
                closest_opponent_pos = min(
                    to_search_pos,
                    key=lambda p: (self.center_pos.tile_distance_to(p, positions_to_avoid=self.resource_positions), LogicGlobals.x_mult * p.x, LogicGlobals.y_mult * p.y)
                )
        else:
            closest_opponent_pos = self.sort_position

        # self.pos_to_defend = sorted(
        #     self.pos_to_defend, key=lambda p: (closest_opponent_pos.distance_to(p), LogicGlobals.x_mult * p.x, LogicGlobals.y_mult * p.y)
        # )
        self.pos_to_defend = sorted(
            self.pos_to_defend, key=lambda p: (closest_opponent_pos.tile_distance_to(p, positions_to_avoid=self.resource_positions), LogicGlobals.x_mult * p.x, LogicGlobals.y_mult * p.y)
        )

        if LogicGlobals.opponent.units:
            distance_to_closest_enemy = {
                p: (min(p.distance_to(u.pos) for u in LogicGlobals.opponent.units), -min(p.distance_to(u.pos) for u in LogicGlobals.player.units) if LogicGlobals.player.units else 0, LogicGlobals.x_mult * p.x, LogicGlobals.y_mult * p.y)
                for p in self.pos_to_defend
            }
            pos_closest_to_enemy = min(
                distance_to_closest_enemy,
                key=distance_to_closest_enemy.get
            )

            opponent_distance, player_distance, *__ = distance_to_closest_enemy[pos_closest_to_enemy]
            self.needs_defending_from_opponent = -player_distance + 1 >= opponent_distance
        else:
            self.needs_defending_from_opponent = False

        # print(f"Resource cluster at {self.center_pos} needs defending: {self.needs_defending_from_opponent}")

        self.city_ids = set()
        self.pos_defended = []
        self.pos_defended_by_player = set()
        for x in range(self.min_loc[0]-1, self.max_loc[0] + 2):
            for y in range(self.min_loc[1]-1, self.max_loc[1] + 2):
                if game_map.is_loc_within_bounds(x, y):
                    city_tile = game_map.get_cell(x, y).citytile
                    if city_tile is not None:
                        if city_tile.cityid in LogicGlobals.player.city_ids:
                            self.city_ids.add(city_tile.cityid)
                            self.pos_defended_by_player.add(city_tile.pos)
                        self.pos_defended.append(Position(x, y))

    @property
    def n_to_block(self):
        return len(self.pos_to_defend)

    @property
    def n_defended(self):
        return len(self.pos_defended)

    @property
    def resource_positions(self):
        return set(self._resource_positions.keys())


class Cell:
    def __init__(self, x, y):
        self.pos = Position(x, y)
        self.resource: Resource = None
        self.citytile = None
        self.road = 0

    def has_resource(self, include_wood_that_is_growing=True, min_amt=0):
        if include_wood_that_is_growing:
            return self.resource is not None and self.resource.amount > min_amt
        else:
            return self.resource is not None and ((self.resource.type != ResourceTypes.WOOD and self.resource.amount > min_amt) or (self.resource.type == ResourceTypes.WOOD and self.resource.amount >= GAME_CONSTANTS["PARAMETERS"]["MAX_WOOD_AMOUNT"]))

    def is_empty(self):
        return self.citytile is None and not self.has_resource()


MAP_CACHE = {}


class GameMap:
    def __init__(self, width, height):
        self.height = height
        self.width = width
        self.map: List[List[Cell]] = [None] * height
        self._resources = []
        self.resource_clusters = None
        for y in range(0, self.height):
            self.map[y] = [None] * width
            for x in range(0, self.width):
                self.map[y][x] = Cell(x, y)

        self.__dict__.update(MAP_CACHE.get('map', {}))

    def save_state(self):
        MAP_CACHE['map'] = {
            key: self.__dict__[key]
            for key in [
                'resource_clusters',
            ]
        }

    def get_cell_by_pos(self, pos):
        if not self.is_within_bounds(pos):
            return None
        return self.map[pos.y][pos.x]

    def get_cell(self, x, y):
        if not self.is_loc_within_bounds(x, y):
            return None
        return self.map[y][x]

    def is_loc_within_bounds(self, x, y):
        return (0 <= x < self.height) and (0 <= y < self.width)

    def is_within_bounds(self, pos):
        return self.is_loc_within_bounds(pos.x, pos.y)

    def _setResource(self, r_type, x, y, amount):
        """
        do not use this function, this is for internal tracking of state
        """
        cell = self.get_cell(x, y)
        cell.resource = Resource(r_type, amount)

    def max_collectors_allowed_at(self, pos):
        return sum(
            self.is_within_bounds(p) and self.get_cell_by_pos(pos).citytile is None
            for p in pos.adjacent_positions(include_center=False, include_diagonals=False)
        )

    def num_adjacent_resources(self, pos, include_center=True, include_wood_that_is_growing=True, check_for_unlock=False):
        return sum(
            self.get_cell_by_pos(p).has_resource(include_wood_that_is_growing=include_wood_that_is_growing) and (self.get_cell_by_pos(p).resource.can_harvest if check_for_unlock else True)
            for p in pos.adjacent_positions(include_center=include_center)
            if self.is_within_bounds(p)
        )

    def adjacent_resource_types(self, pos, include_center=True):
        return set(
            self.get_cell_by_pos(p).resource.type
            for p in pos.adjacent_positions(include_center=include_center)
            if self.is_within_bounds(p) and self.get_cell_by_pos(p).has_resource(include_wood_that_is_growing=True)
        )

    def resources(self, return_positions_only=False):
        if not self._resources:
            self._resources = [
                cell.pos if return_positions_only else cell
                for cell in self.cells()
                if cell.has_resource()
            ]
        return self._resources

    def _check_for_cluster(self, position, resource_set, resource_type):
        for step in ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)):
            new_position = position.shift_by(*step)
            if self.is_within_bounds(new_position) and new_position not in resource_set:
                new_cell = self.get_cell_by_pos(new_position)
                if new_cell.resource is not None and new_cell.resource.type == resource_type:
                    resource_set.add(new_position)
                    self._check_for_cluster(new_position, resource_set, resource_type)

        return resource_set

    def find_clusters(self):
        resource_pos_found = set()
        self.resource_clusters = set()
        for cell in self.cells():
            if cell.has_resource() and cell.pos not in resource_pos_found:
                new_cluster_pos = self._check_for_cluster(cell.pos, {cell.pos}, cell.resource.type)
                resource_pos_found = resource_pos_found | new_cluster_pos
                new_cluster = ResourceCluster(cell.resource.type, new_cluster_pos)
                self.resource_clusters.add(new_cluster)
        self.save_state()
        return self.resource_clusters

    def update_clusters(self, opponent):
        clusters_to_discard = set()
        for cluster in self.resource_clusters:
            cluster.update_state(
                game_map=self, opponent=opponent
            )
            cluster_has_no_resources = cluster.total_amount <= 0
            cluster_has_cities = any(p in LogicGlobals.player.city_pos for p in cluster.pos_to_defend)
            if cluster_has_no_resources and not cluster_has_cities and LogicGlobals.player.current_strategy == StrategyTypes.STARTER:
                clusters_to_discard.add(cluster)
        self.resource_clusters = self.resource_clusters - clusters_to_discard
        self.save_state()

    def get_cluster_by_id(self, cluster_id):
        for c in self.resource_clusters:
            if c.id == cluster_id:
                return c

    def position_to_cluster(self, pos):
        if not self.resource_clusters:
            print("No clusters found!",)
            return None
        if pos is None:
            return None
        for cluster in self.resource_clusters:
            if (cluster.min_loc[0] - 1 <= pos.x <= cluster.max_loc[0] + 1) and (
                    cluster.min_loc[1] - 1 <= pos.y <= cluster.max_loc[1] + 1):
                return cluster
            elif pos in cluster.pos_to_defend:
                return cluster
        return None

    def positions(self):
        """ Iterate over all positions of the map. """
        for x in range(self.height):
            for y in range(self.width):
                yield Position(x, y)

    def cells(self):
        """ Iterate over all cells of the map. """
        for x in range(self.height):
            for y in range(self.width):
                yield self.get_cell(x, y)


class Position:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self._closest_resource_pos = {
            ResourceTypes.WOOD: [],
            ResourceTypes.COAL: [],
            ResourceTypes.URANIUM: [],
        }
        self._closest_city_pos = None

    def __sub__(self, pos) -> int:
        return abs(pos.x - self.x) + abs(pos.y - self.y)

    def turn_distance_to(self, pos, game_map, cooldown, avoid_own_cities=False, include_target_road=False, debug=False):
        num_turns = self.__turn_distance_to(
            pos, game_map, cooldown, avoid_own_cities=avoid_own_cities,
            include_target_road=include_target_road, debug=debug
        )

        if num_turns >= INFINITE_DISTANCE or num_turns == 0:
            return num_turns

        num_turns_to_add = 0
        num_turns_left = num_turns
        turn_number = LogicGlobals.game_state.turn
        turn_number += 1
        num_turns_left -= 1
        while num_turns_left > 0:
            if is_turn_during_night(turn_number):
                num_turns_to_add += cooldown
                turn_number += cooldown
            turn_number += cooldown
            num_turns_left -= cooldown

        return num_turns + num_turns_to_add

    def __turn_distance_to(self, pos, game_map, cooldown, avoid_own_cities=False, include_target_road=False, debug=False):
        if pos is None or not game_map.is_within_bounds(pos):
            return INFINITE_DISTANCE
        if pos == self:
            return 0
        elif (self - pos) > 10:
            return (self - pos) * cooldown
        else:
            i = 0
            if include_target_road:
                step = max(1, cooldown - game_map.get_cell_by_pos(pos).road)
            else:
                step = 1
            main_list = [(pos, step)]

            tiles_not_blocked = {self, pos}
            for p in [self, pos]:
                cell = LogicGlobals.game_state.map.get_cell_by_pos(p)
                if cell.citytile is not None:
                    city_id = cell.citytile.cityid
                    if city_id in LogicGlobals.player.cities:
                        tiles_not_blocked = tiles_not_blocked | {c.pos for c in LogicGlobals.player.cities[city_id].citytiles}

            while self not in set(x[0] for x in main_list):
                # if debug:
                #     print(main_list)
                try:
                    next_pos, step = main_list[i]
                except IndexError:
                    return INFINITE_DISTANCE
                if step >= 10 * cooldown:
                    break
                for p in next_pos.adjacent_positions(include_center=False):
                    if p == self:
                        return step

                    is_valid_to_move_to = p not in (LogicGlobals.opponent.city_pos - tiles_not_blocked)
                    tiles_blocked_by_units = {u.pos for u in LogicGlobals.player.units if (LogicGlobals.game_state.map.get_cell_by_pos(u.pos).citytile is not None and (u.current_task is not None and u.current_task[0] != ValidActions.MOVE))}
                    is_valid_to_move_to = is_valid_to_move_to and p not in (tiles_blocked_by_units - tiles_not_blocked)
                    if avoid_own_cities:
                        is_valid_to_move_to = is_valid_to_move_to and p not in (LogicGlobals.player.city_pos - tiles_not_blocked)

                    if game_map.is_within_bounds(p) and is_valid_to_move_to and p not in set(x[0] for x in main_list):
                        main_list.append((p, step + max(1, cooldown - game_map.get_cell_by_pos(p).road)))
                main_list = sorted(main_list, key=lambda x: (x[1], LogicGlobals.x_mult * x[0].x, LogicGlobals.y_mult * x[0].y))
                i += 1
            for x in main_list:
                if x[0] == self:
                    return x[1]
            return step

    def pathing_distance_to(self, pos, game_map, avoid_own_cities=False, debug=False):
        if pos is None or not game_map.is_within_bounds(pos):
            return INFINITE_DISTANCE
        if pos == self:
            return 0
        elif self - pos > 15:
            return self - pos
        else:
            i = 0
            step = 0
            main_list = [(pos, step)]

            tiles_not_blocked = {self, pos}
            for p in [self, pos]:
                cell = LogicGlobals.game_state.map.get_cell_by_pos(p)
                if cell.citytile is not None:
                    city_id = cell.citytile.cityid
                    if city_id in LogicGlobals.player.cities:
                        tiles_not_blocked = tiles_not_blocked | {c.pos for c in LogicGlobals.player.cities[city_id].citytiles}

            while self not in set(x[0] for x in main_list):
                # if debug:
                #     print(main_list)
                try:
                    next_pos, step = main_list[i]
                except IndexError:
                    return 100000
                if step >= 15:
                    break
                for p in next_pos.adjacent_positions(include_center=False):
                    if p == self:
                        return step + 1

                    is_valid_to_move_to = p not in (LogicGlobals.opponent.city_pos - tiles_not_blocked)
                    tiles_blocked_by_units = {u.pos for u in LogicGlobals.player.units if (LogicGlobals.game_state.map.get_cell_by_pos(u.pos).citytile is not None and (u.current_task is not None and u.current_task[0] != ValidActions.MOVE))}
                    is_valid_to_move_to = is_valid_to_move_to and p not in (tiles_blocked_by_units - tiles_not_blocked)
                    if avoid_own_cities:
                        is_valid_to_move_to = is_valid_to_move_to and p not in (LogicGlobals.player.city_pos - tiles_not_blocked)

                    if game_map.is_within_bounds(p) and is_valid_to_move_to and p not in set(x[0] for x in main_list):
                        main_list.append((p, step + 1))
                i += 1
            for x in main_list:
                if x[0] == self:
                    return x[1] + 1
            return step

    def tile_distance_to(self, pos, positions_to_avoid=None, debug=False):
        if pos is None or not LogicGlobals.game_state.map.is_within_bounds(pos):
            return INFINITE_DISTANCE
        if pos == self:
            return 0
        elif self - pos > 10:
            return self - pos
        else:
            i = 0
            step = 0
            main_list = [(pos, step)]

            tiles_not_blocked = {self, pos}
            for p in [self, pos]:
                cell = LogicGlobals.game_state.map.get_cell_by_pos(p)
                if cell and cell.citytile is not None:
                    city_id = cell.citytile.cityid
                    if city_id in LogicGlobals.player.cities:
                        tiles_not_blocked = tiles_not_blocked | {c.pos for c in LogicGlobals.player.cities[city_id].citytiles}

            while self not in set(x[0] for x in main_list):
                # if debug:
                #     print(main_list)
                try:
                    next_pos, step = main_list[i]
                except IndexError:
                    return 100000
                if step >= 10:
                    break
                for p in next_pos.adjacent_positions(include_center=False):
                    if p == self:
                        return step + 1

                    is_valid_to_move_to = not positions_to_avoid or p not in positions_to_avoid

                    if LogicGlobals.game_state.map.is_within_bounds(p) and is_valid_to_move_to and p not in set(x[0] for x in main_list):
                        main_list.append((p, step + 1))
                i += 1
            for x in main_list:
                if x[0] == self:
                    return x[1] + 1
            return step

    def radial_distance_to(self, pos):
        """
        Returns L2 distance to pos
        """
        return math.sqrt((self.x - pos.x) ** 2 + (self.y - pos.y) ** 2)

    def distance_to(self, pos):
        """
        Returns Manhattan (L1/grid) distance to pos
        """
        return self - pos

    def is_adjacent(self, pos):
        return (self - pos) <= 1

    def __eq__(self, pos) -> bool:
        return self.x == pos.x and self.y == pos.y

    def __hash__(self):
        return hash((self.x, self.y))

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    def __repr__(self) -> str:
        return f"Position({self.x}, {self.y})"

    def adjacent_positions(self, include_center=True, include_diagonals=False):
        adjacent_positions = {
            self.translate(Directions.NORTH, 1),
            self.translate(Directions.EAST, 1),
            self.translate(Directions.SOUTH, 1),
            self.translate(Directions.WEST, 1),
        }
        if include_center:
            adjacent_positions.add(self)
        if include_diagonals:
            adjacent_positions = adjacent_positions | {
                self.translate(Directions.NORTH, 1).translate(Directions.EAST, 1),
                self.translate(Directions.NORTH, 1).translate(Directions.WEST, 1),
                self.translate(Directions.SOUTH, 1).translate(Directions.EAST, 1),
                self.translate(Directions.SOUTH, 1).translate(Directions.WEST, 1)
            }
        return adjacent_positions

    def shift_by(self, x, y) -> 'Position':
        return Position(self.x + x, self.y + y)

    def translate(self, direction, units) -> 'Position':
        if direction == Directions.NORTH:
            return Position(self.x, self.y - units)
        elif direction == Directions.EAST:
            return Position(self.x + units, self.y)
        elif direction == Directions.SOUTH:
            return Position(self.x, self.y + units)
        elif direction == Directions.WEST:
            return Position(self.x - units, self.y)
        elif direction == Directions.CENTER:
            return Position(self.x, self.y)

    def reflect_about(self, pos):
        return Position(2 * pos.x - self.x, 2 * pos.y - self.y)

    def find_closest_city_tile(self, player, game_map):
        """ Find the closest city tile to this position.

        Parameters
        ----------
        player : Player object
            Owner of the city tiles to consider.
        game_map : :GameMap:
            Map containing position and resources.

        Returns
        -------
        Position
            Position of closest city tile.

        """

        if self._closest_city_pos is None or game_map.get_cell_by_pos(self._closest_city_pos).citytile is None:
            if len(player.cities) > 0:
                closest_dist = math.inf
                for pos in player.city_pos:
                    dist = pos.distance_to(self)
                    if dist < closest_dist:
                        closest_dist = dist
                        self._closest_city_pos = pos
            else:
                return None
        return self._closest_city_pos

    def _find_closest_resource(self, resources_to_consider, game_map, tie_breaker_func=None):

        for resource in resources_to_consider:
            if not self._closest_resource_pos[resource] or any(not game_map.get_cell_by_pos(p).has_resource() for p in self._closest_resource_pos[resource]):
                self._closest_resource_pos[resource] = []
                closest_dist = math.inf
                for resource_tile in game_map.resources():
                    if resource_tile.resource.type != resource:
                        continue
                    dist = resource_tile.pos.distance_to(self)
                    if dist <= closest_dist:
                        closest_dist = dist
                        self._closest_resource_pos[resource].append(resource_tile.pos)
        # positions = list(filter(None, [self._closest_resource_pos[r] for r in resources_to_consider]))
        positions = [p for r in resources_to_consider for p in self._closest_resource_pos[r]]
        if positions:
            if tie_breaker_func is None:
                return min(positions, key=lambda p: (self.distance_to(p), LogicGlobals.x_mult * p.x, LogicGlobals.y_mult * p.y))
            else:
                return min(positions, key=lambda p: (self.distance_to(p), tie_breaker_func(p), LogicGlobals.x_mult * p.x, LogicGlobals.y_mult * p.y))
        else:
            return None

    def _find_closest_resource_for_collecting(self, resources_to_consider, game_map, tie_breaker_func=None):
        closest_resource_pos = {}
        for resource in resources_to_consider:
            closest_resource_pos[resource] = []
            closest_dist = math.inf
            for resource_tile in game_map.resources():
                if resource_tile.resource.type != resource or len(LogicGlobals.RESOURCES_BEING_COLLECTED.get(resource_tile.pos, set())) >= LogicGlobals.game_state.map.max_collectors_allowed_at(resource_tile.pos):
                    continue
                dist = resource_tile.pos.distance_to(self)
                if dist <= closest_dist:
                    closest_dist = dist
                    closest_resource_pos[resource].append(resource_tile.pos)
        # positions = list(filter(None, [self._closest_resource_pos[r] for r in resources_to_consider]))
        positions = [p for r in resources_to_consider for p in closest_resource_pos[r]]
        if positions:
            if tie_breaker_func is None:
                return min(positions, key=lambda p: (self.distance_to(p), LogicGlobals.x_mult * p.x, LogicGlobals.y_mult * p.y))
            else:
                return min(positions, key=lambda p: (self.distance_to(p), tie_breaker_func(p), LogicGlobals.x_mult * p.x, LogicGlobals.y_mult * p.y))
        else:
            return None

    def find_closest_wood(self, game_map, tie_breaker_func=None):
        """ Find the closest wood to this position.

        Parameters
        ----------
        game_map : :GameMap:
            Map containing position and resources.
        tie_breaker_func : callable, optional
            Function used to break ties in distance to position.

        Returns
        -------
        Position
            Position of closest resource.

        """
        # return self._find_closest_resource([ResourceTypes.WOOD], game_map, tie_breaker_func=tie_breaker_func)
        return self._find_closest_resource_for_collecting([ResourceTypes.WOOD], game_map, tie_breaker_func=tie_breaker_func)

    def find_closest_resource(self, player, game_map, r_type=None, tie_breaker_func=None):
        """ Find the closest resource to this position.

        Parameters
        ----------
        player : Player object
            Player wanting to find the closest resource.
            Used to determine if player can mind coal or uranium.
        game_map : :GameMap:
            Map containing position and resources.
        r_type : Constants.RESOURCE_TYPES, optional
            Type of resource to look for. If `None`,
            all resources are considered.
        tie_breaker_func : callable, optional
            Function used to break ties in distance to position.

        Returns
        -------
        Position
            Position of closest resource.

        """

        if r_type is not None:
            resources_to_consider = [r_type]
        else:
            resources_to_consider = [ResourceTypes.WOOD]
            if player.researched_coal():
                resources_to_consider.append(ResourceTypes.COAL)
            if player.researched_uranium():
                resources_to_consider.append(ResourceTypes.URANIUM)

        return self._find_closest_resource(resources_to_consider, game_map, tie_breaker_func=tie_breaker_func)

    def find_closest_resource_for_collecting(self, player, game_map, r_type=None, tie_breaker_func=None):
        """ Find the closest resource to this position.

        Excludes positions that are already at max
        collection capacity.

        Parameters
        ----------
        player : Player object
            Player wanting to find the closest resource.
            Used to determine if player can mind coal or uranium.
        game_map : :GameMap:
            Map containing position and resources.
        r_type : Constants.RESOURCE_TYPES, optional
            Type of resource to look for. If `None`,
            all resources are considered.
        tie_breaker_func : callable, optional
            Function used to break ties in distance to position.

        Returns
        -------
        Position
            Position of closest resource.

        """

        if r_type is not None:
            resources_to_consider = [r_type]
        else:
            resources_to_consider = [ResourceTypes.WOOD]
            if player.researched_coal():
                resources_to_consider.append(ResourceTypes.COAL)
            if player.researched_uranium():
                resources_to_consider.append(ResourceTypes.URANIUM)

        return self._find_closest_resource_for_collecting(resources_to_consider, game_map, tie_breaker_func=tie_breaker_func)

    def sort_directions_by_pathing_distance(self, target_pos, game_map, pos_to_check=None, tolerance=None, avoid_own_cities=False):

        if self.distance_to(target_pos) == 0:
            return Directions.CENTER

        return self._sort_directions(
            dist_func=partial(
                target_pos.pathing_distance_to,
                avoid_own_cities=avoid_own_cities,
                game_map=game_map
            ),
            pos_to_check=pos_to_check,
            tolerance=tolerance
        )

    def sort_directions_by_turn_distance(self, target_pos, game_map, cooldown, pos_to_check=None, tolerance=None, avoid_own_cities=False):

        if self.distance_to(target_pos) == 0:
            return Directions.CENTER

        return self._sort_directions(
            dist_func=partial(
                target_pos.turn_distance_to,
                game_map=game_map,
                cooldown=cooldown,
                avoid_own_cities=avoid_own_cities,
                include_target_road=True
            ),
            secondary_dist_func=target_pos.distance_to,
            pos_to_check=pos_to_check,
            tolerance=tolerance
        )

    def _default_positions_to_check(self):
        return {
            direction: self.translate(direction, 1)
            for direction in ALL_DIRECTIONS
        }

    def _sort_directions(self, dist_func, secondary_dist_func=None, pos_to_check=None, tolerance=None):
        if pos_to_check is None:
            pos_to_check = self._default_positions_to_check()

        dir_pos = list(pos_to_check.items())
        dists = {d: (dist_func(p), secondary_dist_func(p) if secondary_dist_func is not None else 0) for d, p in dir_pos}

        if tolerance is not None:
            dists = {k: v for k, v in dists.items() if v[0] <= tolerance + min(v[0] for v in dists.values())}

        return sorted(dists, key=lambda x: (dists.get(x), x))

    def direction_to(self, target_pos: 'Position', pos_to_check=None, do_shuffle=True) -> Directions:
        """ Return closest position to target_pos from this position

        Parameters
        ----------
        target_pos : Position
            Target position to move to. Can be more than 1 unit away.
        pos_to_check : dict
            Dictionary with keys as directions and values as positions
            corresponding to a move in that direction.
        do_shuffle : bool
            Option to shuffle directions so that a random
            one is chosen when multiple have a min distance.

        Returns
        -------
        Direction
            Direction to move

        """

        if self.distance_to(target_pos) == 0:
            return Directions.CENTER

        if pos_to_check is None:
            pos_to_check = {
                direction: self.translate(direction, 1)
                for direction in ALL_DIRECTIONS
            }

        dir_pos = list(pos_to_check.items())
        if do_shuffle and getpass.getuser() != 'Paul':
            shuffle(dir_pos)

        dists = {d: target_pos.distance_to(p) for d, p in dir_pos}
        return min(dists, key=lambda x: (dists.get(x), x))
