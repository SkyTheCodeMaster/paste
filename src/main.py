import asyncio
import json
import logging
import math
import os

import asyncpg
import coloredlogs
from aiohttp import web

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

@web.middleware
async def error_middleware(request, handler):
  try:
    response = await handler(request)
    if response.status != 404:
      return response
    message = response.message
  except web.HTTPException as ex:
    if ex.status != 404:
      raise
    message = ex.reason
  return web.json_response({'error': message})

LOG = logging.getLogger(__name__)

disabledCogs = []
for cog in [f.replace(".py","") for f in os.listdir("cogs") if os.path.isfile(os.path.join("cogs",f))]:
  if cog not in disabledCogs:
    LOG.info(f"Loading {cog}...")
    routes = getRoutes(f"cogs.{cog}")
    app.add_routes(routes)

async def startup():
  try:
    pool = await asyncpg.create_pool(
      config["pg.url"],
      password=config["pg.password"],
      timeout=config["pg.timeout"]
    )
    
    pg = PGUtils(pool)
    app.pg = pg
    app.pool = pool

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(
      runner,
      config["srv.host"],
      config["srv.port"],
    )
    await site.start()
    print(f"Started server on http://{config['srv.host']}:{config['srv.port']}...\nPress ^C to close...")
    await asyncio.sleep(math.inf)
  except KeyboardInterrupt:
    pass
  except asyncio.exceptions.TimeoutError:
    LOG.error("PostgresQL connection timeout. Check the connection arguments!")
  finally:
    try: await site.stop() 
    except: pass

if __name__ == "__main__":
  asyncio.run(startup())