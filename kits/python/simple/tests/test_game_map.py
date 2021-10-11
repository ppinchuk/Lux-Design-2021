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


class TestResourceCluster:

    @pytest.mark.parametrize("initialize_game", [11], indirect=['initialize_game'])
    def test_positions_to_defend_if_different_starting_clusters(self, initialize_game):
        c.LogicGlobals.game_state.update(
            [
                'r coal 4 5 419',
                'r coal 6 5 419',
                'u 0 0 u_1 3 5 0 0 0 0',
                'u 0 1 u_2 7 5 0 0 0 0',
                'c 0 c_1 0 23',
                'c 1 c_2 0 23',
                'ct 0 c_1 3 5 0',
                'ct 1 c_2 7 5 0',
            ], 0
        )

        #     0  1  2  3  4  5  6  7  8  9 10
        #  0 __ __ __ __ __ __ __ __ __ __ __
        #  1 __ __ __ __ __ __ __ __ __ __ __
        #  2 __ __ __ __ __ __ __ __ __ __ __
        #  3 __ __ __ __ __ __ __ __ __ __ __
        #  4 __ __ __ __ __ __ __ __ __ __ __
        #  5 __ __ __ u1 co __ co u2 __ __ __
        #  6 __ __ __ __ __ __ __ __ __ __ __
        #  7 __ __ __ __ __ __ __ __ __ __ __
        #  8 __ __ __ __ __ __ __ __ __ __ __
        #  9 __ __ __ __ __ __ __ __ __ __ __
        # 10 __ __ __ __ __ __ __ __ __ __ __

        assert len(c.LogicGlobals.game_state.map.resource_clusters) == 2

        for cluster in c.LogicGlobals.game_state.map.resource_clusters:
            if gm.Position(4, 5) in cluster.resource_positions:
                assert cluster.pos_to_defend[0] == gm.Position(5, 5), cluster.pos_to_defend[0]
                assert gm.Position(5, 6) in cluster.pos_to_defend[1:3], cluster.pos_to_defend[1:3]
                assert gm.Position(5, 4) in cluster.pos_to_defend[1:3], cluster.pos_to_defend[1:3]
                assert gm.Position(4, 6) in cluster.pos_to_defend[3:5], cluster.pos_to_defend[3:5]
                assert gm.Position(4, 4) in cluster.pos_to_defend[3:5], cluster.pos_to_defend[3:5]
                assert gm.Position(3, 6) in cluster.pos_to_defend[5:], cluster.pos_to_defend[5:]
                assert gm.Position(3, 4) in cluster.pos_to_defend[5:], cluster.pos_to_defend[5:]
                assert gm.Position(3, 5) in cluster.pos_to_defend[5:], cluster.pos_to_defend[5:]

    @pytest.mark.parametrize("initialize_game", [11], indirect=['initialize_game'])
    def test_positions_to_defend_if_same_starting_cluster(self, initialize_game):
        c.LogicGlobals.game_state.update(
            [
                'r coal 4 5 419',
                'r coal 5 5 419',
                'r coal 6 5 419',
                'u 0 0 u_1 3 5 0 0 0 0',
                'u 0 1 u_2 7 5 0 0 0 0',
                'c 0 c_1 0 23',
                'c 1 c_2 0 23',
                'ct 0 c_1 3 5 0',
                'ct 1 c_2 7 5 0',
            ], 0
        )

        #     0  1  2  3  4  5  6  7  8  9 10
        #  0 __ __ __ __ __ __ __ __ __ __ __
        #  1 __ __ __ __ __ __ __ __ __ __ __
        #  2 __ __ __ __ __ __ __ __ __ __ __
        #  3 __ __ __ __ __ __ __ __ __ __ __
        #  4 __ __ __ __ __ __ __ __ __ __ __
        #  5 __ __ __ u1 co co co u2 __ __ __
        #  6 __ __ __ __ __ __ __ __ __ __ __
        #  7 __ __ __ __ __ __ __ __ __ __ __
        #  8 __ __ __ __ __ __ __ __ __ __ __
        #  9 __ __ __ __ __ __ __ __ __ __ __
        # 10 __ __ __ __ __ __ __ __ __ __ __

        for cluster in c.LogicGlobals.game_state.map.resource_clusters:
            assert cluster.pos_to_defend[0] == gm.Position(3, 5)
            assert gm.Position(3, 4) in cluster.pos_to_defend[1:3]
            assert gm.Position(3, 6) in cluster.pos_to_defend[1:3]
            assert gm.Position(4, 4) in cluster.pos_to_defend[3:5]
            assert gm.Position(4, 6) in cluster.pos_to_defend[3:5]
            assert gm.Position(5, 4) in cluster.pos_to_defend[5:7]
            assert gm.Position(5, 6) in cluster.pos_to_defend[5:7]
            assert gm.Position(6, 4) in cluster.pos_to_defend[7:9]
            assert gm.Position(6, 6) in cluster.pos_to_defend[7:9]
            assert gm.Position(7, 4) in cluster.pos_to_defend[9:]
            assert gm.Position(7, 5) in cluster.pos_to_defend[9:]
            assert gm.Position(7, 6) in cluster.pos_to_defend[9:]

    @pytest.mark.parametrize("initialize_game", [7], indirect=['initialize_game'])
    def test_positions_to_defend_by_edge(self, initialize_game):
        c.LogicGlobals.game_state.update(
            [
                'r uranium 0 0 419',
            ], 0
        )

        #    0  1  2  3  4  5  6
        # 0 ur __ __ __ __ __ __
        # 1 __ __ __ __ __ __ __
        # 2 __ __ __ __ __ __ __
        # 3 __ __ __ __ __ __ __
        # 4 __ __ __ __ __ __ __
        # 5 __ __ __ __ __ __ __
        # 6 __ __ __ __ __ __ __

        for cluster in c.LogicGlobals.game_state.map.resource_clusters:
            assert cluster.pos_to_defend[0] == gm.Position(1, 1)
            assert gm.Position(1, 0) in cluster.pos_to_defend[1:]
            assert gm.Position(0, 1) in cluster.pos_to_defend[1:]

    @pytest.mark.parametrize("initialize_game", [7], indirect=['initialize_game'])
    def test_positions_to_defend_by_edge2(self, initialize_game):
        c.LogicGlobals.game_state.update(
            [
                'r coal 1 1 419',
            ], 0
        )

        #    0  1  2  3  4  5  6
        # 0 __ __ __ __ __ __ __
        # 1 __ co __ __ __ __ __
        # 2 __ __ __ __ __ __ __
        # 3 __ __ __ __ __ __ __
        # 4 __ __ __ __ __ __ __
        # 5 __ __ __ __ __ __ __
        # 6 __ __ __ __ __ __ __

        for cluster in c.LogicGlobals.game_state.map.resource_clusters:
            assert cluster.pos_to_defend[0] == gm.Position(2, 2)
            assert gm.Position(2, 1) in cluster.pos_to_defend[1:3]
            assert gm.Position(1, 2) in cluster.pos_to_defend[1:3]
            assert gm.Position(0, 2) in cluster.pos_to_defend[3:]
            assert gm.Position(2, 0) in cluster.pos_to_defend[3:]

    @pytest.mark.parametrize("initialize_game", [7], indirect=['initialize_game'])
    def test_positions_to_defend_by_edge_3(self, initialize_game):
        c.LogicGlobals.game_state.update(
            [
                'r coal 2 2 419',
            ], 0
        )

        #    0  1  2  3  4  5  6
        # 0 __ __ __ __ __ __ __
        # 1 __ __ __ __ __ __ __
        # 2 __ __ co __ __ __ __
        # 3 __ __ __ __ __ __ __
        # 4 __ __ __ __ __ __ __
        # 5 __ __ __ __ __ __ __
        # 6 __ __ __ __ __ __ __

        for cluster in c.LogicGlobals.game_state.map.resource_clusters:
            assert cluster.pos_to_defend[0] == gm.Position(3, 3)
            assert gm.Position(2, 3) in cluster.pos_to_defend[1:3]
            assert gm.Position(3, 2) in cluster.pos_to_defend[1:3]
            assert gm.Position(1, 3) in cluster.pos_to_defend[3:5]
            assert gm.Position(3, 1) in cluster.pos_to_defend[3:5]
            assert gm.Position(0, 3) in cluster.pos_to_defend[5:]
            assert gm.Position(3, 0) in cluster.pos_to_defend[5:]


class TestGameMap:
    @pytest.mark.parametrize("initialize_game", [3], indirect=['initialize_game'])
    def test_bounds(self, initialize_game):
        c.LogicGlobals.game_state.update([], 0)

        assert c.LogicGlobals.game_state.map.is_within_bounds(
            gm.Position(0, 0)
        )
        assert c.LogicGlobals.game_state.map.is_within_bounds(
            gm.Position(1, 1)
        )
        assert not c.LogicGlobals.game_state.map.is_within_bounds(
            gm.Position(1, 3)
        )
        assert not c.LogicGlobals.game_state.map.is_within_bounds(
            gm.Position(-1, 0)
        )
        assert c.LogicGlobals.game_state.map.is_loc_within_bounds(0, 0)
        assert c.LogicGlobals.game_state.map.is_loc_within_bounds(1, 1)
        assert not c.LogicGlobals.game_state.map.is_loc_within_bounds(1, 3)
        assert not c.LogicGlobals.game_state.map.is_loc_within_bounds(-1, 0)

    @pytest.mark.parametrize("initialize_game", [32], indirect=['initialize_game'])
    def test_get_cell(self, initialize_game):
        c.LogicGlobals.game_state.update(
            [
                'r coal 0 3 419',
                'u 0 0 u_1 13 7 0 0 0 0',
                'u 0 1 u_2 13 16 0 0 0 0',
                'c 0 c_1 0 23',
                'c 1 c_2 0 23',
                'ct 0 c_1 13 7 0',
                'ct 1 c_2 13 16 0'
            ], 0
        )

        assert c.LogicGlobals.game_state.map.get_cell_by_pos(
            gm.Position(0, 3)
        ).resource is not None
        assert c.LogicGlobals.game_state.map.get_cell_by_pos(
            gm.Position(-1, -1)
        ) is None

        assert c.LogicGlobals.game_state.map.get_cell(0, 3).resource is not None
        assert c.LogicGlobals.game_state.map.get_cell(0, -1) is None


class TestPosition:
    def test_xy(self):
        pos = gm.Position(0, 0)
        assert pos.x == 0
        assert pos.y == 0

    def test_subtract(self):
        pos = gm.Position(10, 10)
        assert pos - gm.Position(5, -2) == 17

    def test_distance_to(self):
        pos = gm.Position(10, 10)
        assert pos.distance_to(gm.Position(5, -2)) == 17
        assert pos.distance_to(pos) == 0

    def test_is_adjacent(self):
        pos = gm.Position(10, 10)
        assert pos.is_adjacent(pos)
        assert pos.is_adjacent(gm.Position(10, 11))
        assert pos.is_adjacent(gm.Position(10, 9))
        assert pos.is_adjacent(gm.Position(9, 10))
        assert pos.is_adjacent(gm.Position(11, 10))
        assert not pos.is_adjacent(gm.Position(11, 11))

    def test_is_equal(self):
        pos = gm.Position(10, 10)
        assert pos == gm.Position(10, 10)

    def test_adjacent_pos(self):
        pos = gm.Position(10, 10)
        assert gm.Position(10, 9) in pos.adjacent_positions(include_center=True)
        assert gm.Position(10, 11) in pos.adjacent_positions(include_center=True)
        assert gm.Position(11, 10) in pos.adjacent_positions(include_center=True)
        assert gm.Position(9, 10) in pos.adjacent_positions(include_center=True)
        assert gm.Position(10, 10) in pos.adjacent_positions(include_center=True)
        assert gm.Position(10, 10) not in pos.adjacent_positions(include_center=False)

    def test_translate(self):
        pos = gm.Position(10, 10)
        assert pos.translate(c.Directions.NORTH, 1) == gm.Position(10, 9)
        assert pos.translate(c.Directions.SOUTH, 1) == gm.Position(10, 11)
        assert pos.translate(c.Directions.EAST, 1) == gm.Position(11, 10)
        assert pos.translate(c.Directions.WEST, 1) == gm.Position(9, 10)
        assert pos.translate(c.Directions.CENTER, 10) == gm.Position(10, 10)
        assert pos.translate(c.Directions.NORTH, -1) == gm.Position(10, 11)

    @pytest.mark.parametrize("initialize_game", [3], indirect=['initialize_game'])
    def test_find_closest_resource_on_empty_map(self, initialize_game):
        c.LogicGlobals.game_state.update([], 0)
        closest_resource_pos = gm.Position(0, 0).find_closest_resource(
            c.LogicGlobals.player, c.LogicGlobals.game_state.map
        )
        assert closest_resource_pos is None

    @pytest.mark.parametrize("initialize_game", [3], indirect=['initialize_game'])
    def test_find_closest_resource_with_not_enough_rp(self, initialize_game):
        c.LogicGlobals.game_state.update([
            'r uranium 2 2 331'
        ], 0)
        closest_resource_pos = gm.Position(0, 0).find_closest_resource(
            c.LogicGlobals.player, c.LogicGlobals.game_state.map
        )
        assert closest_resource_pos is None

    @pytest.mark.parametrize("initialize_game", [3], indirect=['initialize_game'])
    def test_find_closest_resource_on_non_empty_map(self, initialize_game):
        c.LogicGlobals.game_state.update([
            'r wood 2 2 331',
        ], 0)

        closest_resource_pos = gm.Position(0, 0).find_closest_resource(
            c.LogicGlobals.player, c.LogicGlobals.game_state.map
        )
        assert closest_resource_pos == gm.Position(2, 2)

    @pytest.mark.parametrize("initialize_game", [3], indirect=['initialize_game'])
    def test_find_closest_resource_without_tie_breaker(self, initialize_game):
        c.LogicGlobals.game_state.update([
            'r wood 2 1 331',
            'r wood 1 2 331'
        ], 0)

        #    0  1  2
        # 0 __ __ __
        # 1 __ __ wo
        # 2 __ wo __

        closest_resource_pos = gm.Position(0, 0).find_closest_resource(
            c.LogicGlobals.player, c.LogicGlobals.game_state.map
        )
        assert closest_resource_pos == gm.Position(1, 2) or closest_resource_pos == gm.Position(2, 1)

    @pytest.mark.parametrize("initialize_game", [7], indirect=['initialize_game'])
    def test_find_closest_resource_with_tie_breaker(self, initialize_game):
        c.LogicGlobals.game_state.update([
            'r wood 2 1 331',
            'r wood 3 2 331',
        ], 0)

        #    0  1  2  3  4  5  6
        # 0 __ __ __ __ __ __ __
        # 1 __ __ wo __ __ __ __
        # 2 __ __ __ wo __ __ __
        # 3 __ __ p1 p2 __ __ __
        # 4 __ __ __ __ __ __ __
        # 5 __ __ __ __ __ __ __
        # 6 __ __ __ __ __ __ __

        closest_resource_pos = gm.Position(2, 3).find_closest_resource(
            c.LogicGlobals.player, c.LogicGlobals.game_state.map,
            tie_breaker_func=gm.Position(3, 3).distance_to
        )
        assert closest_resource_pos == gm.Position(3, 2)

    @pytest.mark.parametrize("initialize_game", [3], indirect=['initialize_game'])
    def test_find_closest_city_tile(self, initialize_game):
        c.LogicGlobals.game_state.update([
            'c 0 c_1 0 23',
            'ct 0 c_1 1 1 0',
        ], 0)
        closest_city_pos = gm.Position(0, 0).find_closest_city_tile(
            c.LogicGlobals.player,
            c.LogicGlobals.game_state.map
        )
        assert closest_city_pos == gm.Position(1, 1)

        c.LogicGlobals.game_state.update([], 0)
        closest_city_pos = gm.Position(0, 0).find_closest_city_tile(
            c.LogicGlobals.player,
            c.LogicGlobals.game_state.map
        )
        assert closest_city_pos is None

    @pytest.mark.parametrize("initialize_game", [3], indirect=['initialize_game'])
    def test_pathing_distance_to(self, initialize_game):
        c.LogicGlobals.game_state.update([], 0)
        pos = gm.Position(0, 0)

        assert pos.pathing_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            avoid_own_cities=True
        ) == 4

        assert pos.pathing_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            avoid_own_cities=False
        ) == 4

        c.LogicGlobals.game_state.update(
            [
                'c 0 c_1 0 23',
                'ct 0 c_1 1 1 0',
            ], 0
        )

        assert pos.pathing_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            avoid_own_cities=False
        ) == 4
        assert pos.pathing_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            avoid_own_cities=True
        ) == 4

        c.LogicGlobals.game_state.update(
            [
                'c 0 c_1 0 23',
                'ct 0 c_1 1 1 0',
                'ct 0 c_1 0 1 0',
            ], 0
        )

        assert pos.pathing_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            avoid_own_cities=True
        ) == 4
        assert pos.pathing_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            avoid_own_cities=False
        ) == 4

        assert pos.pathing_distance_to(
            gm.Position(0, 2),
            c.LogicGlobals.game_state.map,
            avoid_own_cities=True
        ) == 6

        assert pos.pathing_distance_to(
            gm.Position(0, 2),
            c.LogicGlobals.game_state.map,
            avoid_own_cities=False
        ) == 2

        c.LogicGlobals.game_state.update(
            [
                'c 0 c_1 0 23',
                'ct 0 c_1 1 1 0',
                'ct 0 c_1 0 1 0',
                'ct 0 c_1 2 1 0',
            ], 0
        )

        assert pos.pathing_distance_to(
            gm.Position(0, 2),
            c.LogicGlobals.game_state.map,
            avoid_own_cities=True
        ) >= c.INFINITE_DISTANCE

        assert pos.pathing_distance_to(
            gm.Position(0, 2),
            c.LogicGlobals.game_state.map,
            avoid_own_cities=False
        ) == 2

        c.LogicGlobals.game_state.update(
            [
                'c 0 c_1 0 23',
                'ct 0 c_1 0 1 0',
                'ct 0 c_1 2 1 0',
            ], 0
        )

        assert pos.pathing_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            avoid_own_cities=True
        ) == 4

        assert pos.pathing_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            avoid_own_cities=False
        ) == 4

    @pytest.mark.parametrize("initialize_game", [3], indirect=['initialize_game'])
    def test_turn_distance_to(self, initialize_game):
        c.LogicGlobals.game_state.update([], 0)
        pos = gm.Position(0, 0)

        assert pos.turn_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True
        ) == 7

        c.LogicGlobals.game_state.update([
            'ccd 0 1 1',
        ], 0)

        assert pos.turn_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True
        ) == 6

        c.LogicGlobals.game_state.update([
            'ccd 0 1 0.5',
        ], 0)

        assert pos.turn_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True
        ) == 6.5

        c.LogicGlobals.game_state.update([
            'ccd 0 1 6',
            'ccd 1 1 6',
            'ccd 2 1 6',
        ], 0)

        assert pos.turn_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True
        ) == 4

        assert gm.Position(2, 2).turn_distance_to(
            gm.Position(1, 0),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True,
            include_target_road=True
        ) == 4

        assert gm.Position(2, 2).turn_distance_to(
            gm.Position(0, 1),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True,
            include_target_road=True
        ) == 3

        c.LogicGlobals.game_state.update(
            [
                'c 0 c_1 0 23',
                'ct 0 c_1 1 1 0',
                'ct 0 c_1 0 1 0',
                'ct 0 c_1 2 1 0',
                'ccd 0 1 6',
                'ccd 1 1 6',
                'ccd 2 1 6',
            ], 0
        )

        assert pos.turn_distance_to(
            gm.Position(0, 2),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True
        ) >= c.INFINITE_DISTANCE

        c.LogicGlobals.game_state = g.Game(0, "30 30")
        c.LogicGlobals.game_state.update([], 0)
        pos = gm.Position(0, 0)

        assert pos.turn_distance_to(
            gm.Position(0, 5),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True
        ) == 9

        assert pos.turn_distance_to(
            gm.Position(0, 6),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True
        ) == 11

        assert pos.turn_distance_to(
            gm.Position(0, 9),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True
        ) == 17

        assert pos.turn_distance_to(
            gm.Position(0, 10),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True
        ) == 19

        assert pos.turn_distance_to(
            gm.Position(0, 11),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True
        ) == 22

    @pytest.mark.parametrize("initialize_game", [3], indirect=['initialize_game'])
    def test_turn_distance_to_at_night(self, initialize_game):
        for __ in range(25):
            c.LogicGlobals.game_state.update([], 0)
        pos = gm.Position(0, 0)

        assert pos.turn_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True
        ) == 7

        for __ in range(5):
            c.LogicGlobals.game_state.update([], 0)
        pos = gm.Position(0, 0)

        assert c.LogicGlobals.game_state.turn == 29

        assert pos.turn_distance_to(
            gm.Position(0, 1),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True
        ) == 1

        assert pos.turn_distance_to(
            gm.Position(2, 2),
            c.LogicGlobals.game_state.map,
            cooldown=2,
            avoid_own_cities=True
        ) == 13
