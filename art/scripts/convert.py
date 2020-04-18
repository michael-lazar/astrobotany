import sys
import json


def colorize(fg, bg, text):
    return f"\033[38;5;{fg}m\033[48;5;{bg}m{text}\033[0m"


filename = sys.argv[1]
with open(filename) as fp:
    data = json.load(fp)


width, height = data["width"], data["height"]
tiles = iter(data["frames"][0]["layers"][0]["tiles"])
for _ in range(height):
    for _ in range(width):
        tile = next(tiles)
        char = chr(tile["char"]) or " "
        print(colorize(tile["fg"] - 1, tile["bg"] - 1, char), end="")
    print("\n", end="")
