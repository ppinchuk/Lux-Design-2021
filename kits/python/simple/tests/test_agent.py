import pytest
import sys
import agent as agent
import lux.game as g
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


class TestManageAction:
    def test_manage_with_no_more_resources(self):
        c.LogicGlobals.game_state = g.Game(0, "3 3")
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 1 0 0 0 0 0',
                'c 0 c_1 0 23',
                'ct 0 c_1 1 1 0',
                'ccd 1 1 6',
            ], 0
        )

        #    0  1  2
        # 0 __ u1 __
        # 1 __ __ __
        # 2 __ __ __

        unit_actions_this_turn = {
            'u_1': (c.ValidActions.MANAGE, 'c_1'),
        }

        for unit in c.LogicGlobals.player.units:
            unit.set_task(*unit_actions_this_turn[unit.id])

        actions, debug = agent.unit_action_resolution(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        assert not actions


class TestUnitMovement:
    def test_single_unit_movement(self):
        c.LogicGlobals.game_state = g.Game(0, "3 3")
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 1 0 0 0 0 0',
            ], 0
        )

        #    0  1  2
        # 0 __ u1 __
        # 1 __ __ __
        # 2 __ __ __

        unit_actions_this_turn = {
            'u_1': (c.ValidActions.MOVE, gm.Position(1, 2)),
        }

        for unit in c.LogicGlobals.player.units:
            unit.set_task(*unit_actions_this_turn[unit.id])

        actions, debug = agent.unit_action_resolution(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        assert actions == ['m u_1 s']

    def test_movement_with_road(self):
        c.LogicGlobals.game_state = g.Game(0, "3 3")
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 0 0 0 0 0 0',
                'ccd 0 1 6',
                'ccd 1 1 6',
                'ccd 2 1 6',
                'ccd 2 2 6',
            ], 0
        )

        #    0  1  2
        # 0 u1 __ __
        # 1 == == ==
        # 2 __ __ ==

        unit_actions_this_turn = {
            'u_1': (c.ValidActions.MOVE, gm.Position(2, 2)),
        }

        for unit in c.LogicGlobals.player.units:
            unit.set_task(*unit_actions_this_turn[unit.id])

        actions, debug = agent.unit_action_resolution(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        assert len(actions) == ['m u_1 s']

    def test_moving_from_city_tile_at_night(self):
        c.LogicGlobals.game_state = g.Game(0, "3 3")

        for _ in range(c.GAME_CONSTANTS['PARAMETERS']['DAY_LENGTH'] - 1):
            c.LogicGlobals.game_state.update(
                [
                    'u 0 0 u_1 0 0 0 0 0 0',
                    'c 0 c_1 0 23',
                    'ct 0 c_1 0 0 0',
                    'ccd 0 0 6',
                ], 0
            )

        #    0  1  2
        # 0 u1 __ __
        # 1 __ __ __
        # 2 __ __ __

        for _ in range(c.GAME_CONSTANTS['PARAMETERS']['NIGHT_LENGTH'] + 1):
            c.LogicGlobals.game_state.update(
                [
                    'u 0 0 u_1 0 0 0 0 0 0',
                    'c 0 c_1 0 23',
                    'ct 0 c_1 0 0 0',
                    'ccd 0 0 6',
                ], 0
            )

            unit_actions_this_turn = {
                'u_1': (c.ValidActions.MOVE, gm.Position(2, 2)),
            }

            for unit in c.LogicGlobals.player.units:
                unit.set_task(*unit_actions_this_turn[unit.id])

            actions, debug = agent.unit_action_resolution(
                c.LogicGlobals.player, c.LogicGlobals.opponent
            )

            assert not actions

        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 0 0 0 0 0 0',
                'c 0 c_1 0 23',
                'ct 0 c_1 0 0 0',
                'ccd 0 0 6',
            ], 0
        )

        unit_actions_this_turn = {
            'u_1': (c.ValidActions.MOVE, gm.Position(2, 2)),
        }

        for unit in c.LogicGlobals.player.units:
            unit.set_task(*unit_actions_this_turn[unit.id])

        actions, debug = agent.unit_action_resolution(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        assert len(actions) == 1


class TestUnitCollisions:
    def test_collision_when_equidistant_move_loc(self):
        c.LogicGlobals.game_state = g.Game(0, "3 3")
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 0 0 0 0 0 0',
                'u 0 0 u_2 1 1 0 0 0 0',
            ], 0
        )

        #    0  1  2
        # 0 u1 __ __
        # 1 __ u2 __
        # 2 __ __ __

        unit_actions_this_turn = {
            'u_1': (c.ValidActions.MOVE, gm.Position(2, 2)),
            'u_2': (c.ValidActions.MOVE, gm.Position(0, 1))
        }

        for unit in c.LogicGlobals.player.units:
            unit.set_task(*unit_actions_this_turn[unit.id])

        actions, debug = agent.unit_action_resolution(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        assert len(actions) == 2
        assert 'm u_2 w' in actions
        assert 'm u_1 e' in actions

    def test_collision_moving_through(self):
        c.LogicGlobals.game_state = g.Game(0, "3 3")
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 1 0 0 0 0 0',
                'u 0 0 u_2 0 1 0 0 0 0',
            ], 0
        )

        #    0  1  2
        # 0 __ u1 __
        # 1 u2 __ __
        # 2 __ __ __

        unit_actions_this_turn = {
            'u_1': (c.ValidActions.MOVE, gm.Position(1, 2)),
            'u_2': (c.ValidActions.MOVE, gm.Position(2, 1))
        }

        for unit in c.LogicGlobals.player.units:
            unit.set_task(*unit_actions_this_turn[unit.id])

        actions, debug = agent.unit_action_resolution(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        assert len(actions) == 1
        assert ('m u_2 e' in actions) or ('m u_1 s' in actions)

    def test_collision_mix_of_through_and_target(self):
        c.LogicGlobals.game_state = g.Game(0, "3 3")
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 1 0 0 0 0 0',
                'u 0 0 u_2 0 1 0 0 0 0',
            ], 0
        )

        #    0  1  2
        # 0 __ u1 __
        # 1 u2 __ __
        # 2 __ __ __

        unit_actions_this_turn = {
            'u_1': (c.ValidActions.MOVE, gm.Position(1, 1)),
            'u_2': (c.ValidActions.MOVE, gm.Position(2, 1))
        }

        for unit in c.LogicGlobals.player.units:
            unit.set_task(*unit_actions_this_turn[unit.id])

        actions, debug = agent.unit_action_resolution(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        assert len(actions) == 1
        assert 'm u_2 e' in actions
        for unit in c.LogicGlobals.player.units:
            if unit.id == 'u_1':
                assert unit.turns_spent_waiting_to_move == 1
            if unit.id == 'u_2':
                assert unit.turns_spent_waiting_to_move == 0

    def test_collision_mix_of_through_and_target_with_city(self):
        c.LogicGlobals.game_state = g.Game(0, "3 3")
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 1 0 0 0 0 0',
                'u 0 0 u_2 0 1 0 0 0 0',
                'c 0 c_1 0 23',
                'ct 0 c_1 1 1 0'
            ], 0
        )

        #    0  1  2
        # 0 __ u1 __
        # 1 u2 c1 __
        # 2 __ __ __

        unit_actions_this_turn = {
            'u_1': (c.ValidActions.MOVE, gm.Position(1, 2)),
            'u_2': (c.ValidActions.MOVE, gm.Position(2, 1))
        }

        for unit in c.LogicGlobals.player.units:
            unit.set_task(*unit_actions_this_turn[unit.id])

        actions, debug = agent.unit_action_resolution(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        assert len(actions) == 2
        assert 'm u_2 e' in actions
        assert 'm u_1 s' in actions

    def test_collision_mix_of_through_and_target_multi(self):
        c.LogicGlobals.game_state = g.Game(0, "5 5")
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 2 0 0 0 0 0',
                'u 0 0 u_2 1 1 0 0 0 0',
                'u 0 0 u_3 0 1 0 0 0 0',
            ], 0
        )

        #    0  1  2  3  4
        # 0 __ __ u1 __ __
        # 1 u3 u2 __ __ __
        # 2 __ __ __ __ __
        # 4 __ __ __ __ __
        # 5 __ __ __ __ __

        unit_actions_this_turn = {
            'u_1': (c.ValidActions.MOVE, gm.Position(2, 1)),
            'u_2': (c.ValidActions.MOVE, gm.Position(4, 1)),
            'u_3': (c.ValidActions.MOVE, gm.Position(3, 1))
        }

        for unit in c.LogicGlobals.player.units:
            unit.set_task(*unit_actions_this_turn[unit.id])

        actions, debug = agent.unit_action_resolution(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        assert len(actions) == 2
        assert 'm u_2 e' in actions
        assert 'm u_3 e' in actions
        for unit in c.LogicGlobals.player.units:
            if unit.id == 'u_1':
                assert unit.turns_spent_waiting_to_move == 1
            if unit.id in {'u_2', 'u_3'}:
                assert unit.turns_spent_waiting_to_move == 0

        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 2 0 0 0 0 0',
                'u 0 0 u_2 2 1 0 0 0 0',
                'u 0 0 u_3 1 1 0 0 0 0',
            ], 0
        )

        #    0  1  2  3  4
        # 0 __ __ u1 __ __
        # 1 __ u3 u2 __ __
        # 2 __ __ __ __ __
        # 4 __ __ __ __ __
        # 5 __ __ __ __ __

        unit_actions_this_turn = {
            'u_1': (c.ValidActions.MOVE, gm.Position(2, 1)),
            'u_2': (c.ValidActions.MOVE, gm.Position(4, 1)),
            'u_3': (c.ValidActions.MOVE, gm.Position(3, 1))
        }

        for unit in c.LogicGlobals.player.units:
            unit.set_task(*unit_actions_this_turn[unit.id])

        actions, debug = agent.unit_action_resolution(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        assert len(actions) == 2
        assert 'm u_2 e' in actions
        assert 'm u_3 e' in actions
        for unit in c.LogicGlobals.player.units:
            if unit.id == 'u_1':
                assert unit.turns_spent_waiting_to_move == 2
            if unit.id in {'u_2', 'u_3'}:
                assert unit.turns_spent_waiting_to_move == 0

        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 2 0 0 0 0 0',
                'u 0 0 u_2 3 1 0 0 0 0',
                'u 0 0 u_3 2 1 0 0 0 0',
            ], 0
        )

        #    0  1  2  3  4
        # 0 __ __ u1 __ __
        # 1 __ __ u3 u2 __
        # 2 __ __ __ __ __
        # 4 __ __ __ __ __
        # 5 __ __ __ __ __

        unit_actions_this_turn = {
            'u_1': (c.ValidActions.MOVE, gm.Position(2, 1)),
            'u_2': (c.ValidActions.MOVE, gm.Position(4, 1)),
            'u_3': (c.ValidActions.MOVE, gm.Position(3, 1))
        }

        for unit in c.LogicGlobals.player.units:
            unit.set_task(*unit_actions_this_turn[unit.id])

        actions, debug = agent.unit_action_resolution(
            c.LogicGlobals.player, c.LogicGlobals.opponent
        )

        assert len(actions) == 3
        assert 'm u_1 s' in actions
        assert 'm u_2 e' in actions
        assert 'm u_3 e' in actions
        for unit in c.LogicGlobals.player.units:
            assert unit.turns_spent_waiting_to_move == 0
