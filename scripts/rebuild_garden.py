#!/usr/bin/env python3
from astrobotany import init_db, settings
from astrobotany.garden import rebuild_garden

init_db(settings.db)

data = rebuild_garden()
print(data['ansi'])
print("")
print(data['plain'])
