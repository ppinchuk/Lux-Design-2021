from itertools import chain
from .constants import ALL_DIRECTIONS, ResourceTypes, Directions
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
