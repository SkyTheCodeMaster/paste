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

app: web.Application = web.Application(
  middlewares=[web.normalize_path_middleware(append_slash=True,merge_slashes=True)]
)

LOG = logging.getLogger(__name__)

disabledCogs:list[str] = []
for cog in [f.replace(".py","") for f in os.listdir("cogs") if os.path.isfile(os.path.join("cogs",f))]:
  if cog not in disabledCogs:
    LOG.info(f"Loading {cog}...")
    routes = getRoutes(f"cogs.{cog}")
    app.add_routes(routes)

app.add_routes([web.static("/","static")])

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