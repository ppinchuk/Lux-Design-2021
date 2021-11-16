import sys
import numpy as np
import statistics
from itertools import chain
import getpass
from .constants import ALL_DIRECTIONS, ResourceTypes, Directions, LogicGlobals, STRATEGY_HYPERPARAMETERS, print, GAME_CONSTANTS, ValidActions
from .game_map import Position


def reset_unit_tasks(player):
    for unit in player.units:
        unit.reset()


def city_tile_to_build(cluster, game_map, pos_being_built):
    if cluster is None:
        return None
    for pos in cluster.pos_to_defend:
        cell = game_map.get_cell_by_pos(pos)
        if cell.is_empty() and pos not in pos_being_built:
            return cell.pos
    return None


def city_tile_to_build_from_id(cluster_id, game_map, pos_being_built, unit):
    if cluster_id is None:
        return None
    cluster = game_map.get_cluster_by_id(cluster_id)
    if cluster.needs_defending_from_opponent:
        for pos in cluster.pos_to_defend:
            cell = game_map.get_cell_by_pos(pos)
            if cell.is_empty() and pos not in pos_being_built:
                return cell.pos
    else:
        try:
            return min(
                filter(
                    lambda p: p not in pos_being_built and game_map.get_cell_by_pos(p).is_empty(),
                    cluster.pos_to_defend
                ),
                key=lambda p: (unit.pos.distance_to(p), LogicGlobals.x_mult * p.x, LogicGlobals.y_mult * p.y))
        except ValueError:
            pass
    return None


def find_closest_cluster_to_colonize(unit):
    return min(
        LogicGlobals.clusters_to_colonize,
        key=lambda c: (unit.pos.distance_to(c.center_pos), c.id if getpass.getuser() == 'Paul' else 0)
        # NOTE: Currently does NOT prefer unlocked resources
    )


def find_closest_understaffed_cluster(unit):
    clusters = [c for c in LogicGlobals.game_state.map.resource_clusters if ((c.type.upper() == ResourceTypes.WOOD) or (c.type.upper() == ResourceTypes.COAL and LogicGlobals.player.researched_coal()) or (c.type.upper() == ResourceTypes.URANIUM and LogicGlobals.player.researched_uranium()))]
    if not clusters:
        clusters = LogicGlobals.game_state.map.resource_clusters
    if not clusters:
        return None
    return min(
        clusters,
        key=lambda c: (
            len(LogicGlobals.CLUSTER_ID_TO_BUILDERS.get(c.id, {})) + len(
                LogicGlobals.CLUSTER_ID_TO_MANAGERS.get(c.id, {})),
            unit.pos.distance_to(c.center_pos),
            LogicGlobals.x_mult * c.center_pos.x,
            LogicGlobals.y_mult * c.center_pos.y)
    )


def find_closest_cluster(unit):
    return LogicGlobals.game_state.map.position_to_cluster(
        unit.pos.find_closest_resource(
            player=LogicGlobals.player,
            game_map=LogicGlobals.game_state.map,
        )
    )


def set_unit_cluster_to_defend_id(unit, player):
    if unit.cluster_to_defend_id is None or LogicGlobals.game_state.map.get_cluster_by_id(unit.cluster_to_defend_id) is None or (
            LogicGlobals.game_state.map.get_cluster_by_id(unit.cluster_to_defend_id).total_amount <= 0
            and not STRATEGY_HYPERPARAMETERS["STARTER"]["CONTINUE_TO_BUILD_AFTER_RESOURCES_DEPLETED"]
            and len(LogicGlobals.CLUSTER_ID_TO_MANAGERS.get(unit.cluster_to_defend_id, set())) > STRATEGY_HYPERPARAMETERS["MANAGER_TO_CITY_RATIO"] * sum(len(LogicGlobals.player.cities[c_id].citytiles) for c_id in LogicGlobals.game_state.map.get_cluster_by_id(unit.cluster_to_defend_id).city_ids)
    ):
        if unit.cluster_to_defend_id is not None:
            LogicGlobals.CLUSTER_ID_TO_BUILDERS[unit.cluster_to_defend_id] = LogicGlobals.CLUSTER_ID_TO_BUILDERS.get(unit.cluster_to_defend_id, set()) - {unit.id}
            LogicGlobals.CLUSTER_ID_TO_MANAGERS[unit.cluster_to_defend_id] = LogicGlobals.CLUSTER_ID_TO_MANAGERS.get(unit.cluster_to_defend_id, set()) - {unit.id}
        unit.cluster_to_defend_id = None
        closest_city_tile_pos = unit.pos.find_closest_city_tile(player, game_map=LogicGlobals.game_state.map)

        if closest_city_tile_pos is not None:
            closest_cluster = LogicGlobals.game_state.map.position_to_cluster(closest_city_tile_pos)
        else:
            closest_cluster = None

        if not unit.has_colonized:
            if closest_cluster is not None:
                if closest_cluster.n_workers_sent_to_colonize <= closest_cluster.n_workers_spawned / STRATEGY_HYPERPARAMETERS['STARTER'][f'N_UNITS_SPAWN_BEFORE_COLONIZE_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}']:
                    if LogicGlobals.clusters_to_colonize:
                        unit.cluster_to_defend_id = find_closest_cluster_to_colonize(unit).id
                        closest_cluster.n_workers_sent_to_colonize += 1
                    else:
                        cluster = find_closest_understaffed_cluster(unit)
                        if cluster is None:
                            return
                        unit.cluster_to_defend_id = cluster.id
                        print(f"New cluster to defend was set for unit {unit.id}: {cluster.center_pos} {unit.cluster_to_defend_id}")
                else:
                    unit.cluster_to_defend_id = closest_cluster.id
                    print(f"New cluster to defend was set for unit {unit.id}: {closest_cluster.center_pos} {unit.cluster_to_defend_id}")
            else:
                cluster = find_closest_understaffed_cluster(unit)
                if cluster is None:
                    return
                unit.cluster_to_defend_id = cluster.id
                print(f"New cluster to defend was set for unit {unit.id}: {cluster.center_pos} {unit.cluster_to_defend_id}")
            return

        cluster = find_closest_understaffed_cluster(unit)

        if cluster is not None:
            unit.cluster_to_defend_id = cluster.id
            print(f"New cluster to defend was set for unit {unit.id}: {cluster.center_pos} ({unit.cluster_to_defend_id})")
        else:
            cluster = find_closest_cluster(unit)

        if cluster is not None:
            unit.cluster_to_defend_id = cluster.id
            print(f"New cluster to defend was set for unit {unit.id}: {cluster.center_pos} ({unit.cluster_to_defend_id})")


# def set_unit_cluster_to_defend_id(unit, player):
#     if unit.cluster_to_defend_id is None or unit.cluster_to_defend_id not in {rc.id for rc in LogicGlobals.game_state.map.resource_clusters}:
#         if unit.cluster_to_defend_id is not None:
#             LogicGlobals.CLUSTER_ID_TO_BUILDERS[unit.cluster_to_defend_id] = LogicGlobals.CLUSTER_ID_TO_BUILDERS.get(unit.cluster_to_defend_id, set()) - {unit.id}
#             LogicGlobals.CLUSTER_ID_TO_MANAGERS[unit.cluster_to_defend_id] = LogicGlobals.CLUSTER_ID_TO_MANAGERS.get(unit.cluster_to_defend_id, set()) - {unit.id}
#         unit.cluster_to_defend_id = None
#         if not unit.has_colonized and LogicGlobals.clusters_to_colonize:
#             closest_city_tile_pos = unit.pos.find_closest_city_tile(player, game_map=LogicGlobals.game_state.map)
#             if closest_city_tile_pos is not None:
#                 closest_cluster = LogicGlobals.game_state.map.position_to_cluster(closest_city_tile_pos)
#             else:
#                 closest_cluster = None
#
#             if closest_cluster is not None and (closest_cluster.n_workers_sent_to_colonize <= closest_cluster.n_workers_spawned / STRATEGY_HYPERPARAMETERS['STARTER']['N_UNITS_SPAWN_BEFORE_COLONIZE']):
#                 unit.cluster_to_defend_id = min(
#                     LogicGlobals.clusters_to_colonize,
#                     key=lambda c: unit.pos.distance_to(c.center_pos)  # NOTE: Currently does NOT prefer unlocked resources
#                 ).id
#                 closest_cluster.n_workers_sent_to_colonize += 1
#             else:
#                 cluster = LogicGlobals.game_state.map.position_to_cluster(
#                     unit.pos.find_closest_resource(
#                         player=player,
#                         game_map=LogicGlobals.game_state.map,
#                     )
#                 )
#                 if cluster is not None:
#                     unit.cluster_to_defend_id = cluster.id
#
#         else:
#             cluster = LogicGlobals.game_state.map.position_to_cluster(
#                 unit.pos.find_closest_resource(
#                     player=player,
#                     game_map=LogicGlobals.game_state.map,
#                 )
#             )
#             if cluster is not None:
#                 unit.cluster_to_defend_id = cluster.id
#         print(f"New cluster to defend was set for unit {unit.id}: {unit.cluster_to_defend_id}")


def switch_builds_if_needed():
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


def move_unit_in_direction(unit, direction, actions, debug_info, register):
    unit.turns_spent_waiting_to_move = 0
    actions.append(unit.move(direction, logs=debug_info))
    register.add(unit)


def compute_tbs_com(game_map):
    tot_amount = 0
    x_com = y_com = 0
    for cluster in game_map.resource_clusters:
        if cluster.type == ResourceTypes.WOOD:
            tot_amount += cluster.total_amount
            x_com += cluster.total_amount * cluster.center_pos.x
            y_com += cluster.total_amount * cluster.center_pos.y
    return Position(
        round(x_com / tot_amount), round(y_com / tot_amount)
    )


def directions_for_spiral():
    num_steps = 0
    ind = 0
    while True:
        if ind % 2 == 0:
            num_steps += 1
        for __ in range(num_steps):
            yield ALL_DIRECTIONS[ind % 4]
        ind += 1


def city_tile_to_build_tbs(com_pos, game_map, pos_being_built):
    if com_pos is None:
        return None

    next_pos = com_pos
    for d in chain([Directions.CENTER], directions_for_spiral()):
        next_pos = next_pos.translate(d, 1)
        if not game_map.is_within_bounds(next_pos):
            return None

        cell = game_map.get_cell_by_pos(next_pos)
        if cell.is_empty() and next_pos not in pos_being_built:
            return cell.pos

    return None


def set_rbs_rtype():
    if LogicGlobals.player.researched_uranium():
        LogicGlobals.RBS_rtype = ResourceTypes.URANIUM
    elif LogicGlobals.player.researched_coal():
        LogicGlobals.RBS_rtype = ResourceTypes.COAL
    else:
        LogicGlobals.RBS_rtype = ResourceTypes.WOOD


def med_position(positions):
    x_pos, y_pos = [], []
    for p in positions:
        x_pos.append(p.x)
        y_pos.append(p.y)
    return Position(
        statistics.median(x_pos),
        statistics.median(y_pos)
    )


def find_clusters_to_colonize_rbs():
    potential_clusters = [
        c for c in LogicGlobals.game_state.map.resource_clusters
        if c.type == LogicGlobals.RBS_rtype
    ]
    clusters_to_colonize = set()
    for cluster in potential_clusters:
        if any(p in LogicGlobals.opponent.city_pos for p in cluster.pos_to_defend):
            continue
        clusters_to_colonize.add(cluster)

    max_num_clusters = len(LogicGlobals.player.unit_ids) // STRATEGY_HYPERPARAMETERS['RBS'][LogicGlobals.RBS_rtype.upper()]['WORKERS_INITIAL']
    print(f"Player has {len(LogicGlobals.player.unit_ids)} units, so num RBS clusters is: {max_num_clusters} (Minimum {STRATEGY_HYPERPARAMETERS['RBS'][LogicGlobals.RBS_rtype.upper()]['WORKERS_INITIAL']} per cluster)")
    if len(clusters_to_colonize) > max_num_clusters:
        unit_med_pos = med_position([u.pos for u in LogicGlobals.player.units])
        clusters_to_colonize = sorted(
            clusters_to_colonize,
            key=lambda c: (c.total_amount * (GAME_CONSTANTS["PARAMETERS"]["MAX_DAYS"] - LogicGlobals.game_state.turn) / (c.center_pos.distance_to(unit_med_pos) * 2.5), -c.center_pos.distance_to(unit_med_pos), c.id if getpass.getuser() == 'Paul' else 0)
        )[:-1-max_num_clusters:-1]

    for c in clusters_to_colonize:
        LogicGlobals.clusters_to_colonize_rbs[c.id] = set()

    if not LogicGlobals.clusters_to_colonize_rbs:
        unit_med_pos = med_position([u.pos for u in LogicGlobals.player.units])
        cluster_to_defend = sorted(
            potential_clusters,
            key=lambda c: (sum(
                p in LogicGlobals.opponent.city_pos
                for p in c.pos_to_defend
            ), -c.center_pos.distance_to(unit_med_pos), c.id if getpass.getuser() == 'Paul' else 0)
        )[0]
        LogicGlobals.clusters_to_colonize_rbs[cluster_to_defend.id] = set()


def update_spawn_to_research_ratio():
    if (LogicGlobals.game_state.turn < STRATEGY_HYPERPARAMETERS['NUM_TURNS_BEFORE_RESEARCH_EXP_FIT']) or ((LogicGlobals.player.research_points - LogicGlobals.RP_AT_LAST_ADJUSTMENT) < STRATEGY_HYPERPARAMETERS["NUM_RP_BETWEEN_RATIO_ADJUSTMENTS"]):
        return
    elif LogicGlobals.player.researched_uranium() or LogicGlobals.opponent.researched_uranium():
        STRATEGY_HYPERPARAMETERS["STARTER"][f"SPAWN_TO_RESEARCH_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] = STRATEGY_HYPERPARAMETERS["STARTER"][f"SPAWN_TO_RESEARCH_STARTER_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"]
        STRATEGY_HYPERPARAMETERS["STARTER"][f"BUILDER_TO_MANAGER_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] = STRATEGY_HYPERPARAMETERS["STARTER"][f"BUILDER_TO_MANAGER_STARTER_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"]
        STRATEGY_HYPERPARAMETERS["STARTER"][f"N_UNITS_SPAWN_BEFORE_COLONIZE_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] = STRATEGY_HYPERPARAMETERS["STARTER"][f"N_UNITS_SPAWN_BEFORE_COLONIZE_STARTER_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"]
        return

    m1, b1 = np.polyfit(np.arange(len(LogicGlobals.game_state.player_rp)) + 1, np.log(LogicGlobals.game_state.player_rp), 1)
    m2, b2 = np.polyfit(np.arange(len(LogicGlobals.game_state.opponent_rp)) + 1, np.log(LogicGlobals.game_state.opponent_rp), 1)
    if m1 <= 0 or m2 <= 0:
        return
    player_research_turn = (np.log(GAME_CONSTANTS["PARAMETERS"]["RESEARCH_REQUIREMENTS"]["URANIUM"]) - b1) / m1
    opponent_research_turn = (np.log(GAME_CONSTANTS["PARAMETERS"]["RESEARCH_REQUIREMENTS"]["URANIUM"]) - b2) / m2
    if player_research_turn > opponent_research_turn:
        LogicGlobals.RP_AT_LAST_ADJUSTMENT = LogicGlobals.player.research_points
        # STRATEGY_HYPERPARAMETERS["STARTER"][f"SPAWN_TO_RESEARCH_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] = max(
        #     STRATEGY_HYPERPARAMETERS["STARTER"][f'DECREASE_SPAWN_TO_RESEARCH_RATIO_AMOUNT_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.neight}'],
        #     STRATEGY_HYPERPARAMETERS["STARTER"][f"SPAWN_TO_RESEARCH_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"]  - STRATEGY_HYPERPARAMETERS["STARTER"][f'DECREASE_SPAWN_TO_RESEARCH_RATIO_AMOUNT_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.neight}']
        # )
        STRATEGY_HYPERPARAMETERS["STARTER"][f"SPAWN_TO_RESEARCH_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] = STRATEGY_HYPERPARAMETERS["STARTER"][f"SPAWN_TO_RESEARCH_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] * (1 - STRATEGY_HYPERPARAMETERS["STARTER"][f'DECREASE_SPAWN_TO_RESEARCH_RATIO_AMOUNT_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.neight}'])
        STRATEGY_HYPERPARAMETERS["STARTER"][f"BUILDER_TO_MANAGER_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] = STRATEGY_HYPERPARAMETERS["STARTER"][f"BUILDER_TO_MANAGER_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] * (1 + STRATEGY_HYPERPARAMETERS["STARTER"][f'DECREASE_SPAWN_TO_RESEARCH_RATIO_AMOUNT_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.neight}'])
        STRATEGY_HYPERPARAMETERS["STARTER"][f"N_UNITS_SPAWN_BEFORE_COLONIZE_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] = STRATEGY_HYPERPARAMETERS["STARTER"][f"N_UNITS_SPAWN_BEFORE_COLONIZE_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] * (1 + STRATEGY_HYPERPARAMETERS["STARTER"][f'DECREASE_SPAWN_TO_RESEARCH_RATIO_AMOUNT_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.neight}'])

    elif player_research_turn + 10 < opponent_research_turn:
        STRATEGY_HYPERPARAMETERS["STARTER"][f"SPAWN_TO_RESEARCH_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] = STRATEGY_HYPERPARAMETERS["STARTER"][f"SPAWN_TO_RESEARCH_STARTER_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"]
        STRATEGY_HYPERPARAMETERS["STARTER"][f"BUILDER_TO_MANAGER_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] = STRATEGY_HYPERPARAMETERS["STARTER"][f"BUILDER_TO_MANAGER_STARTER_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"]
        STRATEGY_HYPERPARAMETERS["STARTER"][f"N_UNITS_SPAWN_BEFORE_COLONIZE_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] = STRATEGY_HYPERPARAMETERS["STARTER"][f"N_UNITS_SPAWN_BEFORE_COLONIZE_STARTER_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"]


def update_builder_to_manager_ratio():
    slope = (STRATEGY_HYPERPARAMETERS["STARTER"][f"BUILDER_TO_MANAGER_STARTER_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] - 1) / 350
    STRATEGY_HYPERPARAMETERS["STARTER"][f"BUILDER_TO_MANAGER_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"] = max(0, min(1, slope * (LogicGlobals.game_state.turn - 350) + STRATEGY_HYPERPARAMETERS["STARTER"][f"BUILDER_TO_MANAGER_STARTER_RATIO_{LogicGlobals.game_state.map.width}X{LogicGlobals.game_state.map.height}"]))
