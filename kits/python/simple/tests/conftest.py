import pytest
import lux.game_map as gm
import lux.constants as c
import lux.game as g


@pytest.fixture
def initialize_game(request):
    c.LogicGlobals.game_state = g.Game(0, f"{request.param} {request.param}")
    yield
    gm.MAP_CACHE.clear()
