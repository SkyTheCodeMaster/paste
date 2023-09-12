import asyncio
import tomllib
import logging
import math
import os

import asyncpg
import coloredlogs
import aiohttp
from aiohttp import web

from utils.utils import get_routes
from utils.pg import PGUtils
# Constant variables
LOGFMT = "[%(filename)s][%(asctime)s][%(levelname)s] %(message)s"
LOGDATEFMT = "%Y/%m/%d-%H:%M:%S"

# Load the config file.
with open("config.toml") as f:
  config = tomllib.loads(f.read())

handlers = [
  logging.StreamHandler()
]

if config["log"]["file"]:
  handlers.append(logging.FileHandler(config["log"]["file"]))

logging.basicConfig(
  handlers = handlers,
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
    routes = get_routes(f"cogs.{cog}")
    app.add_routes(routes)

app.add_routes([web.static("/","static")])

async def startup():
  try:
    pool = await asyncpg.create_pool(
      config["pg"]["url"],
      password=config["pg"]["password"],
      timeout=config["pg"]["timeout"]
    )

    session = aiohttp.ClientSession()
    
    pg = PGUtils(pool)
    app.pg = pg
    app.pool = pool
    app.cs = session

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(
      runner,
      config["srv"]["host"],
      config["srv"]["port"],
    )
    await site.start()
    print(f"Started server on http://{config['srv']['host']}:{config['srv']['port']}...\nPress ^C to close...")
    await asyncio.sleep(math.inf)
  except KeyboardInterrupt:
    pass
  except asyncio.exceptions.TimeoutError:
    LOG.error("PostgresQL connection timeout. Check the connection arguments!")
  finally:
    try: await site.stop() 
    except: pass
    try: await pool.close()
    except: pass
    try: await session.close()
    except: pass


if __name__ == "__main__":
  asyncio.run(startup())