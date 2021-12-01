import functools
import itertools
import json
import os
import random
from typing import Dict, List, NamedTuple, Optional, Tuple

ColorCode = Optional[int]


class Tile(NamedTuple):
    char: str
    bg: ColorCode
    fg: ColorCode


CharacterMatrix = List[List[Tile]]


def colorize(text: str, fg: ColorCode = None, bg: ColorCode = None) -> str:
    """
    Colorize a line of text using the ansi-240 color palette.
    """
    if fg is not None:
        text = f"\033[38;5;{fg+15}m" + text
    if bg is not None:
        text = f"\033[48;5;{bg+15}m" + text
    if fg is not None or bg is not None:
        text = text + "\033[0m"
    return text


class ArtFile:
    """
    This class encapsulates an ASCII art file in the playscii file format.

    See the README for more information on how the art files were created.
    """

    ART_DIR = os.path.join(os.path.dirname(__file__), "art")
    CHARSET = "dos"
    PALETTE = "ansi-240"

    # Common color codes used across all of the source playscii files
    DEFAULT_BG = 1
    DEFAULT_FG = 0
    DEFAULT_SOIL = 80
    DEFAULT_COLOR_PRIMARY = 133
    DEFAULT_COLOR_SECONDARY = 199

    # Default character to use for empty spaces
    FILL_CHAR = " "

    # Palette mapping for scene colors
    BACKGROUND_COLOR: ColorCode = None
    FOREGROUND_COLOR: ColorCode = None
    SOIL_COLOR: ColorCode = 80

    # Palette mapping for flower colors: (primary, secondary)
    FLOWER_COLORS: Dict[str, Tuple[int, int]] = {
        "red": (182, 189),
        "orange": (187, 199),
        "yellow": (211, 207),
        "green": (70, 104),
        "blue": (66, 18),
        "indigo": (48, 83),
        "violet": (150, 184),
        "white": (235, 239),
        "black": (224, 228),
        "gold": (163, 165),
    }

    # Special palette for rainbow colored flowers
    RAINBOW_COLORS = [5, 145, 211, 193, 30, 198, 31]

    # Making this a class-level variable has the effect of introducing some
    # randomness to the order of colors for rainbow plants
    rainbow_generator = itertools.cycle(RAINBOW_COLORS)

    def __init__(self, filename: str, flower_color: Optional[str] = None) -> None:
        self.filename = filename
        self.flower_color = flower_color
        self.character_matrix = self.load_file(filename)

    @classmethod
    def load_file(cls, filename: str) -> CharacterMatrix:
        """
        Load a playscii file and build a matrix of characters representing the scene.
        """
        with open(os.path.join(cls.ART_DIR, filename)) as fp:
            playscii_data = json.load(fp)

        if playscii_data["palette"] != cls.PALETTE:
            raise ValueError(f"Encountered unexpected palette {playscii_data['palette']}")
        if playscii_data["charset"] != cls.CHARSET:
            raise ValueError(f"Encountered unexpected charset {playscii_data['charset']}")

        tiles = iter(playscii_data["frames"][0]["layers"][0]["tiles"])
        data = []
        for _ in range(playscii_data["height"]):
            line = []
            for _ in range(playscii_data["width"]):
                tile = next(tiles)
                char = chr(tile["char"]) if tile["char"] != 0 else cls.FILL_CHAR
                bg = tile["bg"] if tile["bg"] != cls.DEFAULT_BG else None
                fg = tile["fg"] if tile["fg"] != cls.DEFAULT_FG else None
                if char == cls.FILL_CHAR:
                    # Ignore the foreground color if we don't have any foreground character
                    fg = None
                line.append(Tile(char, bg, fg))
            data.append(line)
        return data

    def render(self, ansi_enabled: bool = False) -> str:
        """
        Render the art file as a plain text string, optionally using ANSI color codes.
        """
        if ansi_enabled:
            return self._render_ansi()
        else:
            return self._render_ascii()

    def _render_ascii(self) -> str:
        """
        Drop all styling and render the art as plain ASCII characters.
        """
        return "\n".join("".join(tile.char for tile in line) for line in self.character_matrix)

    def _render_ansi(self) -> str:
        """
        Render the art with optimized ANSI color codes.
        """
        lines = []
        for character_row in self.merge_tiles(self.character_matrix):
            line = []
            for tile in character_row:
                bg = self.substitute_background_color(tile.bg)
                fg = self.substitute_foreground_color(tile.fg)
                line.append(colorize(tile.char, fg, bg))
            lines.append("".join(line))
        return "\n".join(lines)

    def substitute_background_color(self, code: ColorCode) -> ColorCode:
        return code if code is not None else self.BACKGROUND_COLOR

    def substitute_foreground_color(self, code: ColorCode) -> ColorCode:
        if code is None:
            return self.FOREGROUND_COLOR
        elif code == self.DEFAULT_SOIL:
            return self.SOIL_COLOR
        elif code == self.DEFAULT_COLOR_PRIMARY:
            if self.flower_color:
                return self.get_flower_color_code(self.flower_color)
            else:
                return code
        elif code == self.DEFAULT_COLOR_SECONDARY:
            if self.flower_color:
                return self.get_flower_color_code(self.flower_color, secondary=True)
            else:
                return code
        else:
            return code

    @classmethod
    def get_flower_color_code(cls, flower_color: str, secondary: bool = False):
        if flower_color == "rainbow":
            return next(cls.rainbow_generator)
        elif secondary:
            return cls.FLOWER_COLORS[flower_color][1]
        else:
            return cls.FLOWER_COLORS[flower_color][0]

    @classmethod
    def merge_tiles(cls, character_matrix: CharacterMatrix) -> CharacterMatrix:
        """
        Merge repeated tiles with the same styling into larger, single tiles.

        This minimizes the total number of ANSI escape sequences needed to
        render the final output.
        """
        new_matrix = []
        for character_row in character_matrix:
            line = character_row[:1]
            for tile in character_row[1:]:
                last_tile = line[-1]
                if tile.fg in (cls.DEFAULT_COLOR_PRIMARY, cls.DEFAULT_COLOR_SECONDARY):
                    # Never merge flowers, it screws up the rainbow color generation
                    line.append(tile)
                elif (tile.fg, tile.bg) == (last_tile.fg, last_tile.bg):
                    new_char = last_tile.char + tile.char
                    line[-1] = Tile(new_char, tile.bg, tile.fg)
                else:
                    line.append(tile)
            new_matrix.append(line)
        return new_matrix


@functools.lru_cache(maxsize=1000)
def render_art(
    filename: str, flower_color: Optional[str] = None, ansi_enabled: bool = False
) -> str:
    return ArtFile(filename, flower_color).render(ansi_enabled)
