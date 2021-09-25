import sys
import statistics
from itertools import chain
from .constants import ALL_DIRECTIONS, ResourceTypes, Directions, LogicGlobals, STRATEGY_HYPERPARAMETERS, print
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
            clusters_to_colonize, key=lambda c: (c.total_amount, -c.center_pos.distance_to(unit_med_pos))
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
            ), -c.center_pos.distance_to(unit_med_pos))
        )[0]
        LogicGlobals.clusters_to_colonize_rbs[cluster_to_defend.id] = set()
