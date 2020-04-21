import argparse
import json
import pathlib
import itertools


ART_DIRECTORY = pathlib.Path(__file__).parent.parent / "astrobotany" / "art"

# Default palette values
DEFAULT_CODE = 0
GROUND_CODE = 80
PRIMARY_CODE = 133
SECONDARY_CODE = 199

DEFAULT_CHAR = " "

# (primary, secondary)
COLORS = {
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
    "rainbow": (5, 145, 211, 193, 30, 198, 31),
}

SPECIES = [
    "poppy",
    "cactus",
    "aloe",
    "venusflytrap",
    "jadeplant",
    "fern",
    "daffodil",
    "sunflower",
    "baobab",
    "lithops",
    "hemp",
    "pansy",
    "iris",
    "agave",
    "ficus",
    "moss",
    "sage",
    "snapdragon",
    "columbine",
    "brugmansia",
    "palm",
    "pachypodium",
]


def colorize(text, fg=None, bg=None):
    if fg is not None:
        text = f"\033[38;5;{fg}m" + text
    if bg is not None:
        text = f"\033[48;5;{bg}m" + text
    if fg is not None or bg is not None:
        text = text + "\033[0m"
    return text


rainbow_gen = itertools.cycle(COLORS["rainbow"])


def lookup_code(code, flower_color):
    if flower_color is None:
        return code
    elif code == PRIMARY_CODE:
        if flower_color == "rainbow":
            return next(rainbow_gen)
        else:
            return COLORS[flower_color][0]
    elif code == SECONDARY_CODE:
        if flower_color == "rainbow":
            return next(rainbow_gen)
        else:
            return COLORS[flower_color][1]
    else:
        return code


parser = argparse.ArgumentParser()
parser.add_argument("--infile")
parser.add_argument("--species")
parser.add_argument("--stage")
parser.add_argument("--color")
parser.add_argument("--grid", type=int, default=3)
args = parser.parse_args()


if args.infile:
    filenames = [args.infile]
else:
    filenames = []
    for species in args.species or SPECIES:
        for stage in args.stage or [1, 2, 3]:
            filenames.append(f"{species}{stage}.psci")

color_list = [args.color] if args.color else COLORS.keys()

art_data_list = []
for filename in filenames:
    with (ART_DIRECTORY / "playscii" / filename).open() as fp:
        art_data = json.load(fp)
        if filename.endswith("3.psci"):
            for color in color_list:
                art_data_list.append((filename, color, art_data))
        else:
            art_data_list.append((filename, None, art_data))


for index in range(0, len(art_data_list), args.grid):
    art_data_line = art_data_list[index : index + args.grid]

    title = ""
    max_height = max(data[2]["height"] for data in art_data_line)
    lines = [""] * max_height
    for filename, flower_color, art_data in art_data_line:
        width, height = art_data["width"], art_data["height"]
        title += filename.center(width)
        tiles = iter(art_data["frames"][0]["layers"][0]["tiles"])
        for h in range(height):
            for _ in range(width):
                tile = next(tiles)
                char = chr(tile["char"]) if tile["char"] != 0 else DEFAULT_CHAR
                fg = (
                    lookup_code(tile["fg"], flower_color) + 15
                    if tile["fg"] != 0
                    else None
                )
                bg = (
                    lookup_code(tile["bg"], flower_color) + 15
                    if tile["bg"] != 1
                    else None
                )
                lines[h] += colorize(char, fg, bg)
        for h in range(height, max_height):
            lines[h] += DEFAULT_CHAR * width

    print("\n".join(lines))
    print(title)
    print("")
