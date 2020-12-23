#!/usr/bin/env python3
import jetforce

from astrobotany import app, init_db

init_db("astrobotany.sqlite")

server = jetforce.GeminiServer(app, hostname="127.0.0.1")
server.run()
