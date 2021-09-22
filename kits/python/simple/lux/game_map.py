from typing import List
import math
import sys
import statistics
from random import shuffle

from .constants import Constants, ALL_DIRECTIONS

DIRECTIONS = Constants.DIRECTIONS
WOOD = Constants.RESOURCE_TYPES.WOOD
COAL = Constants.RESOURCE_TYPES.COAL
URANIUM = Constants.RESOURCE_TYPES.URANIUM

MAX_DISTANCE_FROM_EDGE = 2


class Resource:
    def __init__(self, r_type: str, amount: int):
        self.type = r_type
        self.amount = amount


class ResourceCluster:
    def __init__(self, r_type: str, positions):
        self.type = r_type
        self._resource_positions = dict()
        self.total_amount = -1
        self.pos_to_defend = []
        self.pos_defended = []
        self.min_loc = None
        self.max_loc = None
        self.center_pos = None
        self.current_score = 0
        self.n_workers_spawned = 0
        self.n_workers_sent_to_colonize = 0

        for pos in positions:
            self._resource_positions[pos] = None
        self._hash = hash(tuple(self._resource_positions.keys()))

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
            cell.resource.amount for cell in cells # if cell.resource is not None
        ) if cells else 0

        if not cells:
            self._resource_positions = dict()
            self.pos_to_defend = []
        elif not self.pos_to_defend or len(cells) != len(self._resource_positions):
            self._resource_positions = dict()
            for cell in cells:
                self._resource_positions[cell.pos] = None

            x_vals = [p.x for p in self._resource_positions.keys()]
            y_vals = [p.y for p in self._resource_positions.keys()]

            self.min_loc = (min(x_vals), min(y_vals))
            self.max_loc = (max(x_vals), max(y_vals))
            self.center_pos = Position(
                (self.max_loc[0] - self.min_loc[0]) // 2 + self.min_loc[0],
                (self.max_loc[1] - self.min_loc[1]) // 2 + self.min_loc[1],
            )
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

            print(f"Num to block: {self.n_to_block}", file=sys.stderr)

            opponent_x_vals, opponent_y_vals = [], []
            for unit in opponent.units:
                opponent_x_vals.append(unit.pos.x)
                opponent_y_vals.append(unit.pos.y)
            for p in opponent.city_pos:
                opponent_x_vals.append(p.x)
                opponent_y_vals.append(p.y)
            opponent_med_pos = Position(
                statistics.median(opponent_x_vals),
                statistics.median(opponent_y_vals),
            )
            self.pos_to_defend = sorted(
                self.pos_to_defend, key=opponent_med_pos.distance_to
            )

        for x in range(self.min_loc[0], self.max_loc[0] + 1):
            for y in range(self.min_loc[1], self.max_loc[1] + 1):
                if game_map.get_cell(x, y).citytile is not None:
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

    def has_resource(self, do_wood_check=False):
        if do_wood_check:
            return self.resource is not None and ((self.resource.type != WOOD and self.resource.amount > 0) or (self.resource.type == WOOD and self.resource.amount >= 500))
        else:
            return self.resource is not None and self.resource.amount > 0

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

    def __del__(self):
        MAP_CACHE['map'] = {
            key: self.__dict__[key]
            for key in [
                'resource_clusters',
            ]
        }

    def get_cell_by_pos(self, pos) -> Cell:
        return self.map[pos.y][pos.x]

    def get_cell(self, x, y) -> Cell:
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

    def num_adjacent_resources(self, pos, include_center=True, do_wood_check=False):
        return sum(
            self.get_cell_by_pos(p).has_resource(do_wood_check=do_wood_check)
            for p in pos.adjacent_positions(include_center=include_center)
            if self.is_within_bounds(p)
        )

    def adjacent_resource_types(self, pos, include_center=True):
        return set(
            self.get_cell_by_pos(p).resource.type
            for p in pos.adjacent_positions(include_center=include_center)
            if self.is_within_bounds(p) and self.get_cell_by_pos(p).has_resource(do_wood_check=True)
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

        return self.resource_clusters

    def update_clusters(self, opponent):
        clusters_to_discard = set()
        for cluster in self.resource_clusters:
            cluster.update_state(
                game_map=self, opponent=opponent
            )
            if cluster.total_amount <= 0:
                clusters_to_discard.add(cluster)
        self.resource_clusters = self.resource_clusters - clusters_to_discard

    def position_to_cluster(self, pos):
        if not self.resource_clusters:
            print("No clusters found!", file=sys.stderr)
            return None
        for cluster in self.resource_clusters:
            if (cluster.min_loc[0] - 1 <= pos.x <= cluster.max_loc[0] + 1) and (
                    cluster.min_loc[1] - 1 <= pos.y <= cluster.max_loc[1] + 1):
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
            WOOD: None,
            COAL: None,
            URANIUM: None,
        }
        self._closest_city_pos = None

    def __sub__(self, pos) -> int:
        return abs(pos.x - self.x) + abs(pos.y - self.y)

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

    def adjacent_positions(self, include_center=True):
        adjacent_positions = {
            self.translate(DIRECTIONS.NORTH, 1),
            self.translate(DIRECTIONS.EAST, 1),
            self.translate(DIRECTIONS.SOUTH, 1),
            self.translate(DIRECTIONS.WEST, 1),
        }
        if include_center:
            adjacent_positions.add(self)
        return adjacent_positions

    def equals(self, pos):
        return self == pos

    def shift_by(self, x, y) -> 'Position':
        return Position(self.x + x, self.y + y)

    def translate(self, direction, units) -> 'Position':
        if direction == DIRECTIONS.NORTH:
            return Position(self.x, self.y - units)
        elif direction == DIRECTIONS.EAST:
            return Position(self.x + units, self.y)
        elif direction == DIRECTIONS.SOUTH:
            return Position(self.x, self.y + units)
        elif direction == DIRECTIONS.WEST:
            return Position(self.x - units, self.y)
        elif direction == DIRECTIONS.CENTER:
            return Position(self.x, self.y)

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

    def _find_closest_resource(self, resources_to_consider, game_map):

        for resource in resources_to_consider:
            if self._closest_resource_pos[resource] is None or not game_map.get_cell_by_pos(self._closest_resource_pos[resource]).has_resource():
                closest_dist = math.inf
                for resource_tile in game_map.resources():
                    if resource_tile.resource.type != resource:
                        continue
                    dist = resource_tile.pos.distance_to(self)
                    if dist < closest_dist:
                        closest_dist = dist
                        self._closest_resource_pos[resource] = resource_tile.pos
        if resources_to_consider:
            return min(
                [self._closest_resource_pos[r] for r in resources_to_consider],
                key=self.distance_to
            )
        else:
            return None

    def find_closest_wood(self, game_map):
        """ Find the closest wood to this position.

        Parameters
        ----------
        game_map : :GameMap:
            Map containing position and resources.

        Returns
        -------
        Position
            Position of closest resource.

        """
        return self._find_closest_resource([WOOD], game_map)

    def find_closest_resource(self, player, game_map, prefer_unlocked_resources=False):
        """ Find the closest resource to this position.

        Parameters
        ----------
        player : Player object
            Player wanting to find the closest resource.
            Used to determine if player can mind coal or uranium.
        game_map : :GameMap:
            Map containing position and resources.
        prefer_unlocked_resources : bool, optional
            Option to prefer the most fuel-efficient resources,
            if they are unlocked.

        Returns
        -------
        Position
            Position of closest resource.

        """

        if prefer_unlocked_resources:
            if player.researched_uranium():
                resources_to_consider = [URANIUM]
            elif player.researched_coal():
                resources_to_consider = [COAL]
            else:
                resources_to_consider = [WOOD]
        else:
            resources_to_consider = [WOOD]
            if player.researched_coal():
                resources_to_consider.append(COAL)
            if player.researched_uranium:
                resources_to_consider.append(COAL)

        return self._find_closest_resource(resources_to_consider, game_map)

    def direction_to(self, target_pos: 'Position', pos_to_check=None, do_shuffle=True) -> DIRECTIONS:
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
            return DIRECTIONS.CENTER

        if pos_to_check is None:
            pos_to_check = {
                direction: self.translate(direction, 1)
                for direction in ALL_DIRECTIONS
            }

        dir_pos = list(pos_to_check.items())
        if do_shuffle:
            shuffle(dir_pos)

        dists = {d: target_pos.distance_to(p) for d, p in dir_pos}
        return min(dists, key=dists.get)

    def __repr__(self) -> str:
        return f"({self.x}, {self.y})"
