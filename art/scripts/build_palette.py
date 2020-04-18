# ANSI Extended Palette
# 6x6x6 color cube + 24 greyscale colors
# The 0-15 system colors are excluded


def colorize(fg, bg, text):
    return f"\033[38;5;{fg}m\033[48;5;{bg}m{text}\033[0m"


line = []
for i in range(16, 256):
    line.append(colorize(0, i, " "))
    if len(line) == 24:
        print("".join(line))
        line = []
