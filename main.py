#!/usr/bin/env python3
import asyncio

import jetforce

from astrobotany import init_db, vhost

init_db("astrobotany.sqlite")

app = jetforce.JetforceApplication()
app.route()(vhost)

cafile = "certs/ca.cer"
ssl_context = jetforce.make_ssl_context(cafile=cafile)
server = jetforce.GeminiServer(app=app, ssl_context=ssl_context)
asyncio.run(server.run())
