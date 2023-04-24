from __future__ import annotations

import datetime
import json
import os
from typing import TYPE_CHECKING

import humanize
from aiohttp import web
from django.conf import settings as django_settings
from django import setup as django_setup
from django.template import Context, Engine
from utils.paste import Paste
from utils.token import Token
from utils.utils import Visibility

if TYPE_CHECKING:
  from typing import Any, Union
  import asyncpg
  from django.template import Template
  from utils.pg import PGUtils

django_settings.configure()
django_setup()

routes = web.RouteTableDef()

with open("config.json") as f:
  contents = f.read()
  config = json.loads(contents)
  USERNAME_MIN_LENGTH = config["user.name_min"]
  USERNAME_MAX_LENGTH = config["user.name_max"]

# Load all of the templates in the static folder.
engine = Engine()
templates: dict[str,Template] = {}
sup_templates: dict[str,Template] = {}

for file in [f for f in os.listdir("templates") if os.path.isfile(os.path.join("templates",f))]:
  with open(os.path.join("templates",file),"r") as f:
    tmpl = engine.from_string(f.read())
    templates[file] = tmpl

for file in [f for f in os.listdir("templates/supporting") if os.path.isfile(os.path.join("templates/supporting",f))]:
  with open(os.path.join("templates/supporting",file),"r") as f:
    tmpl = engine.from_string(f.read())
    sup_templates[file] = tmpl

latest_pastes_cache: list[Paste] = [] # A list of public Pastes for the sidebar.
latest_pastes_cache_age: int = 0

async def prepare_sidebar(request: web.Request, count: int = 8) -> tuple[list[dict[str,str]],Union[list[dict[str,str]],False]]:
  global latest_pastes_cache_age, latest_pastes_cache
  app: web.Application = request.app
  pool: asyncpg.Pool = app.pool
  async with pool.acquire() as conn:
    current_time = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    if current_time > latest_pastes_cache_age + 30:
      latest_pastes_cache = [Paste.from_record(record) for record in await conn.fetch("SELECT * FROM Pastes WHERE Visibility = 1 ORDER BY Created DESC LIMIT $1",count)]
      latest_pastes_cache_age = current_time + 30
    public_pastes: list[dict[str,str]] = [
      {
        "name":paste.title,
        "id": paste.id,
        "date":humanize.naturaltime(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromtimestamp(paste.created,datetime.timezone.utc)),
        "size":humanize.naturalsize(len(paste.data),gnu=True)
      } 
      for paste 
      in latest_pastes_cache
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
          "size":humanize.naturalsize(len(paste.data),gnu=True)
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
    return sup_templates["notloggedin.html"].source
  else:
    user = token.owner
    account = {
      "name": user.name
    }

    ctx_dict = {"account":account}
    return sup_templates["loggedin.html"].render(Context(ctx_dict))

async def prepare_navbar(request: web.Request) -> str:
  login_area = await prepare_account_area(request)
  ctx_dict = {"account": login_area}
  return sup_templates["navbar.html"].render(Context(ctx_dict))

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
  ctx_dict: dict[str,Any] = {
    "navbar":navbar,
    "public_pastes":public_pastes,
    "self_pastes":self_pastes,
    "config": {
      "USERNAME_MAX_LENGTH": USERNAME_MAX_LENGTH,
      "USERNAME_MIN_LENGTH": USERNAME_MIN_LENGTH
    }
  }
  rendered = templates["login.html"].render(Context(ctx_dict))
  return web.Response(body=rendered,content_type="text/html")

@routes.get("/signup")
async def get_index(request: web.Request) -> web.Response:
  # Load the index.html template
  public_pastes, self_pastes = await prepare_sidebar(request)
  navbar = await prepare_navbar(request)
  ctx_dict: dict[str,Any] = {
    "navbar":navbar,
    "public_pastes":public_pastes,
    "self_pastes":self_pastes,
    "config": {
      "USERNAME_MAX_LENGTH": USERNAME_MAX_LENGTH,
      "USERNAME_MIN_LENGTH": USERNAME_MIN_LENGTH
    }
  }
  rendered = templates["signup.html"].render(Context(ctx_dict))
  return web.Response(body=rendered,content_type="text/html")

@routes.get("/{tail:\w+}")
async def get_paste(request: web.Request) -> web.Response:
  pasteID: str = request.path.removeprefix("/")
  app: web.Application = request.app
  pg: PGUtils = app.pg

  paste: Paste = await pg.get_pastes_from_search(id=pasteID)

  text_content: Union[str,False] = ""

  if paste:
    paste = paste[0]
    if paste.visibility == Visibility.PRIVATE.value:
      token = await pg.handle_auth(request,no_exist_ok=True)
      if token and token.creator == paste.creator and token.permissions.view_private:
        text_content = paste.text_content
      else:
        text_content = False
    else:
      text_content = paste.text_content
  else:
    text_content = False

  public_pastes, self_pastes = await prepare_sidebar(request)
  navbar = await prepare_navbar(request)
  _ctx_dict: dict[str,Any] = {}
  if text_content:
    _ctx_dict["paste"] = {
      "lines": [line for line in text_content.splitlines()],
      "title": paste.title,
      "size": humanize.naturalsize(len(paste.data)),
    }
  else:
    _ctx_dict["paste"] = {
      "title": "The paste you are looking for either does not exist, or is private."
    }

  ctx_dict: dict[str,Any] = {"navbar":navbar,"public_pastes":public_pastes,"self_pastes":self_pastes}
  ctx_dict["paste"] = sup_templates["paste.html"].render(Context(_ctx_dict))

  return web.Response(body=templates["paste.html"].render(Context(ctx_dict)),content_type="text/html")

routes.static("/","static")

def setup() -> web.RouteTableDef:
  return routes
