import asyncio
import importlib.util
import json
import logging
import math
import os

import asyncpg
import coloredlogs
import django.template
from aiohttp import web
from django.conf import settings

from utils.utils import getRoutes
from utils.pg import PGUtils
# Constant variables
LOGFMT = "[%(filename)s][%(asctime)s][%(levelname)s] %(message)s"
LOGDATEFMT = "%Y/%m/%d-%H:%M:%S"

# Load the config file.
with open("config.json") as f:
  config = json.loads(f.read())

logging.basicConfig(
  handlers = [
    #logging.FileHandler(config["log.file"]),
    logging.StreamHandler(),
  ],
  format=LOGFMT,
  datefmt=LOGDATEFMT,
  level=logging.INFO,
)

coloredlogs.install(
  fmt=LOGFMT,
  datefmt=LOGDATEFMT
)

app: web.Application = web.Application()

disabledCogs = []
for cog in [f.replace(".py","") for f in os.listdir("cogs") if os.path.isfile(os.path.join("cogs",f))]:
  if cog not in disabledCogs:
    routes = getRoutes(f"cogs.{cog}")
    app.add_routes(routes)

async def startup():
  try:
    conn = await asyncpg.connect(config["pg.url"],password=config["pg.password"])
    
    pgUtils = PGUtils(conn)
    app.pgUtils = pgUtils

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(
      runner,
      config["srv.host"],
      config["srv.port"],
    )
    await site.start()
    
    await asyncio.sleep(math.inf)
  except KeyboardInterrupt:
    pass
  finally:
    await site.stop()

if __name__ == "__main__":
  asyncio.run(startup())