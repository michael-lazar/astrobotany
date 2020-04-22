import argparse

from astrobotany.art import ArtFile
from astrobotany.constants import COLORS, SPECIES


parser = argparse.ArgumentParser()
parser.add_argument("--infile")
parser.add_argument("--species")
parser.add_argument("--stage")
parser.add_argument("--color")
parser.add_argument("--grid", type=int, default=3)
args = parser.parse_args()

color_list = [args.color] if args.color else COLORS
species_list = [args.species] if args.species else SPECIES
stage_list = [args.stage] if args.stage else [1, 2, 3]

if args.infile:
    filenames = [args.infile]
else:
    filenames = []
    for species in species_list:
        for stage in stage_list:
            filenames.append(f"{species.replace(' ', '')}{stage}.psci")


art_files = []
for filename in filenames:
    if filename.endswith("3.psci"):
        for color in color_list:
            art_files.append(ArtFile(filename, color))
    else:
        art_files.append(ArtFile(filename))

for index in range(0, len(art_files), args.grid):
    art_line = art_files[index : index + args.grid]

    title = ""
    max_height = max(len(art.character_matrix) for art in art_line)
    lines = [""] * max_height
    for art in art_line:
        width, height = len(art.character_matrix[0]), len(art.character_matrix)
        title += art.filename.center(width)
        text = art.render(ansi_enabled=True)
        for i, line in enumerate(text.splitlines()):
            lines[i] += line.strip("\r\n")
        for h in range(height, max_height):
            lines[h] += " " * width

    print("\n".join(lines))
    print(title)
    print("")
