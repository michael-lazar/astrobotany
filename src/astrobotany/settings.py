import os

if os.getenv("PRODUCTION"):
    db = "/etc/astrobotany/astrobotany.sqlite"
else:
    db = "data/astrobotany.sqlite"
