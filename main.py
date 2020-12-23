#!/usr/bin/env python3
import jetforce

from astrobotany import app, init_db, settings

init_db(settings.db)

server = jetforce.GeminiServer(app, hostname="127.0.0.1")
server.run()
