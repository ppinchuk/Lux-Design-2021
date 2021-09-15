from typing import List
import math
import sys

from .constants import Constants, ALL_DIRECTIONS

DIRECTIONS = Constants.DIRECTIONS
RESOURCE_TYPES = Constants.RESOURCE_TYPES


class Resource:
    def __init__(self, r_type: str, amount: int):
        self.type = r_type
        self.amount = amount


class ResourceCluster:
    def __init__(self, r_type: str):
        self.type = r_type
        self._resource_positions = dict()
        self.total_amount = -1
        self.pos_to_defend = []
        self.min_loc = None
        self.max_loc = None

    def __eq__(self, other) -> bool:
        return self.resource_positions == other.resource_positions

    def __hash__(self):
        return hash(self._resource_positions.keys())

    def add_resource_positions(self, *positions):
        for pos in positions:
            self._resource_positions[pos] = None

    def update_state(self, game_map):
        cells = {
            game_map.get_cell_by_pos(p)
            for p in self._resource_positions.keys()
            if game_map.is_within_bounds(p)

        }
        self.total_amount = sum(
            cell.resource.amount for cell in cells if cell.resource is not None
        )

        if not self.pos_to_defend:
            x_vals = [p.x for p in self._resource_positions.keys()]
            y_vals = [p.y for p in self._resource_positions.keys()]

            self.min_loc = (min(x_vals), min(y_vals))
            self.max_loc = (max(x_vals), max(y_vals))

            self.pos_to_defend += [
                Position(x, self.min_loc[1] - 1)
                for x in range(self.min_loc[0], self.max_loc[0] + 1)
                if game_map.is_loc_within_bounds(x, self.min_loc[1] - 1)
            ]

            self.pos_to_defend += [
                Position(x, self.max_loc[1] + 1)
                for x in range(self.min_loc[0], self.max_loc[0] + 1)
                if game_map.is_loc_within_bounds(x, self.max_loc[1] + 1)
            ]

            self.pos_to_defend += [
                Position(self.min_loc[0] - 1, y)
                for y in range(self.min_loc[1], self.max_loc[1] + 1)
                if game_map.is_loc_within_bounds(self.min_loc[0] - 1, y)
            ]

            self.pos_to_defend += [
                Position(self.max_loc[0] + 1, y)
                for y in range(self.min_loc[1], self.max_loc[1] + 1)
                if game_map.is_loc_within_bounds(self.max_loc[0] + 1, y)
            ]

            print(f"Num to block: {self.n_to_block}", file=sys.stderr)

    @property
    def n_to_block(self):
        return len(self.pos_to_defend)

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
            return self.resource is not None and ((self.resource.type != RESOURCE_TYPES.WOOD and self.resource.amount > 0) or (self.resource.type == RESOURCE_TYPES.WOOD and self.resource.amount >= 500))
        else:
            return self.resource is not None and self.resource.amount > 0


class GameMap:
    def __init__(self, width, height):
        self.height = height
        self.width = width
        self.map: List[List[Cell]] = [None] * height
        self._resources = []
        for y in range(0, self.height):
            self.map[y] = [None] * width
            for x in range(0, self.width):
                self.map[y][x] = Cell(x, y)

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
        resource_clusters = []
        for cell in self.cells():
            if cell.has_resource() and cell.pos not in resource_pos_found:
                new_cluster_pos = self._check_for_cluster(cell.pos, {cell.pos}, cell.resource.type)
                resource_pos_found = resource_pos_found | new_cluster_pos
                new_cluster = ResourceCluster(cell.resource.type)
                new_cluster.add_resource_positions(*new_cluster_pos)
                resource_clusters.append(new_cluster)

        return resource_clusters

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
        self._closest_resource_pos = None
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
                for k, city in player.cities.items():
                    for city_tile in city.citytiles:
                        dist = city_tile.pos.distance_to(self)
                        if dist < closest_dist:
                            closest_dist = dist
                            self._closest_city_pos = city_tile.pos
        return self._closest_city_pos

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

        if self._closest_resource_pos is None or not game_map.get_cell_by_pos(self._closest_resource_pos).has_resource():
            closest_dist = math.inf
            for resource_tile in game_map.resources():
                if prefer_unlocked_resources:
                    if resource_tile.resource.type == Constants.RESOURCE_TYPES.WOOD:
                        if resource_tile.resource.amount < 500 or player.researched_coal():
                            continue
                    if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL:
                        if not player.researched_coal() or player.researched_uranium():
                            continue
                    if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM:
                        if not player.researched_uranium():
                            continue
                else:
                    # we skip over resources that we can't mine due to not having researched them
                    if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
                    if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
                    if resource_tile.resource.type == Constants.RESOURCE_TYPES.WOOD and resource_tile.resource.amount < 500: continue
                dist = resource_tile.pos.distance_to(self)
                if dist < closest_dist:
                    closest_dist = dist
                    self._closest_resource_pos = resource_tile.pos
        return self._closest_resource_pos

    def direction_to(self, target_pos: 'Position', pos_to_check=None) -> DIRECTIONS:
        """ Return closest position to target_pos from this position

        Parameters
        ----------
        target_pos : Position
            Target position to move to. Can be more than 1 unit away.
        pos_to_check : dict
            Dictionary with keys as directions and values as positions
            corresponding to a move in that direction.

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

        dists = {d: target_pos.distance_to(p) for d, p in pos_to_check.items()}
        return min(dists, key=dists.get)

    def __repr__(self) -> str:
        return f"({self.x}, {self.y})"
