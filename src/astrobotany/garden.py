import itertools
import random
from datetime import datetime, timedelta
from typing import List, Tuple

from astrobotany.art import ArtFile, CharacterMatrix, Tile, colorize
from astrobotany.models import Config, Plant, User
from astrobotany.pond import Pond

Coordinate = Tuple[int, int]
Coordinates = List[Coordinate]


POND_TEMPLATE = """\
 ~~~~    ~~~~~~
~~~~~~~~~~~~~~~~~
 ~~~~~~~~~~~~~~~~
  ~~~~~~~~~~~~~~
    ~~~~~~~~~~
       ~~~~~~
"""


def initialize_canvas(height: int, width: int) -> Tuple[CharacterMatrix, Coordinates]:
    matrix: CharacterMatrix = []
    empty: Coordinates = []
    for y in range(height):
        matrix.append([])
        for x in range(width):
            matrix[-1].append(Tile(" ", None, None))
            empty.append((y, x))

    empty.reverse()
    return matrix, empty


def get_plant_tile(plant: Plant) -> Tile:
    watered_delta = datetime.now() - plant.watered_at
    if plant.dead:
        return Tile(" ", None, None)

    char = [".", ",", "o", "O", "@", "&"][plant.stage]
    if watered_delta > timedelta(days=2):
        fg = 223  # grey (dry)
    elif plant.stage == 0:
        fg = 205  # yellow (seed)
    elif plant.stage == 4:
        fg = ArtFile.get_flower_color_code(plant.color_str)
    elif plant.stage == 5:
        fg = ArtFile.get_flower_color_code(plant.color_str)
    else:
        fg = 26  # green (sapling)

    return Tile(char, None, fg)


def paint_plants(matrix: CharacterMatrix, empty: Coordinates, update_users: bool) -> None:
    for user in User.select():
        symbol = get_plant_tile(user.plant)
        y, x = empty.pop()
        matrix[y][x] = symbol
        if update_users:
            new_coordinates = f"{y} South, {x} East"
            if new_coordinates != user.garden_coordinates:
                user.garden_coordinates = new_coordinates
                user.save()


def paint_pond(
    matrix: CharacterMatrix, empty: Coordinates, y_offset: int, x_offset: int
) -> Coordinates:
    lines = POND_TEMPLATE.splitlines(keepends=False)
    pond = []
    for y, line in enumerate(lines, start=y_offset):
        for x, char in enumerate(line, start=x_offset):
            if char != " ":
                matrix[y][x] = Tile(char, None, 30)
                pond.append((y, x))
                empty.remove((y, x))
    return pond


def paint_koi(matrix: CharacterMatrix, pond: Coordinates) -> None:
    """
    Add a koi fish to a pond with a random location and orientation.

    ~~~~~     ~~~~~
    ~<><~  or ~><>~
    ~~~~~     ~~~~~
    """
    for y, x in random.sample(pond, len(pond)):
        height = range(-1, 2)
        width = range(-1, 4)
        for y_offset, x_offset in itertools.product(height, width):
            # The fish must be surrounded by "~" on all sides
            if (y + y_offset, x + x_offset) not in pond:
                break
        else:
            # Use today's "blessed" color for the koi fish
            fg, _ = ArtFile.FLOWER_COLORS[Pond.get_blessed_color()]
            fish = random.choice(["<><", "><>"])
            matrix[y][x] = Tile(fish[0], None, fg)
            matrix[y][x + 1] = Tile(fish[1], None, fg)
            matrix[y][x + 2] = Tile(fish[2], None, fg)
            break


def render(matrix: CharacterMatrix, ansi_enabled: bool = True) -> str:
    lines = []
    for row in ArtFile.merge_tiles(matrix):
        if ansi_enabled:
            line = [colorize(tile.char, tile.fg, tile.bg) for tile in row]
        else:
            line = [tile.char for tile in row]

        lines.append("".join(line))
    return "\n".join(lines)


def build_matrix(update_users: bool) -> CharacterMatrix:
    count = User.select().count() + len(POND_TEMPLATE)
    width = 60
    height = max(12, count // width + 1)

    matrix, empty = initialize_canvas(height, width)
    pond = paint_pond(matrix, empty, 3, 6)
    paint_koi(matrix, pond)
    paint_plants(matrix, empty, update_users)
    return matrix


def rebuild_garden(update_users: bool = True) -> dict:
    matrix = build_matrix(update_users)
    data = {"ansi": render(matrix, ansi_enabled=True), "plain": render(matrix, ansi_enabled=False)}
    Config.write(Config.GARDEN_ART, data)
    return data


def load_garden(ansi_enabled: bool = True, update_users: bool = True):
    data = Config.load(Config.GARDEN_ART)
    if data is None:
        data = rebuild_garden(update_users)

    return data["ansi"] if ansi_enabled else data["plain"]
