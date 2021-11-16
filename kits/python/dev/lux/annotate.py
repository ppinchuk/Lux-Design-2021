def circle(x: int, y: int) -> str:
    return f"dc {x} {y}"


def x(x: int, y: int) -> str:
    return f"dx {x} {y}"


def line(x1: int, y1: int, x2: int, y2: int) -> str:
    return f"dl {x1} {y1} {x2} {y2}"


# text at cell on map
def text(x: int, y: int, message: str, fontsize: int = 16) -> str:
    return f"dt {x} {y} {fontsize} '{message}'"


# text besides map
def sidetext(message: str) -> str:
    return f"dst '{message}'"


def format_message(message):
    return message.replace(',', ';').replace('(', '[').replace(')', ']')


def add_annotations(actions, player, game_map, debug_info, include_debug_for_vis):
    if include_debug_for_vis:
        actions.append(
            sidetext(
                f"Current Strategy: {player.current_strategy}",
            )
        )
        actions.append(
            sidetext(
                f"Found {len(game_map.resource_clusters)} clusters",
            )
        )
        actions.append(
            sidetext(
                "Cluster - N_resource - N_defend - Score",
            )
        )
        for cluster in sorted(game_map.resource_clusters,
                              key=lambda c: (c.center_pos.x, c.center_pos.y)):
            actions.append(
                sidetext(
                    format_message(
                        f"{cluster.center_pos} - {cluster.total_amount:4d} - {cluster.n_to_block:1d} - {cluster.current_score:0.5f}"),
                )
            )
            # for pos in cluster.resource_positions:
            #     actions.append(annotate.circle(pos.x, pos.y))
            # for pos in cluster.pos_to_defend:
            #     actions.append(annotate.x(pos.x, pos.y))

        # actions.append(annotate.sidetext("STRATEGIES"))
        # for unit in LogicGlobals.player.units:
        #     actions.append(
        #         annotate.sidetext(
        #             f"{unit.id}: {unit.current_strategy}"
        #         )
        #     )

        actions.append(sidetext("GOAL TASKS"))

        for unit in player.units:
            # if unit.current_task is not None:
            #     __, target = unit.current_task
            #     if type(target) is Position:
            #         actions.append(
            #             annotate.line(unit.pos.x, unit.pos.y, target.x, target.y)
            #         )
            if unit.task_q:
                actions.append(
                    sidetext(
                        format_message(f"{unit.id}: {unit.task_q[-1][0]} at {unit.task_q[-1][1]} ")
                    )
                )
            else:
                actions.append(
                    sidetext(
                        f"{unit.id}: None"
                    )
                )

        actions.append(sidetext("CURRENT TASK"))

        for unit in player.units:
            if unit.current_task is None:
                actions.append(
                    sidetext(
                        f"{unit.id}: None"
                    )
                )
            else:
                actions.append(
                    sidetext(
                        format_message(f"{unit.id}: {unit.current_task[0]} at {unit.current_task[1]} ")
                    )
                )

        actions.append(sidetext("TASK QUEUE"))

        for unit in player.units:
            if unit.task_q:
                actions.append(
                    sidetext(
                        # annotate.format_message(f"{unit.id}: {unit.task_q[-1][0]} at {unit.task_q[-1][1]} ")
                        format_message(
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
                    sidetext(
                        f"{unit.id}: None"
                    )
                )

        actions.append(sidetext("ACTIONS"))

        for uid, action, target in debug_info:
            actions.append(
                sidetext(
                    format_message(f"{uid}: {action} with target {target}")
                )
            )

        actions.append(text(15, 15, "A"))
        return actions
