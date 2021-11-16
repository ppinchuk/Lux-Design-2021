import pytest
import sys
import agent as agent
import lux.game as g
import lux.strategy_utils as su
import lux.game_objects as go
import lux.game_map as gm
import lux.constants as c

"""
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'rp 0 0' <- research points (player id, num)
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'rp 1 0'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'r coal 0 3 419' <- resource (type, x, y, amount)
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'r wood 0 9 314'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'r uranium 6 10 331'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'u 0 0 u_1 13 7 0 0 0 0'    <- unit (type, team, id, x, y, cooldown, wood, coal, uranium)
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'u 0 1 u_2 13 16 0 0 0 0'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'c 0 c_1 0 23'  <- city (team, id, fuel, lightupkeep)
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'c 1 c_2 0 23'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'ct 0 c_1 13 7 0'   <- citytile (team, id, x, y, cooldown)
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'ct 1 c_2 13 16 0'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'ccd 13 7 6'   <- road (x, y, level)
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'ccd 13 16 6'
[WARN] (match_NF4VsaRK1hf9) - Agent 0 sent malformed command:  'D_DONE'
"""


class TestBuildLogic:
    @pytest.mark.parametrize("initialize_game", [12], indirect=['initialize_game'])
    def test_switch_builds_while_moving(self, initialize_game):
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 4 0 0 100 0 0',
                'u 0 1 u_2 2 3 0 100 0 0',
                'r wood 3 1 900',
                'c 0 c_1 0 23',
                'ct 0 c_1 3 2 0',
                'ct 0 c_1 4 2 0',
                'c 1 c_2 0 23',
                'ct 1 c_2 4 4 0',
            ], 0
        )

        #    0  1  2  3  4  5  6
        # 0 __ __ __ __ u1 __ __
        # 1 __ __ __ wo __ __ __
        # 2 __ __ __ c1 c1 __ __
        # 3 __ __ u2 __ __ __ __
        # 4 __ __ __ __ c2 __ __
        # 5 __ __ __ __ __ __ __
        # 6 __ __ __ __ __ __ __

        __ = agent.unit_actions(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        for u in c.LogicGlobals.player.units:
            assert u.current_task[0] == c.ValidActions.MOVE
            assert u.current_task[1] == gm.Position(4, 1)
            assert len(u.task_q) == 1
            assert u.task_q[0][0] == c.ValidActions.BUILD
            assert u.task_q[0][1] == gm.Position(4, 1)

        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 4 0 0 100 0 0',
                'u 0 1 u_2 2 3 0 100 0 0',
                'r wood 3 1 900',
                'c 0 c_1 0 23',
                'ct 0 c_1 3 2 0',
                'c 1 c_2 0 23',
                'ct 1 c_2 4 4 0',
            ], 0
        )

        #    0  1  2  3  4  5  6
        # 0 __ __ __ __ u1 __ __
        # 1 __ __ __ wo __ __ __
        # 2 __ __ __ c1 __ __ __
        # 3 __ __ u2 __ __ __ __
        # 4 __ __ __ __ c2 __ __
        # 5 __ __ __ __ __ __ __
        # 6 __ __ __ __ __ __ __

        __ = agent.unit_actions(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        for u in c.LogicGlobals.player.units:
            assert u.current_task[0] == c.ValidActions.MOVE
            assert u.current_task[1] == gm.Position(4, 2)
            assert len(u.task_q) == 1
            assert u.task_q[0][0] == c.ValidActions.BUILD
            assert u.task_q[0][1] == gm.Position(4, 2)

    @pytest.mark.parametrize("initialize_game", [12], indirect=['initialize_game'])
    def test_not_switch_builds_if_about_to_build(self, initialize_game):
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 4 0 0 100 0 0',
                'u 0 1 u_2 2 3 0 100 0 0',
                'r wood 3 1 900',
                'c 0 c_1 0 23',
                'ct 0 c_1 3 2 0',
                'ct 0 c_1 4 2 0',
                'c 1 c_2 0 23',
                'ct 1 c_2 4 4 0',
            ], 0
        )

        #    0  1  2  3  4  5  6
        # 0 __ __ __ __ u1 __ __
        # 1 __ __ __ wo __ __ __
        # 2 __ __ __ c1 c1 __ __
        # 3 __ __ u2 __ __ __ __
        # 4 __ __ __ __ c2 __ __
        # 5 __ __ __ __ __ __ __
        # 6 __ __ __ __ __ __ __

        __ = agent.unit_actions(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        for u in c.LogicGlobals.player.units:
            assert u.current_task[0] == c.ValidActions.MOVE
            assert u.current_task[1] == gm.Position(4, 1)
            assert len(u.task_q) == 1
            assert u.task_q[0][0] == c.ValidActions.BUILD
            assert u.task_q[0][1] == gm.Position(4, 1)

        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 4 1 0 100 0 0',
                'u 0 1 u_2 2 3 0 100 0 0',
                'r wood 3 1 900',
                'c 0 c_1 0 23',
                'ct 0 c_1 3 2 0',
                'c 1 c_2 0 23',
                'ct 1 c_2 4 4 0',
            ], 0
        )

        #    0  1  2  3  4  5  6
        # 0 __ __ __ __ __ __ __
        # 1 __ __ __ wo u1 __ __
        # 2 __ __ __ c1 __ __ __
        # 3 __ __ u2 __ __ __ __
        # 4 __ __ __ __ c2 __ __
        # 5 __ __ __ __ __ __ __
        # 6 __ __ __ __ __ __ __

        __ = agent.unit_actions(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        for u in c.LogicGlobals.player.units:
            assert u.current_task[0] == c.ValidActions.BUILD
            assert u.current_task[1] == gm.Position(4, 1)

    @pytest.mark.parametrize("initialize_game", [12], indirect=['initialize_game'])
    def test_switch_builds_while_collecting(self, initialize_game):
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 3 0 0 60 0 0',
                'u 0 1 u_2 2 3 0 100 0 0',
                'r wood 3 1 900',
                'c 0 c_1 0 23',
                'ct 0 c_1 3 2 0',
                'ct 0 c_1 4 2 0',
                'c 1 c_2 0 23',
                'ct 1 c_2 4 4 0',
            ], 0
        )

        #    0  1  2  3  4  5  6
        # 0 __ __ __ u1 __ __ __
        # 1 __ __ __ wo __ __ __
        # 2 __ __ __ c1 c1 __ __
        # 3 __ __ u2 __ __ __ __
        # 4 __ __ __ __ c2 __ __
        # 5 __ __ __ __ __ __ __
        # 6 __ __ __ __ __ __ __

        __ = agent.unit_actions(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        for u in c.LogicGlobals.player.units:
            assert u.current_task[0] == c.ValidActions.COLLECT
            assert u.current_task[1] == gm.Position(3, 1)
            assert len(u.task_q) == 1
            assert u.task_q[0][0] == c.ValidActions.BUILD
            assert u.task_q[0][1] == gm.Position(4, 1)

        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 3 1 0 80 0 0',
                'u 0 1 u_2 2 3 0 100 0 0',
                'r wood 3 1 900',
                'c 0 c_1 0 23',
                'ct 0 c_1 3 2 0',
                'c 1 c_2 0 23',
                'ct 1 c_2 4 4 0',
            ], 0
        )

        #    0  1  2  3  4  5  6
        # 0 __ __ __ u1 __ __ __
        # 1 __ __ __ wo __ __ __
        # 2 __ __ __ c1 __ __ __
        # 3 __ __ u2 __ __ __ __
        # 4 __ __ __ __ c2 __ __
        # 5 __ __ __ __ __ __ __
        # 6 __ __ __ __ __ __ __

        __ = agent.unit_actions(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        for u in c.LogicGlobals.player.units:
            assert u.current_task[0] == c.ValidActions.COLLECT
            assert u.current_task[1] == gm.Position(3, 1)
            assert len(u.task_q) == 1
            assert u.task_q[0][0] == c.ValidActions.BUILD
            assert u.task_q[0][1] == gm.Position(4, 2)

    @pytest.mark.parametrize("initialize_game", [12], indirect=['initialize_game'])
    def test_switch_builds_while_moving_to_collect(self, initialize_game):
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 4 0 0 60 0 0',
                'u 0 1 u_2 2 3 0 100 0 0',
                'r wood 3 1 900',
                'c 0 c_1 0 23',
                'ct 0 c_1 3 2 0',
                'ct 0 c_1 4 2 0',
                'c 1 c_2 0 23',
                'ct 1 c_2 4 4 0',
            ], 0
        )

        #    0  1  2  3  4  5  6
        # 0 __ __ __ __ u1 __ __
        # 1 __ __ __ wo __ __ __
        # 2 __ __ __ c1 c1 __ __
        # 3 __ __ u2 __ __ __ __
        # 4 __ __ __ __ c2 __ __
        # 5 __ __ __ __ __ __ __
        # 6 __ __ __ __ __ __ __

        __ = agent.unit_actions(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        for u in c.LogicGlobals.player.units:
            assert u.current_task[0] == c.ValidActions.MOVE
            assert u.current_task[1] == gm.Position(3, 1)
            assert len(u.task_q) == 2
            assert u.task_q[0][0] == c.ValidActions.COLLECT
            assert u.task_q[0][1] == gm.Position(3, 1)
            assert u.task_q[1][0] == c.ValidActions.BUILD
            assert u.task_q[1][1] == gm.Position(4, 1)

        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 4 0 0 80 0 0',
                'u 0 1 u_2 2 3 0 100 0 0',
                'r wood 3 1 900',
                'c 0 c_1 0 23',
                'ct 0 c_1 3 2 0',
                'c 1 c_2 0 23',
                'ct 1 c_2 4 4 0',
            ], 0
        )

        #    0  1  2  3  4  5  6
        # 0 __ __ __ __ u1 __ __
        # 1 __ __ __ wo __ __ __
        # 2 __ __ __ c1 __ __ __
        # 3 __ __ u2 __ __ __ __
        # 4 __ __ __ __ c2 __ __
        # 5 __ __ __ __ __ __ __
        # 6 __ __ __ __ __ __ __

        __ = agent.unit_actions(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        for u in c.LogicGlobals.player.units:
            assert u.current_task[0] == c.ValidActions.MOVE
            assert u.current_task[1] == gm.Position(3, 1)
            assert len(u.task_q) == 2
            assert u.task_q[0][0] == c.ValidActions.COLLECT
            assert u.task_q[0][1] == gm.Position(3, 1)
            assert u.task_q[1][0] == c.ValidActions.BUILD
            assert u.task_q[1][1] == gm.Position(4, 2)
