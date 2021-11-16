from lux.game import Game
from lux.game_map import Position
import lux.game_objects as go
import sys
# print("SOME RANDOM NUMBER:", random.random(), file=sys.stderr)
from lux.constants import ValidActions, log, print, StrategyTypes, LogicGlobals, ALL_DIRECTIONS, ResourceTypes, STRATEGY_HYPERPARAMETERS, GAME_CONSTANTS
from lux.strategies import starter_strategy, time_based_strategy, research_based_strategy, set_unit_task, set_unit_strategy
from lux.strategy_utils import compute_tbs_com, update_spawn_to_research_ratio, update_builder_to_manager_ratio
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

    units_that_should_not_switch_builds = {
        u.id for u in LogicGlobals.player.units if u.current_task and u.current_task[0] == ValidActions.BUILD and u.current_task[1] == u.pos and u.has_enough_resources_to_build
    }
    for cluster_id, builders in LogicGlobals.CLUSTER_ID_TO_BUILDERS.items():
        cluster_to_defend = LogicGlobals.game_state.map.get_cluster_by_id(cluster_id)
        if cluster_to_defend is None:
            continue
        units_that_should_switch_builds = set()
        if not cluster_to_defend.needs_defending_from_opponent:
            pos_should_be_built = {
                pos for pos in LogicGlobals.game_state.map.get_cluster_by_id(cluster_id).pos_to_defend
                if (
                        (pos not in LogicGlobals.pos_being_built)
                        and (LogicGlobals.game_state.map.get_cell_by_pos(pos).is_empty())
                        and pos not in LogicGlobals.opponent.unit_pos
                )
            }
            for unit_id in builders - units_that_should_not_switch_builds:
                unit = LogicGlobals.player.get_unit_by_id(unit_id)
                if unit is None:
                    continue
                current_build_pos = None
                if unit.current_task and unit.current_task[0] == ValidActions.BUILD:
                    current_build_pos = unit.current_task[1]
                else:
                    for task in unit.task_q:
                        if task[0] == ValidActions.BUILD:
                            current_build_pos = task[1]
                            break

                if current_build_pos is None:
                    print(f"BUILDER {unit.id} assigned to cluster {unit.cluster_to_defend_id} has no build task!!!")
                else:
                    if (current_build_pos in LogicGlobals.opponent.city_pos or current_build_pos in LogicGlobals.opponent.unit_pos) or (unit.pos.distance_to(current_build_pos) > unit.pos.distance_to(p) for p in pos_should_be_built):
                        units_that_should_switch_builds.add(unit)
                        pos_should_be_built.add(current_build_pos)
            if units_that_should_switch_builds:
                units_that_should_switch_builds = sorted(
                    units_that_should_switch_builds,
                    key=lambda u: -u.cargo_space_left()
                )
        else:
            pos_should_be_built = set()
            for pos in LogicGlobals.game_state.map.get_cluster_by_id(cluster_id).pos_to_defend:
                if len(pos_should_be_built) >= len(builders):
                    break
                cell = LogicGlobals.game_state.map.get_cell_by_pos(pos)
                if cell.is_empty() and cell.pos not in LogicGlobals.opponent.unit_pos:
                    pos_should_be_built.add(cell.pos)

            # if len(pos_should_be_built) < len(builders):
            #     continue

            for unit_id in builders - units_that_should_not_switch_builds:
                unit = LogicGlobals.player.get_unit_by_id(unit_id)
                if unit is None:
                    continue
                current_build_pos = None
                if unit.current_task and unit.current_task[0] == ValidActions.BUILD:
                    current_build_pos = unit.current_task[1]
                else:
                    for task in unit.task_q:
                        if task[0] == ValidActions.BUILD:
                            current_build_pos = task[1]
                            break
                if current_build_pos is None:
                    print(f"BUILDER {unit.id} assigned to cluster {unit.cluster_to_defend_id} has no build task!!!")
                else:
                    if current_build_pos in LogicGlobals.opponent.city_pos or current_build_pos in LogicGlobals.opponent.unit_pos:
                        units_that_should_switch_builds.add(unit)
                    elif current_build_pos in pos_should_be_built:
                        pos_should_be_built.discard(current_build_pos)
                    else:
                        units_that_should_switch_builds.add(unit)

        for unit in units_that_should_switch_builds:
            if pos_should_be_built:
                new_target = min(pos_should_be_built, key=lambda p: (unit.pos.distance_to(p), -sum(ap in LogicGlobals.player.city_pos for ap in p.adjacent_positions(include_center=False, include_diagonals=False)), p.x, p.y))
                pos_should_be_built.discard(new_target)
                # print(f"Switching BUILDER {unit.id} target to {new_target}")
                unit.remove_next_build_action()
                unit.set_task(ValidActions.BUILD, new_target)

    # for unit in player.units:
    #     action, target = unit.propose_action(player, LogicGlobals.game_state)
    #     log(f"Turn {LogicGlobals.game_state.turn}: Unit {unit.id} at {unit.pos} proposed action {action} with target {target}")
    #     if action == ValidActions.MOVE:
    #         blocked_positions.discard(unit.pos)

    debug_info = []
    proposed_positions = {}
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
            if target == unit.pos:
                continue
            blocked_positions.discard(unit.pos)

            pos_to_check = {}
            for direction in ALL_DIRECTIONS:
                new_pos = unit.pos.translate(direction, 1)
                # if new_pos in enemy_blocked_positions:
                #     continue
                # if new_pos in player.city_pos and LogicGlobals.game_state.turns_until_next_night < 3:
                #     continue
                if new_pos in enemy_blocked_positions:
                    continue
                if not LogicGlobals.game_state.map.is_within_bounds(new_pos):
                    continue
                if new_pos in unit.previous_pos:
                    continue
                if LogicGlobals.game_state.map.get_cell_by_pos(unit.pos).citytile is not None and LogicGlobals.game_state.turns_until_next_night <= 1 and LogicGlobals.game_state.map.get_cell_by_pos(new_pos).citytile is None and LogicGlobals.game_state.map.num_adjacent_resources(new_pos, include_center=True, include_wood_that_is_growing=True) == 0:
                    continue
                new_pos_contains_citytile = LogicGlobals.game_state.map.get_cell_by_pos(new_pos).citytile is not None
                if new_pos_contains_citytile and unit.should_avoid_citytiles:
                    tiles_not_blocked = {unit.pos, target}
                    for p in [unit.pos, target]:
                        cell = LogicGlobals.game_state.map.get_cell_by_pos(p)
                        if cell.citytile is not None:
                            city_id = cell.citytile.cityid
                            if city_id in LogicGlobals.player.cities:
                                tiles_not_blocked = tiles_not_blocked | {c.pos for c in LogicGlobals.player.cities[city_id].citytiles}
                    if new_pos not in tiles_not_blocked and unit.turns_spent_waiting_to_move < 5:
                        continue
                pos_to_check[direction] = new_pos
            if not pos_to_check:
                unit.turns_spent_waiting_to_move += 1
                if unit.pos not in player.city_pos:
                    blocked_positions.add(unit.pos)
                continue
            unit.dirs_to_move = unit.pos.sort_directions_by_turn_distance(
                target, LogicGlobals.game_state.map, cooldown=GAME_CONSTANTS['PARAMETERS']['UNIT_ACTION_COOLDOWN'][unit.type_str],
                pos_to_check=pos_to_check, tolerance=max(0, 2 * unit.turns_spent_waiting_to_move if (unit.current_task and (unit.current_task[0] == ValidActions.MANAGE)) else unit.turns_spent_waiting_to_move - 3),
                avoid_own_cities=unit.should_avoid_citytiles
            )
            unit.dirs_to_move = deque((d, pos_to_check[d]) for d in unit.dirs_to_move)
            if not unit.dirs_to_move:
                unit.turns_spent_waiting_to_move += 1
                if unit.pos not in player.city_pos:
                    blocked_positions.add(unit.pos)
                continue
            unit.move_target = target
            units_wanting_to_move.add(unit)

    proposed_positions = dict()
    while any(unit.dirs_to_move for unit in units_wanting_to_move) and (not proposed_positions or any(len(units) > 2 for units in proposed_positions.values())):
        units_with_movement_resolved = set()
        for unit in units_wanting_to_move:
            if not proposed_positions or not any(unit.id in [u[0].id for u in units] for units in proposed_positions.values()):
                if not unit.dirs_to_move:
                    units_with_movement_resolved.add(unit)
                    unit.turns_spent_waiting_to_move += 1
                    if unit.pos not in player.city_pos:
                        blocked_positions.add(unit.pos)
                    continue
                dir_to_move, new_pos = unit.dirs_to_move.popleft()
                proposed_positions.setdefault(new_pos, []).append((unit, dir_to_move))

        pos_to_discard = []
        for pos, units in sorted(proposed_positions.items(), key=lambda tup: (-len(tup[1]), tup[0].x, tup[0].y)):
        # for pos, units in proposed_positions.items():
            if pos in blocked_positions:
                pos_to_discard.append(pos)
                continue
            if pos in player.city_pos:
                for unit, direction in units:
                    unit.turns_spent_waiting_to_move = 0
                    actions.append(unit.move(direction, logs=debug_info))
                    units_with_movement_resolved.add(unit)
                pos_to_discard.append(pos)
            elif len(units) > 1:
                unit, direction = max(
                    units,
                    key=lambda pair: (
                        pair[0].pos in proposed_positions and any(u[0].pos == pos for u in proposed_positions[pair[0].pos]),
                        not pos == pair[0].move_target,
                        pair[0].turns_spent_waiting_to_move,
                        pair[0].is_building(),
                        pair[0].id if getpass.getuser() == 'Paul' else 0
                    )
                )
                unit.turns_spent_waiting_to_move = 0
                actions.append(unit.move(direction, logs=debug_info))
                units_with_movement_resolved.add(unit)
                blocked_positions.add(pos)
                pos_to_discard.append(pos)

        for pos in pos_to_discard:
            proposed_positions.pop(pos)

        units_wanting_to_move = units_wanting_to_move - units_with_movement_resolved

    units_with_movement_resolved = set()
    for unit in units_wanting_to_move:
        if not proposed_positions or not any(unit.id in [u[0].id for u in units] for units in proposed_positions.values()):
            if not unit.dirs_to_move:
                units_with_movement_resolved.add(unit)
                unit.turns_spent_waiting_to_move += 1
                if unit.pos not in player.city_pos:
                    blocked_positions.add(unit.pos)
                continue
            dir_to_move, new_pos = unit.dirs_to_move.popleft()
            proposed_positions.setdefault(new_pos, []).append((unit, dir_to_move))
    for pos, units in proposed_positions.items():
        if pos in blocked_positions:
            continue
        if pos in player.city_pos:
            for unit, direction in units:
                unit.turns_spent_waiting_to_move = 0
                actions.append(unit.move(direction, logs=debug_info))
                units_with_movement_resolved.add(unit)
        else:
            unit, direction = max(
                units,
                key=lambda pair: (
                    pair[0].pos in proposed_positions and any(u[0].pos == pos for u in proposed_positions[pair[0].pos]),
                    not pos == pair[0].move_target,
                    pair[0].turns_spent_waiting_to_move,
                    pair[0].is_building(),
                    pair[0].id if getpass.getuser() == 'Paul' else 0
                )
            )
            unit.turns_spent_waiting_to_move = 0
            actions.append(unit.move(direction, logs=debug_info))
            units_with_movement_resolved.add(unit)
            blocked_positions.add(pos)

    units_wanting_to_move = units_wanting_to_move - units_with_movement_resolved

    for unit in units_wanting_to_move:
        unit.turns_spent_waiting_to_move += 1

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

    # for _, city in LogicGlobals.player.cities.items():
    #     for city_tile in city.citytiles:
    #         if city_tile.can_act():
    #             if len(LogicGlobals.player.units) < LogicGlobals.player.city_tile_count:
    #                 if LogicGlobals.player.current_strategy == StrategyTypes.STARTER:
    #                     actions.append(city_tile.build_worker())
    #                     cluster = LogicGlobals.game_state.map.position_to_cluster(city_tile.pos)
    #                     if cluster is not None:
    #                         cluster.n_workers_spawned += 1
    #                 elif LogicGlobals.player.current_strategy == StrategyTypes.TIME_BASED:
    #                     if city_tile.pos in LogicGlobals.TBS_citytiles:
    #                         actions.append(city_tile.build_worker())
    #                 elif LogicGlobals.player.current_strategy == StrategyTypes.RESEARCH_BASED:
    #                     if city_tile.cluster_to_defend_id is not None:
    #                         existing_carts = LogicGlobals.RBS_cluster_carts.get(city_tile.cluster_to_defend_id, set())
    #                         if len(existing_carts) < STRATEGY_HYPERPARAMETERS['RBS'][LogicGlobals.RBS_rtype.upper()]['MAX_CARTS_PER_CLUSTER']:
    #                             actions.append(city_tile.build_cart())
    #                             existing_carts.add(f"Pending_cart_{city_tile.pos}")
    #                             LogicGlobals.RBS_cluster_carts[city_tile.cluster_to_defend_id] = existing_carts
    #                             continue
    #                     if city_tile.pos in LogicGlobals.RBS_citytiles:
    #                         actions.append(city_tile.build_worker())
    #             else:
    #                 if LogicGlobals.player.current_strategy == StrategyTypes.STARTER and not LogicGlobals.player.researched_uranium():
    #                     actions.append(city_tile.research())
    #                     LogicGlobals.player.research_points += 1

    # for _, city in LogicGlobals.player.cities.items():
    #     for city_tile in city.citytiles:
    #         if city_tile.can_act():
    #             if len(LogicGlobals.player.units) < LogicGlobals.player.city_tile_count:
    #                 if LogicGlobals.player.current_strategy == StrategyTypes.STARTER:
    #                     cluster = LogicGlobals.game_state.map.get_cluster_by_id(city_tile.cluster_to_defend_id)
    #                     if cluster is not None:
    #                         if len(LogicGlobals.CLUSTER_ID_TO_BUILDERS[cluster.id]) + len(LogicGlobals.CLUSTER_ID_TO_MANAGERS[cluster.id]) < len(cluster.pos_defended_by_player):
    #                             actions.append(city_tile.build_worker())
    #                             cluster.n_workers_spawned += 1
    #                             continue
    #             if LogicGlobals.player.current_strategy == StrategyTypes.STARTER and not LogicGlobals.player.researched_uranium():
    #                 actions.append(city_tile.research())
    #                 LogicGlobals.player.research_points += 1

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




