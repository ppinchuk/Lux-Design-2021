from lux.game import Game
from lux.game_map import Position
import lux.game_objects as go
import sys
# print("SOME RANDOM NUMBER:", random.random(), file=sys.stderr)
from lux.constants import ValidActions, log, print, StrategyTypes, LogicGlobals, ALL_DIRECTIONS, ResourceTypes, STRATEGY_HYPERPARAMETERS, GAME_CONSTANTS
from lux.strategies import starter_strategy, time_based_strategy, research_based_strategy, set_unit_task, set_unit_strategy
from lux.strategy_utils import resolve_unit_movement, switch_builds_if_needed, select_movement_direction_for_unit
from collections import deque, Counter, UserDict
from itertools import chain
from lux.annotate import add_annotations
from random import seed
import getpass
import math

seed(69420)


# Define helper functions
def update_logic_globals(player):
    if LogicGlobals.game_state.turn == 0:
        for unit in player.units:
            unit.has_colonized = True
        if LogicGlobals.radius_for_clusters == 0:
            LogicGlobals.radius_for_clusters = max(
                [
                    player.units[0].pos.distance_to(Position(0, 0)),
                    player.units[0].pos.distance_to(Position(0, LogicGlobals.game_state.map.height)),
                    player.units[0].pos.distance_to(Position(LogicGlobals.game_state.map.width, 0)),
                    player.units[0].pos.distance_to(Position(LogicGlobals.game_state.map.width, LogicGlobals.game_state.map.height))
                ]
            )

    LogicGlobals.unlocked_coal = player.researched_coal()
    LogicGlobals.unlocked_uranium = player.researched_uranium()
    LogicGlobals.unlock_coal_memory.append(LogicGlobals.unlocked_coal)
    LogicGlobals.unlock_uranium_memory.append(LogicGlobals.unlocked_uranium)
    LogicGlobals.cities = player.cities

    for city_id, city in player.cities.items():
        city.update_resource_positions(LogicGlobals.game_state.map)

    LogicGlobals.clusters_to_colonize = set()
    for cluster in LogicGlobals.game_state.map.resource_clusters:
        if cluster.total_amount >= 0:
            if cluster.type == ResourceTypes.URANIUM:
                if LogicGlobals.unlocked_uranium:
                    LogicGlobals.clusters_to_colonize.add(cluster)
            elif cluster.type == ResourceTypes.COAL:
                if LogicGlobals.unlocked_coal:
                    LogicGlobals.clusters_to_colonize.add(cluster)
            else:
                LogicGlobals.clusters_to_colonize.add(cluster)
        # if cluster.type == Constants.RESOURCE_TYPES.WOOD and cluster.n_defended == 0:
        #     LogicGlobals.clusters_to_colonize.add(cluster)

    units_lost = set(go.UNIT_CACHE) - player.unit_ids
    for id_ in units_lost:
        go.UNIT_CACHE.pop(id_)

    for k, v in LogicGlobals.CLUSTER_ID_TO_BUILDERS.items():
        LogicGlobals.CLUSTER_ID_TO_BUILDERS[k] = LogicGlobals.CLUSTER_ID_TO_BUILDERS.get(k, set()) & player.unit_ids

    for k, v in LogicGlobals.CLUSTER_ID_TO_MANAGERS.items():
        LogicGlobals.CLUSTER_ID_TO_MANAGERS[k] = LogicGlobals.CLUSTER_ID_TO_MANAGERS.get(k, set()) & player.unit_ids

    # print("Builders:", ", ".join([f"{LogicGlobals.game_state.map.get_cluster_by_id(k)}: {v}" for k, v in LogicGlobals.CLUSTER_ID_TO_BUILDERS.items()]))
    # print("Managers:", ", ".join([f"{LogicGlobals.game_state.map.get_cluster_by_id(k)}: {v}" for k, v in LogicGlobals.CLUSTER_ID_TO_MANAGERS.items()]))

    LogicGlobals.RBS_cluster_carts = {}
    for unit in LogicGlobals.player.units:
        if unit.is_cart():
            if unit.id not in go.UNIT_CACHE:
                unit.cluster_to_defend_id = LogicGlobals.game_state.map.get_cell_by_pos(unit.pos).citytile.cluster_to_defend_id
            LogicGlobals.RBS_cluster_carts.get(unit.cluster_to_defend_id, set()).add(unit.id)

    # if LogicGlobals.game_state.map.width > 12:
    #     update_builder_to_manager_ratio()
    # else:
        # update_spawn_to_research_ratio()


def gather_turn_information(player, opponent):
    blocked_positions = set()
    enemy_blocked_positions = set()

    # Not sure if this is good or not
    # for cell in LogicGlobals.game_state.map.cells():
    #     if cell.has_resource() and cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
    #         if cell.resource.amount < 500:
    #             blocked_positions = blocked_positions | cell.pos.adjacent_positions()

    # for unit in opponent.units:
    #     # TODO: This may cause issues in the endgame. This may have to depend on map size
    #     # if LogicGlobals.game_state.turn < 200:
    #     #     blocked_positions = blocked_positions | unit.pos.adjacent_positions()
    #     enemy_blocked_positions = enemy_blocked_positions | unit.pos.adjacent_positions()

    for __, city in opponent.cities.items():
        for tile in city.citytiles:
            blocked_positions.add(tile.pos)
            enemy_blocked_positions.add(tile.pos)

    LogicGlobals.pos_being_built = set()
    LogicGlobals.RESOURCES_BEING_COLLECTED = {}
    for unit in player.units:
        unit.check_for_task_completion(game_map=LogicGlobals.game_state.map, player=player)
        blocked_positions.add(unit.pos)
        for task, target in chain([unit.current_task if unit.current_task is not None else (None, None)], unit.task_q):
            if task == ValidActions.BUILD:
                LogicGlobals.pos_being_built.add(target)
            elif task == ValidActions.MANAGE:
                if target in player.cities:
                    player.cities[target].managers.add(unit.id)
                else:
                    unit.current_task = None
            elif task == ValidActions.COLLECT:
                LogicGlobals.RESOURCES_BEING_COLLECTED[target] = LogicGlobals.RESOURCES_BEING_COLLECTED.get(target, set()) | {unit.id}

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

    for city_id, city in LogicGlobals.player.cities.items():
        log(f"Turn {LogicGlobals.game_state.turn} city {city_id} managers: {city.managers}")

    for __, city in player.cities.items():
        for tile in city.citytiles:
            blocked_positions.discard(tile.pos)

    deleted_cities = set()
    for p in LogicGlobals.TBS_citytiles:
        if LogicGlobals.game_state.map.get_cell_by_pos(p).citytile is None:
            deleted_cities.add(p)
    LogicGlobals.TBS_citytiles = LogicGlobals.TBS_citytiles - deleted_cities

    deleted_cities = set()
    for p in LogicGlobals.RBS_citytiles:
        if LogicGlobals.game_state.map.get_cell_by_pos(p).citytile is None:
            deleted_cities.add(p)
    LogicGlobals.RBS_citytiles = LogicGlobals.RBS_citytiles - deleted_cities
    # for __, city in player.cities.items():
    #     for tile in city.citytiles:
    #         if LogicGlobals.game_state.turns_until_next_night > 3:  TODO: This fails for managing positions. his may have to depend on cluster resource amount
    #             blocked_positions.discard(tile.pos)
    #         else:
    #             blocked_positions.add(tile.pos)
    # log(f"Turn {LogicGlobals.game_state.turn} - City {city.cityid} managers: {city.managers}")

    return blocked_positions, enemy_blocked_positions


def unit_action_resolution(player, opponent):
    actions = []
    blocked_positions, enemy_blocked_positions = gather_turn_information(player, opponent)

    set_unit_strategy(player)

    for unit in sorted(player.units, key=lambda u: (u.cargo.wood, u.id if getpass.getuser() == 'Paul' else 0))[::-1]:
        if unit.current_task is None:
            unit.get_task_from_strategy(player)
            # unit.set_task_from_strategy(player)
            # set_unit_task(unit, player)

    switch_builds_if_needed()

    # for unit in player.units:
    #     action, target = unit.propose_action(player, LogicGlobals.game_state)
    #     log(f"Turn {LogicGlobals.game_state.turn}: Unit {unit.id} at {unit.pos} proposed action {action} with target {target}")
    #     if action == ValidActions.MOVE:
    #         blocked_positions.discard(unit.pos)

    debug_info = []
    units_wanting_to_move = set()
    for unit in player.units:
        action, target, *extra = unit.propose_action(
            player, LogicGlobals.game_state
        )
        log(
            f"Unit {unit.id} at {unit.pos} with cargo {unit.cargo} proposed action {action} with target {target}",
        )
        if action is None:
            continue
        elif action == ValidActions.BUILD:
            actions.append(unit.build_city(logs=debug_info))
            # if player.current_strategy == StrategyTypes.TIME_BASED:
            if unit.current_strategy == StrategyTypes.TIME_BASED:
                LogicGlobals.TBS_citytiles.add(unit.pos)
            # elif player.current_strategy == StrategyTypes.RESEARCH_BASED:
            elif unit.current_strategy == StrategyTypes.RESEARCH_BASED:
                LogicGlobals.RBS_citytiles.add(unit.pos)
        elif action == ValidActions.TRANSFER:
            actions.append(unit.transfer(*extra, logs=debug_info))
            unit.did_just_transfer = True
        elif action == ValidActions.PILLAGE:
            actions.append(unit.pillage(logs=debug_info))
        elif action == ValidActions.MOVE:
            select_movement_direction_for_unit(
                unit, target, blocked_positions,
                enemy_blocked_positions,
                register=units_wanting_to_move
            )
    actions, debug_info = resolve_unit_movement(
        player, units_wanting_to_move, blocked_positions, actions, debug_info
    )
    return actions, debug_info


def city_actions(actions):
    num_ct_can_act_this_turn = sum(
        city_tile.can_act() for _, city in LogicGlobals.player.cities.items() for city_tile in city.citytiles)
    spawned_this_round = 0
    for _, city in sorted(LogicGlobals.player.cities.items(), key=lambda pair: -int(pair[0].split("_")[1])):
        for city_tile in city.citytiles:
            if city_tile.can_act():
                if (len(LogicGlobals.player.units) == 0 or LogicGlobals.player.researched_uranium() or (
                        spawned_this_round <= num_ct_can_act_this_turn * STRATEGY_HYPERPARAMETERS["STARTER"][
                    f"SPAWN_TO_RESEARCH_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"]
                )) and len(LogicGlobals.player.units) + spawned_this_round < LogicGlobals.player.city_tile_count:
                    if LogicGlobals.player.current_strategy == StrategyTypes.STARTER:
                        actions.append(city_tile.build_worker())
                        spawned_this_round += 1
                        cluster = LogicGlobals.game_state.map.position_to_cluster(city_tile.pos)
                        if cluster is not None:
                            cluster.n_workers_spawned += 1
                else:
                    if LogicGlobals.player.current_strategy == StrategyTypes.STARTER and not LogicGlobals.player.researched_uranium():
                        actions.append(city_tile.research())
                        LogicGlobals.player.research_points += 1

    return actions


def agent(observation, configuration, include_debug_for_vis=True):

    ### Do not edit ###
    if observation["step"] == 0:
        LogicGlobals.game_state = Game(*observation["updates"][:2])
        LogicGlobals.game_state.update(observation["updates"][2:], observation.player)
        LogicGlobals.game_state.id = observation.player
        LogicGlobals.player.current_strategy = StrategyTypes.STARTER
    else:
        LogicGlobals.game_state.update(observation["updates"], observation.player)

    ### AI Code goes down here! ###
    update_logic_globals(LogicGlobals.player)

    # actions, debug_info = old_unit_action_resolution(player, opponent)
    actions, debug_info = unit_action_resolution(LogicGlobals.player, LogicGlobals.opponent)
    actions = city_actions(actions)
    actions = add_annotations(
        actions, LogicGlobals.player, LogicGlobals.game_state.map,
        debug_info, include_debug_for_vis
    )

    return actions




