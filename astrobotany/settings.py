import os

if os.getenv("PRODUCTION"):
    db = "/etc/astrobotany/astrobotany.sqlite"
    cache = "/etc/astrobotany/astrobotany.cache"
else:
    db = "astrobotany.sqlite"
    cache = "astrobotany.cache"
