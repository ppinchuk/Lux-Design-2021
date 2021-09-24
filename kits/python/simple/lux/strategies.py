import sys
from .constants import StrategyTypes, LogicGlobals, ValidActions, STRATEGY_HYPERPARAMETERS, ResourceTypes
from .game_map import Position
from .strategy_utils import reset_unit_tasks, city_tile_to_build, compute_tbs_com, city_tile_to_build_tbs

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
        if LogicGlobals.unlocked_uranium and ResourceTypes.URANIUM in city.neighbor_resource_types:
            if len(city.citytiles) > len(city.managers) and len(city.managers) < city.light_upkeep / (15 * 80) + 1:
                unit.set_task(action=ValidActions.MANAGE, target=city.cityid)
                city.managers.add(unit.id)
                return

        if LogicGlobals.unlocked_coal and ResourceTypes.COAL in city.neighbor_resource_types:
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
            if closest_cluster is not None and (closest_cluster.n_workers_sent_to_colonize < closest_cluster.n_workers_spawned / STRATEGY_HYPERPARAMETERS['STARTER']['N_UNITS_SPAWN_BEFORE_COLONIZE']):
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
    if len(LogicGlobals.pos_being_built | LogicGlobals.TBS_citytiles) < STRATEGY_HYPERPARAMETERS['TBS']['LAST_DITCH_NUMBER_OF_WORKERS_RATIO'] * len(player.units):
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
