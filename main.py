#!/usr/bin/env python3
import jetforce

from astrobotany import app, init_cache, init_db, settings

init_db(settings.db)
init_cache(settings.cache)

server = jetforce.GeminiServer(app)
server.run()
