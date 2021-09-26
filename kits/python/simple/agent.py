from lux.game import Game
from lux.game_map import Position
from lux.constants import ValidActions, log, StrategyTypes, LogicGlobals, ALL_DIRECTIONS, ResourceTypes, STRATEGY_HYPERPARAMETERS, GAME_CONSTANTS
from lux.strategies import starter_strategy, time_based_strategy, research_based_strategy
from collections import deque, Counter, UserDict
from itertools import chain
from lux import annotate
import sys
import lux.game_objects as go

### Define helper functions


def set_unit_task(unit, player):
    max_turn = STRATEGY_HYPERPARAMETERS[f"END_GAME_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"]
    if LogicGlobals.game_state.turn >= max_turn:
        if player.research_points < GAME_CONSTANTS["PARAMETERS"]["RESEARCH_REQUIREMENTS"]["COAL"]:
            time_based_strategy(unit, player)
        else:
            research_based_strategy(unit, player)
    else:
        starter_strategy(unit, player)

    # if player.researched_coal():
    #     research_based_strategy(unit, player)
    # else:
    #     starter_strategy(unit, player)
    # if LogicGlobals.game_state.turn < 200:
    #     starter_strategy(unit, player)
    # else:
    #     time_based_strategy(unit, player)


def update_logic_globals(player):
    if LogicGlobals.game_state.turn == 0:
        for unit in player.units:
            unit.has_colonized = True

    LogicGlobals.unlocked_coal = player.researched_coal()
    LogicGlobals.unlocked_uranium = player.researched_uranium()
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

    LogicGlobals.RBS_cluster_carts = {}
    for unit in LogicGlobals.player.units:
        if unit.is_cart():
            if unit.id not in go.UNIT_CACHE:
                unit.cluster_to_defend_id = LogicGlobals.game_state.map.get_cell_by_pos(unit.pos).citytile.cluster_to_defend_id
            LogicGlobals.RBS_cluster_carts.get(unit.cluster_to_defend_id, set()).add(unit.id)


def gather_turn_information(player, opponent):
    blocked_positions = set()
    enemy_blocked_positions = set()

    # Not sure if this is good or not
    # for cell in LogicGlobals.game_state.map.cells():
    #     if cell.has_resource() and cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
    #         if cell.resource.amount < 500:
    #             blocked_positions = blocked_positions | cell.pos.adjacent_positions()

    for unit in opponent.units:
        # TODO: This may cause issues in the endgame. This may have to depend on map size
        # if LogicGlobals.game_state.turn < 200:
        #     blocked_positions = blocked_positions | unit.pos.adjacent_positions()
        enemy_blocked_positions = enemy_blocked_positions | unit.pos.adjacent_positions()

    for __, city in opponent.cities.items():
        for tile in city.citytiles:
            enemy_blocked_positions.add(tile.pos)

    LogicGlobals.pos_being_built = set()
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

    for unit in sorted(player.units, key=lambda u: u.cargo.wood)[::-1]:
        if unit.current_task is None:
            set_unit_task(unit, player)

    # for unit in player.units:
    #     action, target = unit.propose_action(player, LogicGlobals.game_state)
    #     log(f"Turn {LogicGlobals.game_state.turn}: Unit {unit.id} at {unit.pos} proposed action {action} with target {target}")
    #     if action == ValidActions.MOVE:
    #         blocked_positions.discard(unit.pos)

    debug_info = []
    proposed_positions = {}
    units_wanting_to_move = set()
    for unit in player.units:
        action, target = unit.propose_action(
            player, LogicGlobals.game_state
        )
        log(
            f"Turn {LogicGlobals.game_state.turn}: Unit {unit.id} at {unit.pos} proposed action {action} with target {target}",
        )
        if action is None:
            continue
        elif action == ValidActions.BUILD:
            actions.append(unit.build_city(logs=debug_info))
            if player.current_strategy == StrategyTypes.TIME_BASED:
                LogicGlobals.TBS_citytiles.add(unit.pos)
            elif player.current_strategy == StrategyTypes.RESEARCH_BASED:
                LogicGlobals.RBS_citytiles.add(unit.pos)
        elif action == ValidActions.TRANSFER:
            actions.append(unit.transfer(*target, logs=debug_info))
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
                if new_pos in player.city_pos and LogicGlobals.game_state.turns_until_next_night < 3:
                    continue
                if not LogicGlobals.game_state.map.is_within_bounds(new_pos):
                    continue
                pos_contains_citytile = LogicGlobals.game_state.map.get_cell_by_pos(new_pos).citytile is not None
                if not LogicGlobals.game_state.map.is_within_bounds(new_pos) or (
                        pos_contains_citytile and unit.should_avoid_citytiles and unit.turns_spent_waiting_to_move < 5):
                    continue
                pos_to_check[direction] = new_pos
            if not pos_to_check:
                unit.turns_spent_waiting_to_move += 1
                if unit.pos not in player.city_pos:
                    blocked_positions.add(unit.pos)
                continue
            unit.dirs_to_move = unit.pos.sort_directions_by_pathing_distance(
                target, LogicGlobals.game_state.map,
                pos_to_check=pos_to_check, tolerance=3
            )
            unit.dirs_to_move = deque((d, pos_to_check[d]) for d in unit.dirs_to_move)
            if not unit.dirs_to_move:
                unit.turns_spent_waiting_to_move += 1
                if unit.pos not in player.city_pos:
                    blocked_positions.add(unit.pos)
                continue
            units_wanting_to_move.add(unit)

    while any(unit.dirs_to_move for unit in units_wanting_to_move):
        proposed_positions = dict()
        units_that_cant_move = set()
        for unit in units_wanting_to_move:
            if not unit.dirs_to_move:
                units_that_cant_move.add(unit)
                unit.turns_spent_waiting_to_move += 1
                if unit.pos not in player.city_pos:
                    blocked_positions.add(unit.pos)
                continue
            dir_to_move, new_pos = unit.dirs_to_move.popleft()
            proposed_positions.setdefault(new_pos, []).append((unit, dir_to_move))

        # log(f"{proposed_positions}")
        for pos, units in proposed_positions.items():
            if pos in blocked_positions:
                continue
            unit, direction = max(units, key=lambda pair: pair[0].turns_spent_waiting_to_move)
            unit.turns_spent_waiting_to_move = 0
            actions.append(unit.move(direction, logs=debug_info))
            units_that_cant_move.add(unit)
            blocked_positions.add(pos)

        units_wanting_to_move = units_wanting_to_move - units_that_cant_move

    return actions, debug_info


def agent(observation, configuration):

    ### Do not edit ###
    if observation["step"] == 0:
        LogicGlobals.game_state = Game(*observation["updates"][:2])
        LogicGlobals.game_state.update(observation["updates"][2:], observation.player)
        LogicGlobals.game_state.id = observation.player
    else:
        LogicGlobals.game_state.update(observation["updates"], observation.player)

    ### AI Code goes down here! ###
    update_logic_globals(LogicGlobals.player)

    # actions, debug_info = old_unit_action_resolution(player, opponent)
    actions, debug_info = unit_action_resolution(LogicGlobals.player, LogicGlobals.opponent)

    for _, city in LogicGlobals.player.cities.items():
        for city_tile in city.citytiles:
            if city_tile.can_act():
                if len(LogicGlobals.player.units) < LogicGlobals.player.city_tile_count:
                    if LogicGlobals.player.current_strategy == StrategyTypes.STARTER:
                        actions.append(city_tile.build_worker())
                        cluster = LogicGlobals.game_state.map.position_to_cluster(city_tile.pos)
                        if cluster is not None:
                            cluster.n_workers_spawned += 1
                    elif LogicGlobals.player.current_strategy == StrategyTypes.TIME_BASED:
                        if city_tile.pos in LogicGlobals.TBS_citytiles:
                            actions.append(city_tile.build_worker())
                    elif LogicGlobals.player.current_strategy == StrategyTypes.RESEARCH_BASED:
                        if city_tile.cluster_to_defend_id is not None:
                            existing_carts = LogicGlobals.RBS_cluster_carts.get(city_tile.cluster_to_defend_id, set())
                            if len(existing_carts) < STRATEGY_HYPERPARAMETERS['RBS'][LogicGlobals.RBS_rtype.upper()]['MAX_CARTS_PER_CLUSTER']:
                                actions.append(city_tile.build_cart())
                                existing_carts.add(f"Pending_cart_{city_tile.pos}")
                                LogicGlobals.RBS_cluster_carts[city_tile.cluster_to_defend_id] = existing_carts
                                continue
                        if city_tile.pos in LogicGlobals.RBS_citytiles:
                            actions.append(city_tile.build_worker())
                else:
                    if LogicGlobals.player.current_strategy == StrategyTypes.STARTER and not LogicGlobals.player.researched_uranium():
                        actions.append(city_tile.research())
                        LogicGlobals.player.research_points += 1

    # DEBUG STUFF

    actions.append(
        annotate.sidetext(
            f"Current Strategy: {LogicGlobals.player.current_strategy}",
        )
    )
    actions.append(
        annotate.sidetext(
            f"Found {len(LogicGlobals.game_state.map.resource_clusters)} clusters",
        )
    )
    actions.append(
        annotate.sidetext(
            "Cluster - N_resource - N_defend - Score",
        )
    )
    for cluster in sorted(LogicGlobals.game_state.map.resource_clusters, key=lambda c: (c.center_pos.x, c.center_pos.y)):
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

    for unit in LogicGlobals.player.units:
        # if unit.current_task is not None:
        #     __, target = unit.current_task
        #     if type(target) is Position:
        #         actions.append(
        #             annotate.line(unit.pos.x, unit.pos.y, target.x, target.y)
        #         )
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

    for unit in LogicGlobals.player.units:
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

    for unit in LogicGlobals.player.units:
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




