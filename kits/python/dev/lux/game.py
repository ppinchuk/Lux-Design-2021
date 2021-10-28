import getpass
from .constants import GAME_CONSTANTS, InputConstants, LogicGlobals
from .game_map import GameMap, Position
from .game_objects import Player, Unit, City, CityTile


class Game:
    def __init__(self, map_id, size_str):
        self.id = int(map_id)
        self.turn = -1
        self.turns_until_next_night = GAME_CONSTANTS["PARAMETERS"]["DAY_LENGTH"]
        self.turns_until_next_day = GAME_CONSTANTS["PARAMETERS"]["CYCLE_LENGTH"]
        # get some other necessary initial input
        mapInfo = size_str.split(" ")
        self.map_width = int(mapInfo[0])
        self.map_height = int(mapInfo[1])
        self.players = [Player(0), Player(1)]
        self.map = None
        self.player_rp = []
        self.opponent_rp = []

    def _end_turn(self):
        print("D_FINISH")

    def _reset_player_states(self):
        for p in self.players:
            p.reset_turn_state()

    def update(self, messages, player_id):
        """
        update state
        """
        self.map = GameMap(self.map_width, self.map_height)
        self.turn += 1
        self.turns_until_next_night = max(0,
            GAME_CONSTANTS["PARAMETERS"]["DAY_LENGTH"] - self.turn % GAME_CONSTANTS["PARAMETERS"]["CYCLE_LENGTH"]
        )
        self.turns_until_next_day = GAME_CONSTANTS["PARAMETERS"]["CYCLE_LENGTH"] - self.turn % GAME_CONSTANTS["PARAMETERS"]["CYCLE_LENGTH"]
        self._reset_player_states()

        if getpass.getuser() == 'Paul':
            messages = sorted(messages)

        for update in messages:
            if update == "D_DONE":
                continue
            strs = update.split(" ")
            input_identifier = strs[0]
            if input_identifier == InputConstants.RESEARCH_POINTS:
                team = int(strs[1])
                self.players[team].research_points = int(strs[2])
            elif input_identifier == InputConstants.RESOURCES:
                r_type = strs[1]
                x = int(strs[2])
                y = int(strs[3])
                amt = int(float(strs[4]))
                self.map._setResource(r_type, x, y, amt)
            elif input_identifier == InputConstants.UNITS:
                unittype = int(strs[1])
                team = int(strs[2])
                unitid = strs[3]
                x = int(strs[4])
                y = int(strs[5])
                cooldown = float(strs[6])
                wood = int(strs[7])
                coal = int(strs[8])
                uranium = int(strs[9])
                self.players[team].units.append(Unit(team, unittype, unitid, x, y, cooldown, wood, coal, uranium))
                self.players[team].unit_pos.add(Position(x, y))
                self.players[team].unit_ids.add(unitid)
            elif input_identifier == InputConstants.CITY:
                team = int(strs[1])
                cityid = strs[2]
                fuel = float(strs[3])
                lightupkeep = float(strs[4])
                self.players[team].cities[cityid] = City(team, cityid, fuel, lightupkeep)
                self.players[team].city_ids.add(cityid)
            elif input_identifier == InputConstants.CITY_TILES:
                team = int(strs[1])
                cityid = strs[2]
                x = int(strs[3])
                y = int(strs[4])
                cooldown = float(strs[5])
                city = self.players[team].cities[cityid]
                citytile = city._add_city_tile(x, y, cooldown)
                self.map.get_cell(x, y).citytile = citytile
                self.players[team].city_tile_count += 1
                self.players[team].city_pos.add(Position(x, y))
            elif input_identifier == InputConstants.ROADS:
                x = int(strs[1])
                y = int(strs[2])
                road = float(strs[3])
                self.map.get_cell(x, y).road = road

        LogicGlobals.player = LogicGlobals.game_state.players[player_id]
        LogicGlobals.opponent = LogicGlobals.game_state.players[(player_id + 1) % 2]
        self.player_rp.append(LogicGlobals.player.research_points)
        self.opponent_rp.append(LogicGlobals.opponent.research_points)
        if self.map.resource_clusters is None:
            self.map.find_clusters()
        self.map.update_clusters(LogicGlobals.opponent)
        if self.turn == 0 and LogicGlobals.player.city_pos:
            starter_pos = list(LogicGlobals.player.city_pos)[0]
            LogicGlobals.x_mult = 1 if starter_pos.x > self.map.width // 2 else -1
            LogicGlobals.y_mult = 1 if starter_pos.y > self.map.height // 2 else -1
            for cluster in self.map.resource_clusters:
                if len(cluster.pos_defended) >= 2:
                    cluster.sort_position = starter_pos
                elif len(cluster.pos_defended) == 1:
                    pos = cluster.pos_defended[0]
                    if pos in LogicGlobals.player.city_pos:
                        cluster.sort_position = starter_pos
                    else:
                        cluster.sort_position = pos.reflect_about(cluster.center_pos)

            self.map.update_clusters(LogicGlobals.opponent)
