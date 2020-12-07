import re

from astrobotany import app

match_re = re.compile(r"\(\?P<(.+)>.+\)")

paths = []
for route, _ in app.routes:
    paths.append(match_re.sub(r"{\g<1>}", route.path) or "/")

for path in sorted(paths):
    print(path)
