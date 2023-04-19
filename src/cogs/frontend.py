from __future__ import annotations

import datetime
import os
from typing import TYPE_CHECKING

import humanize
from aiohttp import web
from django.conf import settings as django_settings
from django.template import Context, Engine
from utils.paste import Paste
from utils.token import Token

if TYPE_CHECKING:
  from typing import Any, Union
  import asyncpg
  from django.template import Template
  from utils.pg import PGUtils

django_settings.configure()

routes = web.RouteTableDef()

# Load all of the templates in the static folder.
engine = Engine()
templates: dict[str,Template] = {}

for file in os.listdir("templates"):
  with open(os.path.join("templates",file),"r") as f:
    tmpl = engine.from_string(f.read())
    templates[file] = tmpl

async def prepare_sidebar(request: web.Request, count: int = 8) -> tuple[list[dict[str,str]],Union[list[dict[str,str]],False]]:
  app: web.Application = request.app
  pool: asyncpg.Pool = app.pool
  async with pool.acquire() as conn:
    records = await conn.fetch("SELECT * FROM Pastes WHERE Visibility = 1 ORDER BY Created DESC LIMIT $1",count)
    pastes: list[Paste] = [Paste.from_record(record) for record in records]
    public_pastes: list[dict[str,str]] = [
      {
        "name":paste.title,
        "id": paste.id,
        "date":humanize.naturaltime(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromtimestamp(paste.created,datetime.timezone.utc)),
        "size":humanize.naturalsize(len(paste.data))
      } 
      for paste 
      in pastes
    ]
    token = await request.app.pg.handle_auth(request,strict_password=True,no_exist_ok=True)
    if type(token) is Token:
      records = await conn.fetch("SELECT * FROM Pastes WHERE Creator = $1 ORDER BY Created DESC LIMIT $2;",token.owner.id,count)
      pastes: list[Paste] = [Paste.from_record(record) for record in records]
      self_pastes: list[dict[str,str]] = [
        {
          "name":paste.title,
          "id": paste.id,
          "date":humanize.naturaltime(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromtimestamp(paste.created,datetime.timezone.utc)),
          "size":humanize.naturalsize(len(paste.data))
        } 
        for paste 
        in pastes
      ]
      return public_pastes,self_pastes
    return public_pastes,False

async def prepare_account_area(request: web.Request) -> str:
  pg: PGUtils = request.app.pg
  token = await pg.handle_auth(request,strict_password=True,no_exist_ok=True)
  if type(token) != Token:
    # This means that there is no valid authorization, and we should display the "log in"
    # and "sign up" buttons.
    return templates["notloggedin.html"].source
  else:
    user = token.owner
    account = {
      "name": user.name
    }

    ctx_dict = {"account":account}
    return templates["loggedin.html"].render(Context(ctx_dict))

async def prepare_navbar(request: web.Request) -> str:
  login_area = await prepare_account_area(request)
  ctx_dict = {"account": login_area}
  return templates["navbar.html"].render(Context(ctx_dict))

@routes.get("/")
async def get_index(request: web.Request) -> web.Response:
  # Load the index.html template
  public_pastes, self_pastes = await prepare_sidebar(request)
  navbar = await prepare_navbar(request)
  ctx_dict: dict[str,Any] = {"navbar":navbar,"public_pastes":public_pastes,"self_pastes":self_pastes}
  rendered = templates["index.html"].render(Context(ctx_dict))
  return web.Response(body=rendered,content_type="text/html")

@routes.get("/login")
async def get_index(request: web.Request) -> web.Response:
  # Load the index.html template
  public_pastes, self_pastes = await prepare_sidebar(request)
  navbar = await prepare_navbar(request)
  ctx_dict: dict[str,Any] = {"navbar":navbar,"public_pastes":public_pastes,"self_pastes":self_pastes}
  rendered = templates["login.html"].render(Context(ctx_dict))
  return web.Response(body=rendered,content_type="text/html")

def setup() -> web.RouteTableDef:
  return routes
