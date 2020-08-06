#!/usr/bin/env python3
import jetforce

from astrobotany import app, init_db

init_db("astrobotany.sqlite")

server = jetforce.GeminiServer(app, cafile="certs/ca.cer")
server.run()
