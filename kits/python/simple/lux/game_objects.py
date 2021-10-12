from typing import Dict
from itertools import chain
from collections import deque
from .constants import ValidActions, print, log, UNIT_TYPE_AS_STR, StrategyTypes, GAME_CONSTANTS, STRATEGY_HYPERPARAMETERS, UnitTypes, LogicGlobals
from .game_map import Position
from .strategies import STRATEGY_FUNCTIONS


class Player:
    def __init__(self, team):
        self.team = team
        self.research_points = 0
        self.units: list[Unit] = []
        self.cities: Dict[str, City] = {}
        self.city_tile_count = 0
        self.city_pos = set()
        self.city_ids = set()
        self.unit_pos = set()
        self.unit_ids = set()
        self.current_strategy = None

    def reset_turn_state(self):
        self.units = []
        self.cities = {}
        self.city_tile_count = 0
        self.city_pos = set()
        self.city_ids = set()
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

    def __eq__(self, other) -> bool:
        return self.cityid == other.cityid

    def __hash__(self):
        return hash(self.cityid)

    def __repr__(self) -> str:
        return f"City({self.cityid})"

    def _add_city_tile(self, x, y, cooldown):
        ct = CityTile(self.team, self.cityid, x, y, cooldown)
        self.citytiles.append(ct)
        return ct

    @property
    def num_night_turns_can_survive(self):
        return self.fuel / self.light_upkeep

    @property
    def num_turns_can_survive(self):
        num_turns = LogicGlobals.game_state.turns_until_next_night
        num_night_turns = self.num_night_turns_can_survive

        while num_night_turns > GAME_CONSTANTS["PARAMETERS"]["NIGHT_LENGTH"]:
            num_turns += GAME_CONSTANTS["PARAMETERS"]["CYCLE_LENGTH"]
            num_night_turns -= GAME_CONSTANTS["PARAMETERS"]["NIGHT_LENGTH"]
        num_turns += num_night_turns
        return num_turns

    @property
    def can_survive_until_end_of_game(self):
        return self.num_turns_can_survive >= (GAME_CONSTANTS["PARAMETERS"]["MAX_DAYS"] - LogicGlobals.game_state.turn + 1)

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
        self.cluster_to_defend_id = None

    def __eq__(self, other) -> bool:
        return (self.cityid == other.cityid) and (self.pos == other.pos)

    def __hash__(self):
        return hash((self.cityid, self.pos.x, self.pos.y))

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

    def __repr__(self) -> str:
        return f"Cargo(Wood: {self.wood}, Coal: {self.coal}, Uranium: {self.uranium})"


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

        self.current_task = None
        self.task_q = deque()
        self.did_just_transfer = False
        self.turns_spent_waiting_to_move = 0
        self.has_colonized = False
        self.cluster_to_defend = None
        self.cluster_to_defend_id = None
        self.current_strategy = StrategyTypes.STARTER
        self.previous_pos = deque(maxlen=2)
        self.__dict__.update(UNIT_CACHE.get(self.id, {}))
        if self.pos not in self.previous_pos:
            self.previous_pos.append(self.pos)

    def save_state(self):
        UNIT_CACHE[self.id] = {
            key: self.__dict__.get(key, None)
            for key in [
                'current_task',
                'task_q',
                'did_just_transfer',
                'turns_spent_waiting_to_move',
                'has_colonized',
                'cluster_to_defend',
                'cluster_to_defend_id',
                'current_strategy',
                'previous_pos',
            ]
        }

    def __del__(self):
        self.save_state()

    def __eq__(self, other) -> bool:
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self) -> str:
        return f"Unit({self.type_str} ({self.id}) at {self.pos} with cargo {self.cargo})"

    def reset(self):
        self.current_task = None
        self.task_q = deque()
        self.did_just_transfer = False
        self.turns_spent_waiting_to_move = 0
        # self.has_colonized = False
        self.cluster_to_defend = None
        self.cluster_to_defend_id = None
        self.previous_pos = deque(maxlen=2)
        self.save_state()

    def is_worker(self) -> bool:
        return self.type == UnitTypes.WORKER

    def is_cart(self) -> bool:
        return self.type == UnitTypes.CART

    def is_building(self):
        builds = [
            t[0] == ValidActions.BUILD
            for t in chain(
                [self.current_task if self.current_task is not None
                 else (None, None)],
                self.task_q
            )
        ]
        return any(builds)

    def get_task_from_strategy(self, player):
        return STRATEGY_FUNCTIONS[self.current_strategy](self, player)

    def set_task(self, action, target, *args):
        if action not in ValidActions.for_unit(self.type):
            raise ValueError(
                f"Invalid action {action} requested "
                f"for unit {self.id} (type: {self.type})"
            )
        if action == ValidActions.MOVE and target == self.pos:
            print(
                f"Set move task for unit {self.id} (type {self.type}), "
                f"but unit is already at {target}",
            )
            return
        if action == ValidActions.COLLECT and self.cargo_space_left() <= 0:
            print(
                f"Set collect task for unit {self.id} (type {self.type}), "
                f"but unit is already at max cargo capacity.",
            )
            return

        if action == ValidActions.BUILD:
            LogicGlobals.add_as_builder(self.id, self.cluster_to_defend_id)
        elif action == ValidActions.MANAGE:
            LogicGlobals.add_as_manager(self.id, self.cluster_to_defend_id)

        self.current_task = (action, target, *args)
        # if action == ValidActions.MANAGE:
        # print(f"New task was set for unit {self.id} at {self.pos}: {action} with target {target}")
        # print(f"New task was set for unit {self.id} at {self.pos}: {self.current_task}")
        # log(f"New task was set for unit {self.id} at {self.pos}: {action} with target {target}")
        self.save_state()

    @property
    def should_avoid_citytiles(self):
        if self.current_task:
            if self.current_task[0] == ValidActions.BUILD:
                return True
            if self.current_task[0] == ValidActions.MOVE and self.num_resources > 0 and any([t[0] == ValidActions.BUILD for t in list(self.task_q)[0:2]]):
                return True
        if not self.task_q:
            return False
        return (self.task_q[0][0] == ValidActions.TRANSFER) or (self.task_q[0][0] == ValidActions.MANAGE and self.num_resources > 0) or (LogicGlobals.game_state.turns_until_next_night >= STRATEGY_HYPERPARAMETERS['BUILD_NIGHT_TURN_BUFFER'] and (self.task_q[0][0] == ValidActions.BUILD)) #  or (len(self.task_q) >= 2 and self.task_q[1][0] == ValidActions.BUILD)))

    @property
    def has_enough_resources_to_manage_city(self):
        return self.num_resources > 0.9 * GAME_CONSTANTS["PARAMETERS"]["RESOURCE_CAPACITY"][self.type_str]

    def can_make_it_back_to_city_before_it_dies(self, city_id, closest_citytile_to_unit=None, mult=1.1):
        if closest_citytile_to_unit is None:
            closest_citytile_to_unit = min(
                [cell.pos for cell in LogicGlobals.player.cities[city_id].citytiles],
                key=self.pos.distance_to
            )
        return mult * LogicGlobals.player.cities[city_id].num_turns_can_survive > self.turn_distance_to(closest_citytile_to_unit)

    def propose_action(self, player, game_state):

        # This does not currently work
        # if game_state.turns_until_next_night == 3:
        #     print(f"STARTING THE AVOID ON TURN {game_state.turn}")
        # elif game_state.turns_until_next_night == 30:
        #     print(f"RESETTING THE AVOID ON TURN {game_state.turn}")

        if not self.can_act():
            return None, None

        # if self.should_avoid_citytiles and game_state.map.get_cell_by_pos(self.pos).citytile is not None:
        #     for pos in self.pos.adjacent_positions(include_center=False):
        #         if game_state.map.get_cell_by_pos(pos).citytile is None:
        #             self.push_task((ValidActions.MOVE, pos))

        if self.current_task is None:
            return None, None

        action, target, *extra = self.current_task

        if action == ValidActions.TRANSFER:
            target_id, __, __ = extra
            for unit in player.units:
                if unit.id == target_id:
                    target_pos = unit.pos
                    self.current_task = (action, target_pos, *extra)
                    if not self.pos.is_adjacent(target_pos):
                        self.push_task((ValidActions.MOVE, target_pos))
                        return self.propose_action(player, game_state)

        elif action == ValidActions.MANAGE:
            if target in player.cities:
                if player.cities[target].resource_positions and any(game_state.map.num_adjacent_resources(p, include_wood_that_is_growing=False, check_for_unlock=True) > 0 for p in player.cities[target].resource_positions):  # TODO: This wood check may make the manage role too difficult
                    print(f"Unit {self.id} can manage at resource positions :", player.cities[target].resource_positions)
                    for target_pos in player.cities[target].resource_positions:
                        if target_pos not in LogicGlobals.player.unit_pos and game_state.map.num_adjacent_resources(target_pos, include_wood_that_is_growing=False, check_for_unlock=True) > 0:  # TODO: This wood check may make the manage role too difficult
                            self.push_task((ValidActions.MOVE, target_pos))
                            return self.propose_action(player, game_state)
            else:
                print(f"Manager {self.id} is managing a non-existent city!")
                return None, None

            closest_citytile_to_unit = min(
                [cell.pos for cell in player.cities[target].citytiles],
                key=self.pos.distance_to
            )

            if not self.has_enough_resources_to_manage_city:
                print(f"Manager {self.id} has to go find resources.")
                target_pos = self.pos.find_closest_resource(
                    player, game_state.map
                )
                print(f"Found closest resource to Manager {self.id}:", target_pos)
                if target_pos is not None:
                    if self.can_make_it_back_to_city_before_it_dies(target, closest_citytile_to_unit=closest_citytile_to_unit, mult=1.1):
                        if target_pos != self.pos and self.can_make_it_to_pos_without_dying(target_pos, mult=1.1): #  self.can_make_it_before_nightfall(target_pos, game_state, mult=1.0):
                            self.push_task((ValidActions.COLLECT, target_pos))
                            return self.propose_action(player, game_state)
                        else:  # TODO: What should we do if worker is too far away from resource to get there before night time???? Maybe have another unit transfer it some resources???
                            distance_to_target = self.pos.pathing_distance_to(target_pos, game_state.map)
                            print(
                                f"Manager {self.id} wants to go find resources but it will take {distance_to_target * GAME_CONSTANTS['PARAMETERS']['UNIT_ACTION_COOLDOWN'][self.type_str] * 1.1 + 0} turns to make it to pos {target_pos}, with {game_state.turns_until_next_night} turns left until nightfall")
                            return None, None
                else:
                    print(f"Manager {self.id} wants to go find resources but there are none left!")
                    return None, None
            # else:
            #     target_pos = min(
            #         [cell.pos for cell in player.cities[target].citytiles],
            #         key=self.pos.distance_to
            #     )
            #     if target_pos != self.pos and self.can_make_it_to_pos_without_dying(target_pos, mult=1.1): # self.can_make_it_before_nightfall(target_pos, game_state, mult=1.1):
            #         self.push_task((ValidActions.MOVE, target_pos))
            #         return self.propose_action(player, game_state)
            #     else:
            #         return None, None

            if closest_citytile_to_unit != self.pos and self.can_make_it_to_pos_without_dying(closest_citytile_to_unit, mult=1.1):  # self.can_make_it_before_nightfall(target_pos, game_state, mult=1.1):
                self.push_task((ValidActions.MOVE, closest_citytile_to_unit))
                return self.propose_action(player, game_state)
            else:
                print(f"Manager {self.id} cannot make it back to city in time!")
                return None, None

        elif action == ValidActions.BUILD:
            if not self.has_enough_resources_to_build:
                closest_resource_pos = self.closest_resource_pos_for_building(target, game_state, player)
                if closest_resource_pos is not None:
                    self.push_task((ValidActions.COLLECT, closest_resource_pos))
                    return self.propose_action(player, game_state)
                else:
                    self.load_next_task()
                    self.check_for_task_completion(game_state.map, player)
                    return self.propose_action(player, game_state)
            elif self.pos != target:
                if self.can_make_it_before_nightfall(target, game_state, mult=1.1, tolerance=STRATEGY_HYPERPARAMETERS['BUILD_NIGHT_TURN_BUFFER']):
                    self.push_task((ValidActions.MOVE, target))
                    return self.propose_action(player, game_state)
                else:
                    closest_city_pos = target.find_closest_city_tile(player, game_state.map)
                    if closest_city_pos is not None and self.can_make_it_to_pos_without_dying(closest_city_pos) and self.turn_distance_to(closest_city_pos) < LogicGlobals.game_state.turns_until_next_day:
                        self.push_task((ValidActions.MOVE, closest_city_pos))
                        return self.propose_action(player, game_state)
                    else:
                        return None, None  # TODO: What should we do if worker is too far away from resource to get there before night time and there is no city to dump resources into?
            if game_state.turns_until_next_night < STRATEGY_HYPERPARAMETERS['BUILD_NIGHT_TURN_BUFFER']:
                return None, None

        elif action == ValidActions.COLLECT:
            if game_state.map.get_cell_by_pos(target).resource is None:
                target_pos = target.find_closest_resource(
                    player, game_state.map
                )
                self.current_task = (action, target_pos)
                if target_pos is not None:
                    self.push_task((ValidActions.MOVE, target_pos))
                    return self.propose_action(player, game_state)
                else:
                    print(f"Unit {self.id} wants to collect but cannot find any resources!")
            elif not self.pos.is_adjacent(target) or game_state.map.get_cell_by_pos(self.pos).citytile is not None:
                self.push_task((ValidActions.MOVE, target))
                return self.propose_action(player, game_state)

        elif action == ValidActions.MOVE:
            # if game_state.map.get_cell_by_pos(self.pos).citytile is not None and game_state.turns_until_next_night <= 1: # TODO:  This is basic and can probably be improved... We don't even check for a resource in the movement direction
            #     return None, None
            if not self.can_make_it_to_pos_without_dying(target): # self.can_make_it_before_nightfall(target, game_state, mult=1) and (self.num_resources < GAME_CONSTANTS["PARAMETERS"]["LIGHT_UPKEEP"][self.type_str] * (GAME_CONSTANTS["PARAMETERS"]["NIGHT_LENGTH"] + 1)):
                closest_resource_pos = self.pos.find_closest_resource(player, game_state.map)
                if closest_resource_pos is not None and closest_resource_pos != target:
                    self.push_task((ValidActions.COLLECT, closest_resource_pos))
                    return self.propose_action(player, game_state)
                # else:
                #     return None, None

        # if action in ValidActions.can_be_adjacent():
        #     if not self.pos.is_adjacent(target_pos):
        #         return ValidActions.MOVE, target_pos
        # else:
        #     if self.pos != target_pos:
        #         return ValidActions.MOVE, target_pos
        self.save_state()
        return self.current_task

    def check_for_task_completion(self, game_map, player):
        # if self.current_task is None:
        #     return
        #
        # should_recheck = True
        # while should_recheck:
        #     should_recheck = False
        #     for ind, (action, target) in enumerate(self.task_q):
        #         if player.current_strategy == StrategyTypes.STARTER and (action == ValidActions.BUILD) and (game_map.position_to_cluster(target) is None):
        #             self.current_task = None
        #             if ind >= len(self.task_q) - 1:
        #                 self.task_q = deque()
        #             else:
        #                 self.task_q = deque(list(self.task_q)[ind + 1:])
        #             should_recheck = True
        #             break
        #         elif action == ValidActions.COLLECT:
        #             if game_map.get_cell_by_pos(target).resource is None or self.cargo_space_left() <= 0:
        #                 if ind >= len(self.task_q) - 1:
        #                     self.task_q = deque()
        #                 else:
        #                     self.task_q = deque(list(self.task_q)[ind+1:])
        #                 self.current_task = None
        #                 should_recheck = True
        #             break
        #         elif action == ValidActions.MANAGE and target not in player.city_ids:
        #             self.current_task = None
        #             self.task_q = deque()
        #             return None

        for ind, (action, target, *extra) in enumerate(self.task_q):
            # if player.current_strategy == StrategyTypes.STARTER and (action == ValidActions.BUILD) and (game_map.position_to_cluster(target) is None):
            if self.current_strategy == StrategyTypes.STARTER and (action == ValidActions.BUILD) and (game_map.position_to_cluster(target) is None):
                print(f"REMOVING BUILD ACTION for UNIT: {self.id}")
                if ind >= len(self.task_q) - 1:
                    self.task_q = deque()
                else:
                    self.task_q = deque(list(self.task_q)[ind + 1:])
                self.current_task = None
                self.check_for_task_completion(game_map, player)
            elif action == ValidActions.COLLECT:
                if game_map.is_within_bounds(target) and game_map.get_cell_by_pos(target).resource is None: #  or self.cargo_space_left() <= 0:
                    if ind >= len(self.task_q) - 1:
                        self.task_q = deque()
                    else:
                        self.task_q = deque(list(self.task_q)[ind+1:])
                    self.current_task = None
                    self.check_for_task_completion(game_map, player)
            elif action == ValidActions.MANAGE and target not in player.city_ids:
                self.current_task = None
                self.task_q = deque()
                return None

        if self.current_task is None:
            self.load_next_task()
            if self.current_task is None:
                return

        action, target = self.current_task
        # if action == ValidActions.MOVE:
        #     if (self.task_q and (self.task_q[0][0] in ValidActions.can_be_adjacent()) and self.pos.is_adjacent(target)) or self.pos == target:
        #         self.current_task = None
        if action == ValidActions.MOVE:
            if self.pos == target:
                self.current_task = None
                self.previous_pos = deque(maxlen=2)
            elif self.task_q:
                if self.task_q[0][0] in ValidActions.can_be_adjacent() and self.pos.is_adjacent(target) and game_map.get_cell_by_pos(self.pos).citytile is None:
                    self.current_task = None
                    self.previous_pos = deque(maxlen=2)
                elif self.task_q[0][0] == ValidActions.TRANSFER:
                    self.current_task = None
                elif LogicGlobals.just_unlocked_new_resource() and len(self.task_q) >= 2 and self.task_q[0][0] == ValidActions.COLLECT and self.task_q[1][0] != ValidActions.BUILD:
                    self.task_q.popleft()
                    self.current_task = self.task_q.popleft()

        elif action == ValidActions.COLLECT:
            if game_map.get_cell_by_pos(target).resource is None:
                self.current_task = None
            elif self.cargo_space_left() <= 0:
                self.current_task = None
            elif self.task_q and self.task_q[0][0] == ValidActions.MANAGE:
                if self.has_enough_resources_to_manage_city:
                    self.current_task = None
                elif self.num_resources > 0 and not self.can_make_it_back_to_city_before_it_dies(self.task_q[0][1], closest_citytile_to_unit=None, mult=1.1):
                    self.current_task = None
                elif self.total_fuel >= STRATEGY_HYPERPARAMETERS["STARTER"][f"MAX_FUEL_PER_MANAGER_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"]:
                    self.current_task = None
        elif action == ValidActions.BUILD:
            city_tile = game_map.get_cell_by_pos(target).citytile
            if city_tile is not None:
                city_tile.cluster_to_defend_id = self.cluster_to_defend_id
                self.current_task = None
                self.has_colonized = True
            # elif player.current_strategy == StrategyTypes.STARTER and game_map.position_to_cluster(target) is None:
            elif self.current_strategy == StrategyTypes.STARTER and game_map.position_to_cluster(target) is None:
                self.current_task = None
                self.has_colonized = True
        elif action == ValidActions.PILLAGE and game_map.get_cell_by_pos(target).road == 0:
            self.current_task = None
        elif action == ValidActions.TRANSFER and self.did_just_transfer:
            self.did_just_transfer = False
            self.current_task = None
        elif action == ValidActions.MANAGE:
            if target in player.city_ids and player.cities[target].can_survive_until_end_of_game:
                print(f"City {target} can now survive until the end of the game! Manager {self.id} released!")
                self.current_task = None
                self.cluster_to_defend = None
                self.cluster_to_defend_id = None

        # if self.current_task is None:
        #     print(f"Unit {self.id} task was set to None during completion check!")
        # print(f"Unit {self.id} task after completion check:", self.current_task)
        if self.current_task is None and self.task_q:
            self.current_task = self.task_q.popleft()
            self.check_for_task_completion(game_map, player)

        self.save_state()

    def push_task(self, task):
        if self.current_task is not None:
            self.task_q.appendleft(self.current_task)
        self.current_task = task
        self.save_state()

    def load_next_task(self):
        if self.task_q:
            self.current_task = self.task_q.popleft()
        else:
            self.current_task = None
        self.save_state()

    def cargo_space_left(self):
        """
        get cargo space left in this unit
        """
        return GAME_CONSTANTS["PARAMETERS"]["RESOURCE_CAPACITY"][self.type_str] - self.num_resources

    @property
    def num_resources(self) -> int:
        return self.cargo.wood + self.cargo.coal + self.cargo.uranium

    @property
    def total_fuel(self):
        return (
            self.cargo.wood * GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"]["WOOD"]
            + self.cargo.coal * GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"]["COAL"]
            + self.cargo.uranium * GAME_CONSTANTS["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"]["URANIUM"]
        )

    @property
    def has_enough_resources_to_build(self) -> bool:
        return self.num_resources >= GAME_CONSTANTS["PARAMETERS"]["CITY_BUILD_COST"]

    def closest_resource_pos_for_building(self, build_pos, game_state, player):
        if self.num_resources >= 0.75 * GAME_CONSTANTS["PARAMETERS"]["CITY_BUILD_COST"]:
            return build_pos.find_closest_resource(player, game_state.map, tie_breaker_func=self.turn_distance_to)

        closest_resource_pos = build_pos.find_closest_wood(game_state.map, tie_breaker_func=self.turn_distance_to)
        if closest_resource_pos is not None:
            return closest_resource_pos
        return build_pos.find_closest_resource(player, game_state.map, tie_breaker_func=self.turn_distance_to)

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

    def turn_distance_to(self, target_pos):
        return self.pos.turn_distance_to(
            target_pos,
            LogicGlobals.game_state.map,
            cooldown=GAME_CONSTANTS["PARAMETERS"]["UNIT_ACTION_COOLDOWN"][self.type_str],
            avoid_own_cities=self.should_avoid_citytiles,
        )

    def can_make_it_to_pos_without_dying(self, target_pos, mult=1.0):
        if self.pos.is_adjacent(target_pos) and LogicGlobals.game_state.map.num_adjacent_resources(target_pos) > 0:
            return True
        elif self.pos.distance_to(target_pos) <= 2 and LogicGlobals.game_state.map.get_cell_by_pos(target_pos).resource is not None:  # TODO: This could also rely on the amount of fuel left in the resource
            return True
        num_turns_left = self.turn_distance_to(target_pos) - LogicGlobals.game_state.turns_until_next_night
        num_night_turns = 0
        while num_turns_left > GAME_CONSTANTS["PARAMETERS"]["NIGHT_LENGTH"]:
            num_night_turns += GAME_CONSTANTS["PARAMETERS"]["NIGHT_LENGTH"]
            num_turns_left -= GAME_CONSTANTS["PARAMETERS"]["DAY_LENGTH"]
        num_night_turns += max(0, num_turns_left)
        fuel_needed_to_survive = num_night_turns * GAME_CONSTANTS["PARAMETERS"]["LIGHT_UPKEEP"][self.type_str]
        return self.total_fuel >= mult * fuel_needed_to_survive

    def can_make_it_before_nightfall(self, target_pos, game_state, mult=1.0, tolerance=0):
        if target_pos is None:
            return False
        turns_to_target = self.turn_distance_to(target_pos)
        return turns_to_target * mult + tolerance < game_state.turns_until_next_night

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
