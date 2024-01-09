import os

if os.getenv("PRODUCTION"):
    db = "/etc/astrobotany/astrobotany.sqlite"
else:
    db = "astrobotany.sqlite"
