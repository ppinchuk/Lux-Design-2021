from lux.game import Game
# from lux.game_map import MAP_CACHE
from lux.constants import Constants, ALL_DIRECTIONS, ALL_DIRECTIONS_AND_CENTER, ValidActions, print_out, StrategyTypes
from lux.strategy_utils import *
from collections import deque, Counter, UserDict
from itertools import chain
from lux.game_constants import STRATEGY_CONSTANTS
from lux import annotate
import math
import sys
import lux.game_objects as go

### Define helper functions

DIRECTIONS = Constants.DIRECTIONS

# if our cluster is separate from other base, build around them.
# Prefer 2x2 clusters


def starter_strategy(unit, player):
    if player.current_strategy != StrategyTypes.STARTER:
        player.current_strategy = StrategyTypes.STARTER
        reset_unit_tasks(player)
        LogicGlobals.pos_being_built = set()

    if not unit.can_act():
        return

    for __, city in player.cities.items():
        if LogicGlobals.unlocked_uranium and Constants.RESOURCE_TYPES.URANIUM in city.neighbor_resource_types:
            if len(city.citytiles) > len(city.managers) and len(city.managers) < city.light_upkeep / (15 * 80) + 1:
                unit.set_task(action=ValidActions.MANAGE, target=city.cityid)
                city.managers.add(unit.id)
                return

        if LogicGlobals.unlocked_coal and Constants.RESOURCE_TYPES.COAL in city.neighbor_resource_types:
            if len(city.citytiles) > len(city.managers) and len(city.managers) < city.light_upkeep / (15 * 50) + 1:
                unit.set_task(action=ValidActions.MANAGE, target=city.cityid)
                city.managers.add(unit.id)
                return

    # if not unit.has_colonized and LogicGlobals.clusters_to_colonize:
    #     # cluster_to_defend = min(
    #     #     LogicGlobals.clusters_to_colonize,
    #     #     key=lambda c: min(unit.pos.distance_to(p) for p in c.pos_to_defend)
    #     # )
    #     cluster_to_defend = max(
    #         LogicGlobals.clusters_to_colonize,
    #         key=lambda c: c.current_score
    #     )

    if unit.cluster_to_defend is None or unit.cluster_to_defend not in LogicGlobals.game_state.map.resource_clusters:
        if not unit.has_colonized and LogicGlobals.clusters_to_colonize:
            closest_cluster = LogicGlobals.game_state.map.position_to_cluster(
                unit.pos.find_closest_city_tile(player, game_map=LogicGlobals.game_state.map)
            )
            if closest_cluster is not None and (closest_cluster.n_workers_sent_to_colonize < closest_cluster.n_workers_spawned / STRATEGY_CONSTANTS['STARTER']['N_UNITS_SPAWN_BEFORE_COLONIZE']):
                unit.cluster_to_defend = max(
                    LogicGlobals.clusters_to_colonize,
                    key=lambda c: c.current_score
                )
                closest_cluster.n_workers_sent_to_colonize += 1
            else:
                unit.cluster_to_defend = LogicGlobals.game_state.map.position_to_cluster(
                    unit.pos.find_closest_resource(
                        player=player,
                        game_map=LogicGlobals.game_state.map,
                    )
                )

        else:
            unit.cluster_to_defend = LogicGlobals.game_state.map.position_to_cluster(
                unit.pos.find_closest_resource(
                    player=player,
                    game_map=LogicGlobals.game_state.map,
                )
            )

    # TODO: WHAT IF THERE IS NO MORE WOOD??
    new_city_pos = city_tile_to_build(
        unit.cluster_to_defend,
        LogicGlobals.game_state.map,
        LogicGlobals.pos_being_built
    )
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


def time_based_strategy(unit, player):
    """

    0.) Stop all city research efforts
    1.) Choose center of mass (COM) point to all collectable resource clusters
         available (most likely all the wood ones)
    2.) Move `LAST_DITCH_NUMBER_OF_WORKERS` number of closest workers with 100 wood units to COM
    3.) Build fully connected city (not around a cluster just a 'circular' form)
    4.) Assign remainder of workers to dump their resources into city for fuel
    5.) Spawn workers at all cities
    6.) Divide workers into groups based on number of wood clusters available
    7.) Move workers to available resources and collect then return
    8.) Have `LAST_DITCH_RESOURCE_DUMP_RATIO` amount of workers dump resources as fuel
    9.) Have remainder build cities
    10.) Repeat 5.) - 10.)

    *** NOTE: Workers and carts need to move to next cluster if current cluster is
         depleted ***


    Parameters
    ----------
    unit
    player


    """
    if player.current_strategy != StrategyTypes.TIME_BASED:
        player.current_strategy = StrategyTypes.TIME_BASED
        reset_unit_tasks(player)
        LogicGlobals.pos_being_built = set()

    if LogicGlobals.TBS_COM is None:
        LogicGlobals.TBS_COM = compute_tbs_com(LogicGlobals.game_state.map)
        print(f"New TBS COM is: {LogicGlobals.TBS_COM}", file=sys.stderr)

    # TODO: WHAT IF THERE IS NO MORE WOOD??
    if len(LogicGlobals.pos_being_built | LogicGlobals.TBS_citytiles) < STRATEGY_CONSTANTS['TBS']['LAST_DITCH_NUMBER_OF_WORKERS_RATIO'] * len(player.units):
        new_city_pos = city_tile_to_build_tbs(
            LogicGlobals.TBS_COM,
            LogicGlobals.game_state.map,
            LogicGlobals.pos_being_built
        )
        if new_city_pos is not None:
            unit.set_task(action=ValidActions.BUILD, target=new_city_pos)
            LogicGlobals.pos_being_built.add(new_city_pos)
            LogicGlobals.TBS_citytiles.add(new_city_pos)
            return

    center_city_tile_pos = {
        p for p in LogicGlobals.TBS_citytiles
        if LogicGlobals.game_state.map.get_cell_by_pos(p).citytile is not None
    }
    if center_city_tile_pos:
        print("SHOULD SET MANAGE!!!!!", file=sys.stderr)
        city_id = LogicGlobals.game_state.map.get_cell_by_pos(
            center_city_tile_pos.pop()
        ).citytile.cityid
        unit.set_task(action=ValidActions.MANAGE, target=city_id)
    # if LogicGlobals.TBS_citytiles:
    #     print("SHOULD SET MANAGE!!!!!", file=sys.stderr)
    #     city_id = LogicGlobals.game_state.map.get_cell_by_pos(
    #         list(LogicGlobals.TBS_citytiles)[0]
    #     ).citytile.cityid
    #     unit.set_task(action=ValidActions.MANAGE, target=city_id)
    else:
        if unit.cargo_space_left() > 0:
            closest_resource = unit.pos.find_closest_resource(
                    player, LogicGlobals.game_state.map
                )
            if closest_resource is not None:
                unit.set_task(action=ValidActions.COLLECT, target=closest_resource)
                return
        else:
            closest_cluster = LogicGlobals.game_state.map.position_to_cluster(
                LogicGlobals.TBS_COM.find_closest_resource(
                    player, LogicGlobals.game_state.map
                )
            )
            # mid_point = Position(
            #     round((LogicGlobals.TBS_COM.x - closest_cluster.center_pos.x) / 2 + closest_cluster.center_pos.x),
            #     round((LogicGlobals.TBS_COM.y - closest_cluster.center_pos.y) / 2 + closest_cluster.center_pos.y),
            # )
            # mid_point = Position(
            #     round(2 * LogicGlobals.TBS_COM.x - closest_cluster.center_pos.x),
            #     round(2 * LogicGlobals.TBS_COM.y - closest_cluster.center_pos.y),
            # )
            mid_point = Position(
                round((LogicGlobals.TBS_COM.x - closest_cluster.center_pos.x) * 0.65 + closest_cluster.center_pos.x),
                round((LogicGlobals.TBS_COM.y - closest_cluster.center_pos.y) * 0.65 + closest_cluster.center_pos.y),
            )
            unit.set_task(
                ValidActions.MOVE,
                target=unit.pos.translate(unit.pos.direction_to(mid_point), 1)
            )
    # if any(
    #         LogicGlobals.game_state.map.get_cell_by_pos(p).resource is not None
    #         for p in unit.pos.adjacent_positions()
    # ):
    #     unit.set_task(ValidActions.MOVE, target=LogicGlobals.TBS_COM.translate(Constants.DIRECTIONS.WEST, 2))


def set_unit_task(unit, player):
    if LogicGlobals.game_state.turn < 200:
        starter_strategy(unit, player)
    else:
        time_based_strategy(unit, player)


class LogicGlobals:
    game_state = Game()
    player = None
    start_tile = None
    unlocked_coal = False
    unlocked_uranium = False
    cities = None
    pos_being_built = set()
    resource_cluster_to_defend = None
    clusters_to_colonize = set()
    max_resource_cluster_amount = 0
    TBS_COM = None
    TBS_citytiles = set()


def update_logic_globals(player):
    if LogicGlobals.game_state.turn == 0:
        for unit in player.units:
            unit.has_colonized = True
        # LogicGlobals.game_state.map.find_clusters()
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
    for cluster in LogicGlobals.game_state.map.resource_clusters:
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

    if LogicGlobals.resource_cluster_to_defend is not None and (all(
            LogicGlobals.game_state.map.get_cell_by_pos(p).citytile is not None for p in
            LogicGlobals.resource_cluster_to_defend.pos_to_defend) or LogicGlobals.resource_cluster_to_defend.total_amount <= 0):
        LogicGlobals.resource_cluster_to_defend = None

    units_lost = set(go.UNIT_CACHE) - player.unit_ids
    for id_ in units_lost:
        go.UNIT_CACHE.pop(id_)


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
        print(f"Turn {LogicGlobals.game_state.turn} city {city_id} managers: {city.managers}", file=print_out)

    for __, city in player.cities.items():
        for tile in city.citytiles:
            blocked_positions.discard(tile.pos)

    deleted_cities = set()
    for p in LogicGlobals.TBS_citytiles:
        if LogicGlobals.game_state.map.get_cell_by_pos(p).citytile is None:
            deleted_cities.add(p)
    LogicGlobals.TBS_citytiles = LogicGlobals.TBS_citytiles - deleted_cities

    # for __, city in player.cities.items():
    #     for tile in city.citytiles:
    #         if LogicGlobals.game_state.turns_until_next_night > 3:  TODO: This fails for managing positions. his may have to depend on cluster resource amount
    #             blocked_positions.discard(tile.pos)
    #         else:
    #             blocked_positions.add(tile.pos)
    # print(f"Turn {LogicGlobals.game_state.turn} - City {city.cityid} managers: {city.managers}", file=print_out)

    return blocked_positions, enemy_blocked_positions


def unit_action_resolution(player, opponent):
    actions = []
    blocked_positions, enemy_blocked_positions = gather_turn_information(player, opponent)

    for unit in sorted(player.units, key=lambda u: u.cargo.wood)[::-1]:
        if unit.current_task is None:
            set_unit_task(unit, player)

    # for unit in player.units:
    #     action, target = unit.propose_action(player, LogicGlobals.game_state)
    #     print(f"Turn {LogicGlobals.game_state.turn}: Unit {unit.id} at {unit.pos} proposed action {action} with target {target}", file=print_out)
    #     if action == ValidActions.MOVE:
    #         blocked_positions.discard(unit.pos)

    debug_info = []
    proposed_positions = {}
    units_wanting_to_move = set()
    for unit in player.units:
        action, target = unit.propose_action(
            player, LogicGlobals.game_state
        )
        print(
            f"Turn {LogicGlobals.game_state.turn}: Unit {unit.id} at {unit.pos} proposed action {action} with target {target}",
            file=print_out)
        if action is None:
            continue
        elif action == ValidActions.BUILD:
            actions.append(unit.build_city(logs=debug_info))
            if player.current_strategy == StrategyTypes.TIME_BASED:
                LogicGlobals.TBS_citytiles.add(unit.pos)
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

        # print(f"{proposed_positions}", file=print_out)
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
        LogicGlobals.game_state._initialize(observation["updates"])
        LogicGlobals.game_state._update(observation["updates"][2:], observation)
        LogicGlobals.game_state.id = observation.player
    else:
        LogicGlobals.game_state._update(observation["updates"], observation)

    ### AI Code goes down here! ###
    player = LogicGlobals.player = LogicGlobals.game_state.players[observation.player]
    opponent = LogicGlobals.game_state.players[(observation.player + 1) % 2]
    width, height = LogicGlobals.game_state.map.width, LogicGlobals.game_state.map.height
    update_logic_globals(player)

    # actions, debug_info = old_unit_action_resolution(player, opponent)
    actions, debug_info = unit_action_resolution(player, opponent)

    for _, city in player.cities.items():
        for city_tile in city.citytiles:
            if city_tile.can_act():
                if len(player.units) < player.city_tile_count:
                    if player.current_strategy == StrategyTypes.STARTER:
                        actions.append(city_tile.build_worker())
                        cluster = LogicGlobals.game_state.map.position_to_cluster(city_tile.pos)
                        if cluster is not None:
                            cluster.n_workers_spawned += 1
                    elif player.current_strategy == StrategyTypes.TIME_BASED:
                        if city_tile.pos in LogicGlobals.TBS_citytiles:
                            actions.append(city_tile.build_worker())
                else:
                    if player.current_strategy == StrategyTypes.STARTER and not player.researched_uranium():
                        actions.append(city_tile.research())
                        player.research_points += 1

    # DEBUG STUFF

    actions.append(
        annotate.sidetext(
            f"Current Strategy: {player.current_strategy}",
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

    for unit in player.units:
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




