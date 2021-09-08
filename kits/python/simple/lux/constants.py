class Constants:

    class INPUT_CONSTANTS:
        RESEARCH_POINTS = "rp"
        RESOURCES = "r"
        UNITS = "u"
        CITY = "c"
        CITY_TILES = "ct"
        ROADS = "ccd"
        DONE = "D_DONE"

    class DIRECTIONS:
        NORTH = "n"
        WEST = "w"
        SOUTH = "s"
        EAST = "e"
        CENTER = "c"

    class UNIT_TYPES:
        WORKER = 0
        CART = 1

    class RESOURCE_TYPES:
        WOOD = "wood"
        URANIUM = "uranium"
        COAL = "coal"


class ValidActions:
    MOVE = "move"
    TRANSFER = "transfer"
    PILLAGE = "pillage"
    BUILD = "build"

    @classmethod
    def for_unit(cls, u_type):
        if u_type == Constants.UNIT_TYPES.WORKER:
            return {cls.MOVE, cls.TRANSFER, cls.PILLAGE, cls.BUILD}
        elif u_type == Constants.UNIT_TYPES.CART:
            return {cls.MOVE, cls.TRANSFER}
        else:
            return set()


ALL_DIRECTIONS = [
    Constants.DIRECTIONS.NORTH, Constants.DIRECTIONS.EAST,
    Constants.DIRECTIONS.SOUTH, Constants.DIRECTIONS.WEST
]

ALL_DIRECTIONS_AND_CENTER = [
    Constants.DIRECTIONS.NORTH, Constants.DIRECTIONS.EAST,
    Constants.DIRECTIONS.SOUTH, Constants.DIRECTIONS.WEST,
    Constants.DIRECTIONS.CENTER
]
