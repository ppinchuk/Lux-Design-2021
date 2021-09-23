from typing import Dict
import sys
from collections import deque

from .constants import Constants, ValidActions, print_out, UNIT_TYPE_AS_STR
from .game_map import Position
from .game_constants import GAME_CONSTANTS, STRATEGY_CONSTANTS

UNIT_TYPES = Constants.UNIT_TYPES


class Player:
    def __init__(self, team):
        self.team = team
        self.research_points = 0
        self.units: list[Unit] = []
        self.cities: Dict[str, City] = {}
        self.city_tile_count = 0
        self.city_pos = set()
        self.unit_pos = set()
        self.unit_ids = set()

    def researched_coal(self) -> bool:
        return self.research_points >= GAME_CONSTANTS["PARAMETERS"]["RESEARCH_REQUIREMENTS"]["COAL"]

    def researched_uranium(self) -> bool:
        return self.research_points >= GAME_CONSTANTS["PARAMETERS"]["RESEARCH_REQUIREMENTS"]["URANIUM"]


class City:
    def __init__(self, teamid, cityid, fuel, light_upkeep):
        self.cityid = cityid
        self.team = teamid
        self.fuel = fuel
        self.citytiles: list[CityTile] = []
        self.light_upkeep = light_upkeep
        self.managers = set()
        self.resource_positions = []
        self.neighbor_resource_types = set()

    def _add_city_tile(self, x, y, cooldown):
        ct = CityTile(self.team, self.cityid, x, y, cooldown)
        self.citytiles.append(ct)
        return ct

    def get_light_upkeep(self):
        return self.light_upkeep

    def update_resource_positions(self, game_map):
        num_resources_for_tile = [
            (
                tile.pos,
                game_map.num_adjacent_resources(tile.pos, include_center=False)
            )
            for tile in self.citytiles
        ]
        self.resource_positions = [
            x[0] for x in sorted(num_resources_for_tile, key=lambda x: x[1])
        ][::-1]

        self.neighbor_resource_types = set()
        for tile in self.citytiles:
            self.neighbor_resource_types = self.neighbor_resource_types | game_map.adjacent_resource_types(tile.pos, include_center=False)


class CityTile:
    def __init__(self, teamid, cityid, x, y, cooldown):
        self.cityid = cityid
        self.team = teamid
        self.pos = Position(x, y)
        self.cooldown = cooldown

    def can_act(self) -> bool:
        """
        Whether or not this unit can research or build
        """
        return self.cooldown < 1

    def research(self) -> str:
        """
        returns command to ask this tile to research this turn
        """
        return "r {} {}".format(self.pos.x, self.pos.y)

    def build_worker(self) -> str:
        """
        returns command to ask this tile to build a worker this turn
        """
        return "bw {} {}".format(self.pos.x, self.pos.y)

    def build_cart(self) -> str:
        """
        returns command to ask this tile to build a cart this turn
        """
        return "bc {} {}".format(self.pos.x, self.pos.y)


class Cargo:
    def __init__(self, wood=0, coal=0, uranium=0):
        self.wood = wood
        self.coal = coal
        self.uranium = uranium

    def __str__(self) -> str:
        return f"Cargo | Wood: {self.wood}, Coal: {self.coal}, Uranium: {self.uranium}"


UNIT_CACHE = {}


class Unit:
    def __init__(self, teamid, u_type, unitid, x, y, cooldown, wood, coal, uranium):
        self.pos = Position(x, y)
        self.team = teamid
        self.id = unitid
        self.type = u_type
        self.type_str = UNIT_TYPE_AS_STR[u_type]
        self.cooldown = cooldown
        self.cargo = Cargo(wood, coal, uranium)
        self.__dict__.update(
            UNIT_CACHE.get(self.id, {
                'current_task': None,
                'task_q': deque(),
                'did_just_transfer': False,
                'turns_spent_waiting_to_move': 0,
                'should_avoid_citytiles': False,
                'was_avoiding_citytiles': False,
                'has_colonized': False,
                'cluster_to_defend': None,
            })
        )

    def __del__(self):
        UNIT_CACHE[self.id] = {
            key: self.__dict__[key]
            for key in [
                'current_task',
                'task_q',
                'did_just_transfer',
                'turns_spent_waiting_to_move',
                'should_avoid_citytiles',
                'was_avoiding_citytiles',
                'has_colonized',
                'cluster_to_defend',
            ]
        }

    def reset(self):
        self.current_task = None
        self.task_q = deque()
        self.did_just_transfer = False
        self.turns_spent_waiting_to_move = 0
        self.should_avoid_citytiles = False
        self.was_avoiding_citytiles = False
        # self.has_colonized = False
        self.cluster_to_defend = None

    def is_worker(self) -> bool:
        return self.type == UNIT_TYPES.WORKER

    def is_cart(self) -> bool:
        return self.type == UNIT_TYPES.CART

    def set_task(self, action, target):
        if action not in ValidActions.for_unit(self.type):
            raise ValueError(
                f"Invalid action {action} requested "
                f"for unit {self.id} (type: {self.type})"
            )
        if action == ValidActions.MOVE and target == self.pos:
            print(
                f"Set move task for unit {self.id} (type {self.type}), "
                f"but unit is already at {target}",
                file=sys.stderr
            )
            return
        if action == ValidActions.COLLECT and self.cargo_space_left() <= 0:
            print(
                f"Set collect task for unit {self.id} (type {self.type}), "
                f"but unit is already at max cargo capacity.",
                file=sys.stderr
            )
            return
        # if action == ValidActions.BUILD:
        #     self.should_avoid_citytiles = True
        self.current_task = (action, target)
        if action == ValidActions.MANAGE:
            print(f"New task was set for unit {self.id} at {self.pos}: {action} with target {target}", file=sys.stderr)
        print(f"New task was set for unit {self.id} at {self.pos}: {action} with target {target}", file=print_out)

    def propose_action(self, player, game_state):

        # This does not currently work
        # if game_state.turns_until_next_night == 3:
        #     print(f"STARTING THE AVOID ON TURN {game_state.turn}", file=sys.stderr)
        #     self.was_avoiding_citytiles = self.should_avoid_citytiles
        #     self.should_avoid_citytiles = True
        # elif game_state.turns_until_next_night == 30:
        #     print(f"RESETTING THE AVOID ON TURN {game_state.turn}", file=sys.stderr)
        #     self.should_avoid_citytiles = self.was_avoiding_citytiles
        #     self.was_avoiding_citytiles = False

        if not self.can_act():
            return None, None

        # if self.should_avoid_citytiles and game_state.map.get_cell_by_pos(self.pos).citytile is not None:
        #     for pos in self.pos.adjacent_positions(include_center=False):
        #         if game_state.map.get_cell_by_pos(pos).citytile is None:
        #             self.push_task((ValidActions.MOVE, pos))

        if self.current_task is None:
            return None, None

        action, target = self.current_task
        if action == ValidActions.TRANSFER:
            target_id, __, __ = target
            for unit in player.units:
                if unit.id == target_id:
                    target_pos = unit.pos
                    if not self.pos.is_adjacent(target_pos):
                        self.push_task((ValidActions.MOVE, target_pos))
                    break

        action, target = self.current_task
        if action == ValidActions.MANAGE:
            if player.cities[target].resource_positions and any(game_state.map.num_adjacent_resources(p, do_wood_check=False) > 0 for p in  player.cities[target].resource_positions):
                for target_pos in player.cities[target].resource_positions:
                    if game_state.map.num_adjacent_resources(target_pos, do_wood_check=True) > 0:
                        self.push_task((ValidActions.MOVE, target_pos))
                        break
            else:
                if self.num_resources < GAME_CONSTANTS["PARAMETERS"]["RESOURCE_CAPACITY"][self.type_str]:
                    target_pos = self.pos.find_closest_resource(
                        player, game_state.map
                    )
                    if target_pos != self.pos and self.can_make_it_before_nightfall(target_pos, game_state, mult=1.1):
                        self.push_task((ValidActions.COLLECT, target_pos))
                    else:  # TODO: What should we do if worker is too far away from resource to get there before night time???? Maybe have another unit transfer it some resources???
                        return None, None
                else:
                    target_pos = min(
                        [cell.pos for cell in player.cities[target].citytiles],
                        key=self.pos.distance_to
                    )
                    if target_pos != self.pos and self.can_make_it_before_nightfall(target_pos, game_state, mult=1.1):
                        self.push_task((ValidActions.MOVE, target_pos))
                    else:
                        return None, None

        action, target_pos = self.current_task
        if action == ValidActions.BUILD:
            # if self.num_resources > 0:
            #     self.should_avoid_citytiles = True
            self.should_avoid_citytiles = True
            closest_resource_pos = self.closest_resource_pos_for_building(target_pos, game_state, player)
            if not self.has_enough_resources_to_build:
                if closest_resource_pos is not None:
                    self.push_task((ValidActions.COLLECT, closest_resource_pos))
                    return self.propose_action(player, game_state)
                else:
                    self.load_next_task()
                    self.check_for_task_completion(game_state.map)
                    return self.propose_action(player, game_state)
            elif self.pos != target_pos:
                if self.can_make_it_before_nightfall(target_pos, game_state, mult=1.1, tolerance=STRATEGY_CONSTANTS['BUILD_NIGHT_TURN_BUFFER']):
                    self.push_task((ValidActions.MOVE, target_pos))
                else:  # TODO: What should we do if worker is too far away from resource to get there before night time???? Maybe have another unit transfer it some resources???
                    return None, None
            if game_state.turns_until_next_night < STRATEGY_CONSTANTS['BUILD_NIGHT_TURN_BUFFER']:
                return None, None
        # else:
        #     self.should_avoid_citytiles = False

        action, target_pos = self.current_task
        if action == ValidActions.COLLECT:
            if game_state.map.get_cell_by_pos(target_pos).resource is None:
                target_pos = target_pos.find_closest_resource(
                    player, game_state.map
                )
                self.current_task = (action, target_pos)
                if target_pos is not None:
                    self.push_task((ValidActions.MOVE, target_pos))
                else:
                    print(f"Unit {self.id} wants to collect but cannot find any resources!", file=sys.stderr)
            elif not self.pos.is_adjacent(target_pos) or game_state.map.get_cell_by_pos(self.pos).citytile is not None:
                self.push_task((ValidActions.MOVE, target_pos))

        action, target_pos = self.current_task
        if action == ValidActions.MOVE:
            if not self.can_make_it_before_nightfall(target_pos, game_state, mult=1.1) and (self.num_resources < GAME_CONSTANTS["PARAMETERS"]["LIGHT_UPKEEP"][self.type_str] * (GAME_CONSTANTS["PARAMETERS"]["NIGHT_LENGTH"] + 1)):
                closest_resource_pos = self.pos.find_closest_resource(player, game_state.map)
                if closest_resource_pos is not None and closest_resource_pos != target_pos:
                    self.push_task((ValidActions.COLLECT, closest_resource_pos))
                else:
                    return None, None

        action, target_pos = self.current_task
        if action == ValidActions.COLLECT:
            if not self.pos.is_adjacent(target_pos) or game_state.map.get_cell_by_pos(self.pos).citytile is not None:
                self.push_task((ValidActions.MOVE, target_pos))

        # if action in ValidActions.can_be_adjacent():
        #     if not self.pos.is_adjacent(target_pos):
        #         return ValidActions.MOVE, target_pos
        # else:
        #     if self.pos != target_pos:
        #         return ValidActions.MOVE, target_pos

        return self.current_task

    def check_for_task_completion(self, game_map):
        if self.current_task is None:
            return

        should_recheck = True
        while should_recheck:
            should_recheck = False
            for ind, (action, target) in enumerate(self.task_q):
                if action == ValidActions.BUILD and game_map.position_to_cluster(target) is None:
                    self.task_q = deque(list(self.task_q)[ind+1:])
                    should_recheck = True
                    break
                elif action == ValidActions.COLLECT and game_map.get_cell_by_pos(target).resource is None:
                    self.task_q = deque(list(self.task_q)[ind+1:])
                    should_recheck = True
                    break

        action, target = self.current_task
        # if action == ValidActions.MOVE:
        #     if (self.task_q and (self.task_q[0][0] in ValidActions.can_be_adjacent()) and self.pos.is_adjacent(target)) or self.pos == target:
        #         self.current_task = None
        if action == ValidActions.MOVE and self.pos == target:
            self.current_task = None
        elif action == ValidActions.COLLECT:
            if self.cargo_space_left() <= 0 or game_map.get_cell_by_pos(target).resource is None:
                self.current_task = None
        elif action == ValidActions.BUILD:
            if game_map.get_cell_by_pos(target).citytile is not None or game_map.position_to_cluster(target) is None:
                self.should_avoid_citytiles = False
                self.current_task = None
                self.has_colonized = True
        elif action == ValidActions.PILLAGE and game_map.get_cell_by_pos(target).road == 0:
            self.current_task = None
        elif action == ValidActions.TRANSFER and self.did_just_transfer:
            self.did_just_transfer = False
            self.current_task = None

        if self.current_task is None and self.task_q:
            self.current_task = self.task_q.popleft()
            self.check_for_task_completion(game_map)

    def push_task(self, task):
        if self.current_task is not None:
            self.task_q.appendleft(self.current_task)
        self.current_task = task

    def load_next_task(self):
        if self.task_q:
            self.current_task = self.task_q.popleft()
        else:
            self.current_task = None

    def cargo_space_left(self):
        """
        get cargo space left in this unit
        """
        return GAME_CONSTANTS["PARAMETERS"]["RESOURCE_CAPACITY"][self.type_str] - self.num_resources

    @property
    def num_resources(self) -> int:
        return self.cargo.wood + self.cargo.coal + self.cargo.uranium

    @property
    def has_enough_resources_to_build(self) -> bool:
        return self.num_resources >= GAME_CONSTANTS["PARAMETERS"]["CITY_BUILD_COST"]

    def closest_resource_pos_for_building(self, build_pos, game_state, player):
        if self.num_resources >= 0.75 * GAME_CONSTANTS["PARAMETERS"]["CITY_BUILD_COST"]:
            closest_resource_pos = build_pos.find_closest_resource(player, game_state.map)
        else:
            closest_resource_pos = build_pos.find_closest_wood(game_state.map)
        return closest_resource_pos

    def can_build(self, game_map) -> bool:
        """
        whether or not the unit can build where it is right now
        """
        if self.is_cart():
            return False
        cell = game_map.get_cell_by_pos(self.pos)
        if not cell.has_resource() and cell.citytile is None and self.can_act() and self.has_enough_resources_to_build:
            return True
        return False

    def can_act(self) -> bool:
        """
        whether or not the unit can move or not. This does not check for potential collisions into other units or enemy cities
        """
        return self.cooldown < 1

    def can_make_it_before_nightfall(self, target_pos, game_state, mult=1.0, tolerance=0):
        distance_to_target = self.pos.pathing_distance_to(target_pos, game_state.map)
        return distance_to_target * GAME_CONSTANTS["PARAMETERS"]["UNIT_ACTION_COOLDOWN"][self.type_str] * mult + tolerance < game_state.turns_until_next_night

    def move(self, dir, logs=None) -> str:
        """
        return the command to move unit in the given direction
        """
        if logs is not None:
            logs.append((self.id, ValidActions.MOVE, dir))
        return "m {} {}".format(self.id, dir)

    def transfer(self, dest_id, resourceType, amount, logs=None) -> str:
        """
        return the command to transfer a resource from a source unit to a destination unit as specified by their ids
        """
        if logs is not None:
            logs.append((self.id, ValidActions.TRANSFER, dest_id))
        return "t {} {} {} {}".format(self.id, dest_id, resourceType, amount)

    def build_city(self, logs=None) -> str:
        """
        return the command to build a city right under the worker
        """
        if self.is_cart():
            raise ValueError(f"Unit {self.id} is a cart; cannot build a city!")
        if logs is not None:
            logs.append((self.id, ValidActions.BUILD, self.pos))
        return "bcity {}".format(self.id)

    def pillage(self, logs=None) -> str:
        """
        return the command to pillage whatever is underneath the worker
        """
        if self.is_cart():
            raise ValueError(f"Unit {self.id} is a cart; cannot pillage!")
        if logs is not None:
            logs.append((self.id, ValidActions.PILLAGE, self.pos))
        return "p {}".format(self.id)
