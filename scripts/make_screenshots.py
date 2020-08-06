import subprocess
import sys

import astrobotany.constants

for species in sorted(astrobotany.constants.SPECIES):
    cmd = (
        f"{sys.executable} scripts/demo_art.py --grid 4 --match-background "
        f"--species {species.replace(' ', '')} "
        f"--title '{species.capitalize()}' | less -r"
    )
    subprocess.run(cmd, shell=True, check=True)
