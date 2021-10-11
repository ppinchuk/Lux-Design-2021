import pytest
import lux.game_objects as go
import lux.game as g
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


class TestGame:
    @pytest.mark.parametrize("initialize_game", [32], indirect=['initialize_game'])
    def test_correct_turn_number(self, initialize_game):
        c.LogicGlobals.game_state.update([], 0)
        assert c.LogicGlobals.game_state.turn == 0
        assert c.LogicGlobals.game_state.turns_until_next_night == 30
        c.LogicGlobals.game_state.update([], 0)
        assert c.LogicGlobals.game_state.turn == 1
        assert c.LogicGlobals.game_state.turns_until_next_night == 29

    @pytest.mark.parametrize("initialize_game", [32], indirect=['initialize_game'])
    def test_correct_turns_until_next_day(self, initialize_game):
        c.LogicGlobals.game_state.update([], 0)
        assert c.LogicGlobals.game_state.turns_until_next_day == 40
        for turn in range(1, 40):
            c.LogicGlobals.game_state.update([], 0)
            assert c.LogicGlobals.game_state.turns_until_next_day == 40 - turn

    @pytest.mark.parametrize("initialize_game", [32], indirect=['initialize_game'])
    def test_correct_turns_until_next_night(self, initialize_game):
        c.LogicGlobals.game_state.update([], 0)
        assert c.LogicGlobals.game_state.turns_until_next_night == 30
        for turn in range(1, 30):
            c.LogicGlobals.game_state.update([], 0)
            assert c.LogicGlobals.game_state.turns_until_next_night == 30 - turn

        for __ in range(10):
            c.LogicGlobals.game_state.update([], 0)
            assert c.LogicGlobals.game_state.turns_until_next_night == 0

        c.LogicGlobals.game_state.update([], 0)
        assert c.LogicGlobals.game_state.turns_until_next_night == 30

    @pytest.mark.parametrize("initialize_game", [32], indirect=['initialize_game'])
    def test_correct_turn_state(self, initialize_game):
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 1 0 0 0 0 0',
                'u 0 0 u_2 0 1 0 0 0 0',
                'c 0 c_1 0 23',
                'c 0 c_2 0 23',
                'c 0 c_4 0 23',
                'ct 0 c_1 13 7 0',
                'ct 0 c_2 15 7 0',
                'ct 0 c_4 15 5 0',
            ], 0
        )

        assert len(c.LogicGlobals.player.units) == 2
        assert 'u_1' in [u.id for u in c.LogicGlobals.player.units]
        assert 'u_2' in [u.id for u in c.LogicGlobals.player.units]

        assert len(c.LogicGlobals.player.cities) == 3
        assert 'c_1' in c.LogicGlobals.player.cities
        assert 'c_2' in c.LogicGlobals.player.cities
        assert 'c_4' in c.LogicGlobals.player.cities

        assert c.LogicGlobals.player.city_tile_count == 3

        assert len(c.LogicGlobals.player.city_pos) == 3
        assert gm.Position(13, 7) in c.LogicGlobals.player.city_pos
        assert gm.Position(15, 7) in c.LogicGlobals.player.city_pos
        assert gm.Position(15, 5) in c.LogicGlobals.player.city_pos

        assert len(c.LogicGlobals.player.city_ids) == 3
        assert 'c_1' in c.LogicGlobals.player.city_ids
        assert 'c_2' in c.LogicGlobals.player.city_ids
        assert 'c_4' in c.LogicGlobals.player.city_ids

        assert len(c.LogicGlobals.player.unit_ids) == 2
        assert 'u_1' in c.LogicGlobals.player.unit_ids
        assert 'u_2' in c.LogicGlobals.player.unit_ids

        assert len(c.LogicGlobals.player.unit_pos) == 2
        assert gm.Position(1, 0) in c.LogicGlobals.player.unit_pos
        assert gm.Position(0, 1) in c.LogicGlobals.player.unit_pos

    @pytest.mark.parametrize("initialize_game", [32], indirect=['initialize_game'])
    def test_correct_multi_turn_state(self, initialize_game):
        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 1 0 0 0 0 0',
                'u 0 0 u_2 0 1 0 0 0 0',
                'c 0 c_1 0 23',
                'c 0 c_2 0 23',
                'c 0 c_4 0 23',
                'ct 0 c_1 13 7 0',
                'ct 0 c_2 15 7 0',
                'ct 0 c_4 15 5 0',
            ], 0
        )

        curr_team = c.LogicGlobals.player.team
        curr_rp = c.LogicGlobals.player.research_points
        curr_strat = c.LogicGlobals.player.current_strategy

        c.LogicGlobals.game_state.update(
            [
                'u 0 0 u_1 1 0 0 0 0 0',
                'c 0 c_1 0 23',
                'ct 0 c_1 13 7 0',
            ], 0
        )

        assert len(c.LogicGlobals.player.units) == 1
        assert 'u_1' in [u.id for u in c.LogicGlobals.player.units]
        assert 'u_2' not in [u.id for u in c.LogicGlobals.player.units]

        assert len(c.LogicGlobals.player.cities) == 1
        assert 'c_1' in c.LogicGlobals.player.cities
        assert 'c_2' not in c.LogicGlobals.player.cities
        assert 'c_4' not in c.LogicGlobals.player.cities

        assert c.LogicGlobals.player.city_tile_count == 1

        assert len(c.LogicGlobals.player.city_pos) == 1
        assert gm.Position(13, 7) in c.LogicGlobals.player.city_pos
        assert gm.Position(15, 7) not in c.LogicGlobals.player.city_pos
        assert gm.Position(15, 5) not in c.LogicGlobals.player.city_pos

        assert len(c.LogicGlobals.player.city_ids) == 1
        assert 'c_1' in c.LogicGlobals.player.city_ids
        assert 'c_2' not in c.LogicGlobals.player.city_ids
        assert 'c_4' not in c.LogicGlobals.player.city_ids

        assert len(c.LogicGlobals.player.unit_ids) == 1
        assert 'u_1' in c.LogicGlobals.player.unit_ids
        assert 'u_2' not in c.LogicGlobals.player.unit_ids

        assert len(c.LogicGlobals.player.unit_pos) == 1
        assert gm.Position(1, 0) in c.LogicGlobals.player.unit_pos
        assert gm.Position(0, 1) not in c.LogicGlobals.player.unit_pos

        assert curr_team == c.LogicGlobals.player.team
        assert curr_rp == c.LogicGlobals.player.research_points
        assert curr_strat == c.LogicGlobals.player.current_strategy

