from typing import List
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

    def has_resource(self):
        return self.resource is not None and self.resource.amount > 0


class GameMap:
    def __init__(self, width, height):
        self.height = height
        self.width = width
        self.map: List[List[Cell]] = [None] * height
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
