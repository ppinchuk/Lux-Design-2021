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


def test_med_position():
    c.LogicGlobals.game_state = g.Game(0, "32 32")
    c.LogicGlobals.game_state.update(
        [
            'u 0 0 u_1 3 2 0 0 0 0',
            'u 0 0 u_2 26 2 0 0 0 0',
            'u 0 0 u_2 3 19 0 0 0 0',
        ], 0
    )

    med_pos = su.med_position([u.pos for u in c.LogicGlobals.player.units])
    assert med_pos == gm.Position(3, 2)
