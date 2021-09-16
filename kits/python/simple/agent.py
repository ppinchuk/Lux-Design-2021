from lux.game import Game
from lux.game_map import Cell, DIRECTIONS, Position
from lux.constants import Constants, ALL_DIRECTIONS, ALL_DIRECTIONS_AND_CENTER, ValidActions
from collections import Counter, UserDict
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


def city_tile_to_build(cluster):
    for pos in cluster.pos_to_defend:
        cell = LogicGlobals.game_state.map.get_cell_by_pos(pos)
        if cell.citytile is None and pos not in LogicGlobals.pos_being_built:
            return cell.pos
    return None


# if our cluster is separate from other base, build around them.
# Prefer 2x2 clusters


def set_unit_task(unit, player):
    if not unit.can_act():
        return

    for __, city in player.cities.items():
        if LogicGlobals.unlocked_uranium and Constants.RESOURCE_TYPES.URANIUM in city.neighbor_resource_types:
            if len(city.managers) < city.light_upkeep / (15 * 80) + 1:
                unit.set_task(action=ValidActions.MANAGE, target=city.cityid)
                city.managers.add(unit.id)
                return

        if LogicGlobals.unlocked_coal and Constants.RESOURCE_TYPES.COAL in city.neighbor_resource_types:
            if len(city.managers) < city.light_upkeep / (15 * 50) + 1:
                unit.set_task(action=ValidActions.MANAGE, target=city.cityid)
                city.managers.add(unit.id)
                return

    if not unit.has_colonized and LogicGlobals.clusters_to_colonize:
        # cluster_to_defend = min(
        #     LogicGlobals.clusters_to_colonize,
        #     key=lambda c: min(unit.pos.distance_to(p) for p in c.pos_to_defend)
        # )
        cluster_to_defend = max(
            LogicGlobals.clusters_to_colonize,
            key=lambda c: c.current_score
        )

    else:
        cluster_to_defend = POSITION_TO_CLUSTER[
            unit.pos.find_closest_resource(
                player=player,
                game_map=LogicGlobals.game_state.map,
                prefer_unlocked_resources=False
            )
        ]

    new_city_pos = city_tile_to_build(cluster_to_defend)
    if new_city_pos is not None:
        unit.set_task(action=ValidActions.BUILD, target=new_city_pos)
        LogicGlobals.pos_being_built.add(new_city_pos)

    # TODO: May be better if a city requests a manager from a nearby unit
    # if LogicGlobals.player.city_tile_count >= 5 or (LogicGlobals.game_state.turn % GAME_CONSTANTS["PARAMETERS"]["CYCLE_LENGTH"]) > GAME_CONSTANTS["PARAMETERS"]["DAY_LENGTH"] // 2:
    #     for __, city in LogicGlobals.player.cities.items():
    #         if not city.managers:
    #             unit.set_task(action=ValidActions.MANAGE, target=city.cityid)
    #             city.managers.add(unit.id)
    #             return

    # new_city_pos = city_tile_to_build(LogicGlobals.start_tile, player)
    # if new_city_pos is not None:
    #     unit.set_task(action=ValidActions.BUILD, target=new_city_pos)
    #     LogicGlobals.pos_being_built.add(new_city_pos)


class LogicGlobals:
    game_state = Game()
    player = None
    start_tile = None
    clusters = None
    unlocked_coal = False
    unlocked_uranium = False
    cities = None
    pos_being_built = set()
    resource_cluster_to_defend = None
    clusters_to_colonize = set()
    max_resource_cluster_amount = 0


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
    player = LogicGlobals.player = LogicGlobals.game_state.players[observation.player]
    opponent = LogicGlobals.game_state.players[(observation.player + 1) % 2]
    width, height = LogicGlobals.game_state.map.width, LogicGlobals.game_state.map.height

    if LogicGlobals.game_state.turn == 0:
        for unit in player.units:
            unit.has_colonized = True
        LogicGlobals.clusters = LogicGlobals.game_state.map.find_clusters()
        if LogicGlobals.start_tile is None:
            LogicGlobals.start_tile = Position(0, 0).find_closest_city_tile(player, LogicGlobals.game_state.map)

    # LogicGlobals.clusters = LogicGlobals.game_state.map.find_clusters()
    # if LogicGlobals.start_tile is None:
    #     LogicGlobals.start_tile = Position(0, 0).find_closest_city_tile(player, LogicGlobals.game_state.map)

    LogicGlobals.unlocked_coal = player.researched_coal()
    LogicGlobals.unlocked_uranium = player.researched_uranium()
    LogicGlobals.cities = player.cities

    for city_id, city in player.cities.items():
        city.update_resource_positions(LogicGlobals.game_state.map)

    LogicGlobals.clusters_to_colonize = set()
    for cluster in LogicGlobals.clusters:
        cluster.update_state(game_map=LogicGlobals.game_state.map)
        if cluster.total_amount >= 0:
            if cluster.type == Constants.RESOURCE_TYPES.URANIUM:
                if LogicGlobals.unlocked_uranium:
                    LogicGlobals.clusters_to_colonize.add(cluster)
            elif cluster.type == Constants.RESOURCE_TYPES.COAL:
                if LogicGlobals.unlocked_coal:
                    LogicGlobals.clusters_to_colonize.add(cluster)
            else:
                LogicGlobals.clusters_to_colonize.add(cluster)
        # if cluster.type == Constants.RESOURCE_TYPES.WOOD and cluster.n_defended == 0:
        #     LogicGlobals.clusters_to_colonize.add(cluster)

    if LogicGlobals.resource_cluster_to_defend is not None and (all(LogicGlobals.game_state.map.get_cell_by_pos(p).citytile is not None for p in LogicGlobals.resource_cluster_to_defend.pos_to_defend) or LogicGlobals.resource_cluster_to_defend.total_amount <= 0):
        LogicGlobals.resource_cluster_to_defend = None

    actions = []
    blocked_positions = set()

    # Not sure if this is good or not
    # for cell in LogicGlobals.game_state.map.cells():
    #     if cell.has_resource() and cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
    #         if cell.resource.amount < 500:
    #             blocked_positions = blocked_positions | cell.pos.adjacent_positions()

    for unit in opponent.units:
        # TODO: This may cause issues in the endgame
        blocked_positions = blocked_positions | unit.pos.adjacent_positions()

    LogicGlobals.pos_being_built = set()
    for unit in player.units:
        unit.check_for_task_completion(game_map=LogicGlobals.game_state.map)
        blocked_positions.add(unit.pos)
        for task, target in chain([unit.current_task if unit.current_task is not None else (None, None)], unit.task_q):
            if task == ValidActions.BUILD:
                LogicGlobals.pos_being_built.add(target)
            elif task == ValidActions.MANAGE:
                if target in player.cities:
                    player.cities[target].managers.add(unit.id)
                else:
                    unit.current_task = None

    clusters_already_bing_colonized = {
        c for c in LogicGlobals.clusters_to_colonize
        if any(p in LogicGlobals.pos_being_built for p in c.pos_to_defend)
        or any(p in player.city_pos for p in c.pos_defended)
    }
    LogicGlobals.clusters_to_colonize = LogicGlobals.clusters_to_colonize - clusters_already_bing_colonized
    LogicGlobals.max_resource_cluster_amount = max(
        [1] + [c.total_amount for c in LogicGlobals.clusters_to_colonize]
    )
    for c in LogicGlobals.clusters_to_colonize:
        c.calculate_score(player, opponent, scaling_factor=LogicGlobals.max_resource_cluster_amount)

    # for city_id, city in LogicGlobals.player.cities.items():
    #     print(f"Turn {LogicGlobals.game_state.turn} city {city_id} managers: {city.managers}", file=sys.stderr)

    for __, city in player.cities.items():
        for tile in city.citytiles:
            blocked_positions.discard(tile.pos)
        # print(f"Turn {LogicGlobals.game_state.turn} - City {city.cityid} managers: {city.managers}", file=sys.stderr)

    for unit in player.units:
        if unit.current_task is None:
            set_unit_task(unit, player)

    for unit in player.units:
        action, target = unit.propose_action(player, LogicGlobals.game_state)
        # print(f"Unit {unit.id} at {unit.pos} proposed action {action} with target {target}", file=sys.stderr)
        if action == ValidActions.MOVE:
            blocked_positions.discard(unit.pos)

    debug_info = []
    proposed_positions = {}
    for unit in player.units:
        action, target = unit.propose_action(
            player, LogicGlobals.game_state
        )
        if action is None:
            continue
        elif action == ValidActions.BUILD:
            actions.append(unit.build_city(logs=debug_info))
        elif action == ValidActions.TRANSFER:
            actions.append(unit.transfer(*target, logs=debug_info))
            unit.did_just_transfer = True
        elif action == ValidActions.PILLAGE:
            actions.append(unit.pillage(logs=debug_info))
        elif action == ValidActions.MOVE:
            blocked_positions.discard(unit.pos)

            pos_to_check = {}
            for direction in ALL_DIRECTIONS:
                new_pos = unit.pos.translate(direction, 1)
                if not LogicGlobals.game_state.map.is_within_bounds(new_pos):
                    continue
                pos_contains_citytile = LogicGlobals.game_state.map.get_cell_by_pos(new_pos).citytile is not None
                if not LogicGlobals.game_state.map.is_within_bounds(new_pos) or (pos_contains_citytile and unit.should_avoid_citytiles and unit.turns_spent_waiting_to_move < 5):
                    continue
                pos_to_check[direction] = new_pos
            if not pos_to_check:
                unit.turns_spent_waiting_to_move += 1
                blocked_positions.add(unit.pos)
                continue
            dir_to_move = unit.pos.direction_to(target, pos_to_check=pos_to_check)
            if dir_to_move == DIRECTIONS.CENTER:
                continue
            new_pos = pos_to_check[dir_to_move]
            if new_pos in blocked_positions:
                unit.turns_spent_waiting_to_move += 1
                blocked_positions.add(unit.pos)
                continue
            proposed_positions.setdefault(new_pos, []).append((unit, dir_to_move))

    # print(f"{proposed_positions}", file=sys.stderr)
    for pos, units in proposed_positions.items():
        unit, direction = max(units, key=lambda pair: pair[0].turns_spent_waiting_to_move)
        actions.append(unit.move(direction, logs=debug_info))
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
                    if not player.researched_uranium():
                        actions.append(city_tile.research())
                        player.research_points += 1

    # DEBUG STUFF

    actions.append(
        annotate.sidetext(
            f"Found {len(LogicGlobals.clusters)} clusters",
        )
    )
    actions.append(
        annotate.sidetext(
            "Cluster - N_resource - N_defend - Score",
        )
    )
    for cluster in LogicGlobals.clusters:
        actions.append(
            annotate.sidetext(
                annotate.format_message(f"{cluster.center_pos} - {cluster.total_amount:4d} - {cluster.n_to_block:1d} - {cluster.current_score:0.5f}"),
            )
        )
        # for pos in cluster.resource_positions:
        #     actions.append(annotate.circle(pos.x, pos.y))
        # for pos in cluster.pos_to_defend:
        #     actions.append(annotate.x(pos.x, pos.y))

    actions.append(annotate.sidetext("GOAL TASKS"))

    for unit in player.units:
        if unit.task_q:
            actions.append(
                annotate.sidetext(
                    annotate.format_message(f"{unit.id}: {unit.task_q[-1][0]} at {unit.task_q[-1][1]} ")
                )
            )
        else:
            actions.append(
                annotate.sidetext(
                    f"{unit.id}: None"
                )
            )

    actions.append(annotate.sidetext("TASK QUEUE"))

    for unit in player.units:
        if unit.task_q:
            actions.append(
                annotate.sidetext(
                    # annotate.format_message(f"{unit.id}: {unit.task_q[-1][0]} at {unit.task_q[-1][1]} ")
                    annotate.format_message(
                        f"{unit.id}: " +
                        " - ".join(
                            [f"{t[0]} to {t[1]}"
                             if t[0] == 'move' else f"{t[0]} at {t[1]}"
                             for t in unit.task_q
                             ]
                        )
                    )
                )
            )
        else:
            actions.append(
                annotate.sidetext(
                    f"{unit.id}: None"
                )
            )

    actions.append(annotate.sidetext("TASKS"))

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
                    annotate.format_message(f"{unit.id}: {unit.current_task[0]} at {unit.current_task[1]} ")
                )
            )

    actions.append(annotate.sidetext("ACTIONS"))

    for uid, action, target in debug_info:
        actions.append(
            annotate.sidetext(
                annotate.format_message(f"{uid}: {action} with target {target}")
            )
        )

    actions.append(annotate.text(15, 15, "A"))

    return actions




