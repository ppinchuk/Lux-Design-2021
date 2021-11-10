import sys
from path import Path
if Path(__file__).parent.parent.absolute().as_posix() not in sys.path:
    sys.path.append(Path(__file__).parent.parent.absolute().as_posix())
import pytest
import lux.game_map as gm
import lux.game_objects as go
import lux.constants as c
import lux.game as g


def _reset_state():
    gm.MAP_CACHE.clear()
    go.UNIT_CACHE.clear()
    c.LogicGlobals.reset()


@pytest.fixture
def initialize_game(request):
    _reset_state()
    c.LogicGlobals.game_state = g.Game(0, f"{request.param} {request.param}")
    yield
    _reset_state()


@pytest.fixture
def reset_agent_state():
    return _reset_state
