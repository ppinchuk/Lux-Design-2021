import pytest
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


class TestCity:
    @pytest.mark.parametrize("initialize_game", [11], indirect=['initialize_game'])
    def test_num_turns_can_survive(self, initialize_game):
        c.LogicGlobals.game_state.update(
            [
                'c 0 c_1 230 23',
                'ct 0 c_1 3 5 0',
            ], 0
        )

        #     0  1  2  3  4  5  6  7  8  9 10
        #  0 __ __ __ __ __ __ __ __ __ __ __
        #  1 __ __ __ __ __ __ __ __ __ __ __
        #  2 __ __ __ __ __ __ __ __ __ __ __
        #  3 __ __ __ __ __ __ __ __ __ __ __
        #  4 __ __ __ __ __ __ __ __ __ __ __
        #  5 __ __ __ c1 __ __ __ __ __ __ __
        #  6 __ __ __ __ __ __ __ __ __ __ __
        #  7 __ __ __ __ __ __ __ __ __ __ __
        #  8 __ __ __ __ __ __ __ __ __ __ __
        #  9 __ __ __ __ __ __ __ __ __ __ __
        # 10 __ __ __ __ __ __ __ __ __ __ __

        for c_id, city in c.LogicGlobals.player.cities.items():
            assert city.num_turns_can_survive == 40

        c.LogicGlobals.game_state.update(
            [
                'c 0 c_1 230 23',
                'ct 0 c_1 3 5 0',
            ], 0
        )

        #     0  1  2  3  4  5  6  7  8  9 10
        #  0 __ __ __ __ __ __ __ __ __ __ __
        #  1 __ __ __ __ __ __ __ __ __ __ __
        #  2 __ __ __ __ __ __ __ __ __ __ __
        #  3 __ __ __ __ __ __ __ __ __ __ __
        #  4 __ __ __ __ __ __ __ __ __ __ __
        #  5 __ __ __ c1 __ __ __ __ __ __ __
        #  6 __ __ __ __ __ __ __ __ __ __ __
        #  7 __ __ __ __ __ __ __ __ __ __ __
        #  8 __ __ __ __ __ __ __ __ __ __ __
        #  9 __ __ __ __ __ __ __ __ __ __ __
        # 10 __ __ __ __ __ __ __ __ __ __ __

        for c_id, city in c.LogicGlobals.player.cities.items():
            assert city.num_turns_can_survive == 39

        for __ in range(29):
            c.LogicGlobals.game_state.update(
                [
                    'c 0 c_1 230 23',
                    'ct 0 c_1 3 5 0',
                ], 0
            )

        assert c.LogicGlobals.game_state.turn == 30
        for c_id, city in c.LogicGlobals.player.cities.items():
            assert city.num_turns_can_survive == 10

        for __ in range(10):
            c.LogicGlobals.game_state.update(
                [
                    'c 0 c_1 2070 23',
                    'ct 0 c_1 3 5 0',
                ], 0
            )

        for c_id, city in c.LogicGlobals.player.cities.items():
            assert city.num_turns_can_survive >= 360
