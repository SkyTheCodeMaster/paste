from __future__ import annotations

import datetime
import os
import pathlib
import tomllib
from typing import TYPE_CHECKING

import humanize
from aiohttp import web
from django import setup as django_setup
from django.conf import settings as django_settings
from django.template import Context, Engine

from utils.paste import Paste
from utils.token import Token
from utils.utils import Visibility

if TYPE_CHECKING:
  from typing import Any, Union

  import asyncpg
  from django.template import Template

  from utils.pg import PGUtils
  from utils.user import User

django_settings.configure()
django_setup()

routes = web.RouteTableDef()

grand_context = {}

with open("config.toml") as f:
  contents = f.read()
  config = tomllib.loads(contents)
  USERNAME_MIN_LENGTH = config["user"]["name_min"]
  USERNAME_MAX_LENGTH = config["user"]["name_max"]
  PASSWORD_MIN_LENGTH = config["user"]["password_min"]
  PASSWORD_MAX_LENGTH = config["user"]["password_max"]
  PUBLIC_PASTE_LINES_SHOWN = config["paste"]["public"]["lines_shown"]
  PUBLIC_PASTE_CHARS_SHOWN = config["paste"]["public"]["characters_shown"]
  PASTE_SIDEBAR_NUM_SHOW = config["paste"]["show_number"]
  PUBLIC_PASTE_NAME_LENGTH = config["paste"]["public"]["name_max_length"]
  grand_context["public_url"] = config["srv"]["publicurl"]

# Load all of the templates in the static folder.
engine = Engine()
templates: dict[str,Template] = {}
sup_templates: dict[str,Template] = {}

def join(a: str, b: str) -> str:
  "Join 2 filepaths"
  return str(pathlib.Path(a).joinpath(pathlib.Path(b)))

for root, dirs, files in os.walk("templates"):
  if "supporting" in root: continue
  for file in files:
    filepath = join(root,file)
    with open(filepath,"r") as f:
      tmpl = engine.from_string(f.read())
      templates[filepath.removeprefix("templates").removeprefix("/")] = tmpl

for root, dirs, files in os.walk("templates/supporting"):
  for file in files:
    filepath = join(root,file)
    with open(filepath,"r") as f:
      tmpl = engine.from_string(f.read())
      sup_templates[filepath.removeprefix("templates/supporting").removeprefix("/")] = tmpl

def reload_files():
  for root, dirs, files in os.walk("templates"):
    if "supporting" in root: continue
    for file in files:
      filepath = join(root,file)
      with open(filepath,"r") as f:
        tmpl = engine.from_string(f.read())
        templates[filepath.removeprefix("templates").removeprefix("/")] = tmpl

  for root, dirs, files in os.walk("templates/supporting"):
    for file in files:
      filepath = join(root,file)
      with open(filepath,"r") as f:
        tmpl = engine.from_string(f.read())
        sup_templates[filepath.removeprefix("templates/supporting").removeprefix("/")] = tmpl

latest_pastes_cache: list[Paste] = [] # A list of public Pastes for the sidebar.
latest_pastes_cache_age: int = 0

def get_first_x_lines(input: str, x: int) -> str:
  l: list[str] = input.split("\n")
  # I've noticed that 42 chars is better for not making scrollbars on fullhd monitors
  k = [s[:42] for s in l]
  return "\n".join(k[:x])

def process_paste_content(input: str) -> str:
  "Trim paste content and make it nice"
  trimmed_lines = get_first_x_lines(input, PUBLIC_PASTE_LINES_SHOWN)
  return trimmed_lines[:PUBLIC_PASTE_CHARS_SHOWN]

async def refresh_sidebar_pastes(conn: asyncpg.Connection, count: int = 8):
  global latest_pastes_cache_age, latest_pastes_cache
  latest_pastes_cache = [Paste.from_record(record) for record in await conn.fetch("SELECT * FROM Pastes WHERE Visibility = 1 ORDER BY Created DESC LIMIT $1",count)]
  latest_pastes_cache_age = int(datetime.datetime.now(datetime.timezone.utc).timestamp()) + 30

async def prepare_sidebar(request: web.Request, count: int = 8) -> str:
  global latest_pastes_cache_age, latest_pastes_cache
  app: web.Application = request.app
  pool: asyncpg.Pool = app.pool
  async with pool.acquire() as conn:
    current_time = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    if current_time > latest_pastes_cache_age + 30:
      latest_pastes_cache = [Paste.from_record(record) for record in await conn.fetch("SELECT * FROM Pastes WHERE Visibility = 1 ORDER BY Created DESC LIMIT $1",count)]
      latest_pastes_cache_age = current_time + 30
    public_pastes: list[str] = [
      sup_templates["paste/public.html"].render(Context({
        "name":paste.title if len(paste.title) < PUBLIC_PASTE_NAME_LENGTH  else f"{paste.title[:PUBLIC_PASTE_NAME_LENGTH ]}…",
        "id": paste.id,
        "date":humanize.naturaltime(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromtimestamp(paste.created,datetime.timezone.utc)),
        "size":humanize.naturalsize(len(paste.data),gnu=True),
        "content": process_paste_content(paste.text_content),
        "syntax": paste.syntax,
        "author": (await paste.get_creator(app.pg)).name
      }))
      for paste 
      in latest_pastes_cache
    ]
    public_out = "\n\n".join(public_pastes)
    token = await request.app.pg.handle_auth(request,strict_password=True,no_exist_ok=True)
    if type(token) is Token:
      records = await conn.fetch("SELECT * FROM Pastes WHERE Creator = $1 ORDER BY Created DESC LIMIT $2;",token.owner.id,count)
      pastes: list[Paste] = [Paste.from_record(record) for record in records]
      self_pastes: list[str] = [
        sup_templates["paste/public.html"].render(Context({
          "name":paste.title if len(paste.title) < PUBLIC_PASTE_NAME_LENGTH  else f"{paste.title[:PUBLIC_PASTE_NAME_LENGTH ]}…",
          "id": paste.id,
          "date":humanize.naturaltime(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromtimestamp(paste.created,datetime.timezone.utc)),
          "size":humanize.naturalsize(len(paste.data),gnu=True),
          "content": process_paste_content(paste.text_content),
          "syntax": paste.syntax,
          "author": (await paste.get_creator(app.pg)).name
        }))
        for paste 
        in pastes
      ]
      self_out = "\n\n".join(self_pastes)
      return sup_templates["paste/sidebar.html"].render(Context({"public_pastes": public_out, "self_pastes": self_out}))
    return sup_templates["paste/sidebar.html"].render(Context({"public_pastes": public_out, "self_pastes": False}))

async def prepare_account_area(request: web.Request) -> str:
  pg: PGUtils = request.app.pg
  token = await pg.handle_auth(request,strict_password=True,no_exist_ok=True)
  if type(token) != Token:
    # This means that there is no valid authorization, and we should display the "log in"
    # and "sign up" buttons.
    return sup_templates["account/not_logged_in.html"].source
  else:
    user = token.owner
    account = {
      "name": user.name.lower(),
      "Name": user.name
    }

    ctx_dict = {**grand_context, "account":account}
    return sup_templates["account/logged_in.html"].render(Context(ctx_dict))

async def prepare_navbar(request: web.Request) -> str:
  login_area = await prepare_account_area(request)
  ctx_dict = {
    **grand_context, 
    "account": login_area
  }
  return sup_templates["navbar.html"].render(Context(ctx_dict))

@routes.get("/")
async def get_index(request: web.Request) -> web.Response:
  # Check devmode
  if config["devmode"]:
    reload_files()
  # Load the index.html template
  pg: PGUtils = request.app.pg

  paste_sidebar = await prepare_sidebar(request, PASTE_SIDEBAR_NUM_SHOW)
  navbar = await prepare_navbar(request)

  token = await pg.handle_auth(request,strict_password=True,no_exist_ok=True)
  authorized = type(token) is Token

  ctx_dict: dict[str,Any] = {
    **grand_context, 
    "navbar":navbar,
    "footer": sup_templates["footer.html"].source,
    "paste_sidebar": paste_sidebar,
    "authorized": authorized,
    "create_paste": sup_templates["paste/create.html"].source
  }
  rendered = templates["index.html"].render(Context(ctx_dict))
  return web.Response(body=rendered,content_type="text/html")

@routes.get("/login")
async def get_index(request: web.Request) -> web.Response:
  # Check devmode
  if config["devmode"]:
    reload_files()
  # Load the index.html template
  paste_sidebar = await prepare_sidebar(request, PASTE_SIDEBAR_NUM_SHOW)
  navbar = await prepare_navbar(request)
  ctx_dict: dict[str,Any] = {
    **grand_context, 
    "navbar":navbar,
    "footer": sup_templates["footer.html"].source,
    "paste_sidebar": paste_sidebar,
    "config": {
      "USERNAME_MAX_LENGTH": USERNAME_MAX_LENGTH,
      "USERNAME_MIN_LENGTH": USERNAME_MIN_LENGTH,
    }
  }
  rendered = templates["login/login.html"].render(Context(ctx_dict))
  return web.Response(body=rendered,content_type="text/html")

@routes.get("/signup")
async def get_index(request: web.Request) -> web.Response:
  # Check devmode
  if config["devmode"]:
    reload_files()
  # Load the index.html template
  paste_sidebar = await prepare_sidebar(request, PASTE_SIDEBAR_NUM_SHOW)
  navbar = await prepare_navbar(request)
  ctx_dict: dict[str,Any] = {
    **grand_context, 
    "navbar":navbar,
    "footer": sup_templates["footer.html"].source,
    "paste_sidebar": paste_sidebar,
    "config": {
      "USERNAME_MAX_LENGTH": USERNAME_MAX_LENGTH,
      "USERNAME_MIN_LENGTH": USERNAME_MIN_LENGTH,
      "PASSWORD_MAX_LENGTH": PASSWORD_MAX_LENGTH,
      "PASSWORD_MIN_LENGTH": PASSWORD_MIN_LENGTH,
    }
  }
  rendered = templates["login/signup.html"].render(Context(ctx_dict))
  return web.Response(body=rendered,content_type="text/html")

@routes.get("/user/{user_name:\w+}/")
async def get_user(request: web.Request) -> web.Response:
  user_name = request.match_info["user_name"]
  print(user_name)
  app: web.Application = request.app
  pg: PGUtils = app.pg

  user: User = await pg.get_user(name=user_name.lower())

  # Check devmode
  if config["devmode"]:
    reload_files()
  # Load the index.html template
  paste_sidebar = await prepare_sidebar(request, PASTE_SIDEBAR_NUM_SHOW)
  navbar = await prepare_navbar(request)

  if not user:
    ctx_dict = {
      "navbar": navbar,
    "footer": sup_templates["footer.html"].source,
      "paste_sidebar": paste_sidebar
    }
    rendered = templates["user/not_exists.html"].render(Context(ctx_dict))
    return web.Response(body=rendered,content_type="text/html")

  token = await pg.handle_auth(request,strict_password=True,no_exist_ok=True)
  authorized = type(token) is Token

  pastes: list[Paste] = await pg.get_pastes_from_creator(creator=user.id)
  if not authorized:
    pastes = list(filter(lambda paste: paste.visibility == 1, pastes))
  pastes = sorted(pastes, key=lambda paste: -paste.created)

  folders: set[dict] = set()
  for paste in pastes.copy():
    if paste.folder:
      folders.add(paste.folder)
      pastes.remove(paste)

  def suffix(x):
    if len(str(x)) > 1 and str(x)[-2] == "1":
      return f"{x}th"
    elif x % 10 == 1:
      return f"{x}st"
    elif x % 10 == 2:
      return f"{x}nd"
    elif x % 10 == 3:
      return f"{x}rd"
    else:
      return f"{x}th"
    
  def ftime(format, t):
    return t.strftime(format).replace('{S}', suffix(t.day))
  
  visibility_icon = {
    1: "vaadin:globe",
    2: "system-uicons:chain",
    3: "mdi:lock"
  }
  visibility_title = {
    1: "This paste is globally accessible by anyone.",
    2: "This paste is only accessible to those with the link.",
    3: "This paste is only accessible by you."
  }

  template_pastes = [
    {
      "title": paste.title,
      "real_time": ftime("%b {S}, %Y",datetime.datetime.fromtimestamp(paste.created, datetime.timezone.utc)),
      "relative_time":humanize.naturaltime(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromtimestamp(paste.created,datetime.timezone.utc)),
      "size":humanize.naturalsize(len(paste.data),gnu=True),
      "id": paste.id,
      "Syntax": paste.syntax.title(),
      "visibility_icon": visibility_icon[paste.visibility],
      "visibility_title": visibility_title[paste.visibility]
    }
    for paste in pastes
  ]

  c_user = {
    "name": user.name,
    "join": ftime("%b {S}, %Y",datetime.datetime.fromtimestamp(user.joindate, datetime.timezone.utc)),
    "relative_join": humanize.naturaltime(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromtimestamp(user.joindate,datetime.timezone.utc))
  }

  ctx_dict = {
    "folders": folders,
    "pastes": template_pastes,
    "user": c_user,
    "navbar": navbar,
    "footer": sup_templates["footer.html"].source,
    "paste_sidebar": paste_sidebar,
  }
  rendered = templates["user/exists.html"].render(Context(ctx_dict))
  return web.Response(body=rendered,content_type="text/html")

@routes.get("/user/{user_name:\w+}/{folder:\w+}/")
async def get_user(request: web.Request) -> web.Response:
  user_name = request.match_info["user_name"]
  folder = request.match_info["folder"]
  print(user_name)
  app: web.Application = request.app
  pg: PGUtils = app.pg

  user: User = await pg.get_user(name=user_name.lower())

  # Check devmode
  if config["devmode"]:
    reload_files()
  # Load the index.html template
  paste_sidebar = await prepare_sidebar(request, PASTE_SIDEBAR_NUM_SHOW)
  navbar = await prepare_navbar(request)

  if not user:
    ctx_dict = {
      "navbar": navbar,
    "footer": sup_templates["footer.html"].source,
      "paste_sidebar": paste_sidebar
    }
    rendered = templates["user/not_exists.html"].render(Context(ctx_dict))
    return web.Response(body=rendered,content_type="text/html")

  token = await pg.handle_auth(request,strict_password=True,no_exist_ok=True)
  authorized = type(token) is Token

  pastes: list[Paste] = await pg.get_pastes_from_creator(creator=user.id)
  if not authorized:
    pastes = list(filter(lambda paste: paste.visibility == 1, pastes))
  pastes = sorted(pastes, key=lambda paste: -paste.created)
  pastes = list(filter(lambda paste: paste.folder == folder, pastes))

  def suffix(x):
    if len(str(x)) > 1 and str(x)[-2] == "1":
      return f"{x}th"
    elif x % 10 == 1:
      return f"{x}st"
    elif x % 10 == 2:
      return f"{x}nd"
    elif x % 10 == 3:
      return f"{x}rd"
    else:
      return f"{x}th"
    
  def ftime(format, t):
    return t.strftime(format).replace('{S}', suffix(t.day))
  
  visibility_icon = {
    1: "vaadin:globe",
    2: "system-uicons:chain",
    3: "mdi:lock"
  }
  visibility_title = {
    1: "This paste is globally accessible by anyone.",
    2: "This paste is only accessible to those with the link.",
    3: "This paste is only accessible by you."
  }

  template_pastes = [
    {
      "title": paste.title,
      "real_time": ftime("%b {S}, %Y",datetime.datetime.fromtimestamp(paste.created, datetime.timezone.utc)),
      "relative_time":humanize.naturaltime(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromtimestamp(paste.created,datetime.timezone.utc)),
      "size":humanize.naturalsize(len(paste.data),gnu=True),
      "id": paste.id,
      "Syntax": paste.syntax.title(),
      "visibility_icon": visibility_icon[paste.visibility],
      "visibility_title": visibility_title[paste.visibility]
    }
    for paste in pastes
  ]

  c_user = {
    "name": user.name,
    "join": ftime("%b {S}, %Y",datetime.datetime.fromtimestamp(user.joindate, datetime.timezone.utc)),
    "relative_join": humanize.naturaltime(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromtimestamp(user.joindate,datetime.timezone.utc))
  }

  ctx_dict = {
    "folder_name": f"{folder} folder",
    "pastes": template_pastes,
    "user": c_user,
    "navbar": navbar,
    "footer": sup_templates["footer.html"].source,
    "paste_sidebar": paste_sidebar,
  }
  rendered = templates["user/exists.html"].render(Context(ctx_dict))
  return web.Response(body=rendered,content_type="text/html")

@routes.get("/settings/")
async def get_settings(request: web.Request) -> web.Response:
  # Check devmode
  if config["devmode"]:
    reload_files()
  raise web.HTTPFound("/settings/general")

@routes.get("/settings/{tail:\w+$}")
async def get_settings_subpage(request: web.Request) -> web.Response:
  subpage: str = request.path.removeprefix("/settings/")
  app: web.Application = request.app
  pg: PGUtils = app.pg

  # Check devmode
  if config["devmode"]:
    reload_files()
  # Load the index.html template
  paste_sidebar = await prepare_sidebar(request, PASTE_SIDEBAR_NUM_SHOW)
  navbar = await prepare_navbar(request)

  pages = {
    "general": "settings/general/general.html",
    "security": "settings/general/security.html",
    "apitokens": "settings/developer/apitokens.html"
  }

  page_template = sup_templates[pages[subpage]]

  token = await pg.handle_auth(request,strict_password=True,no_exist_ok=False)
  if type(token) is not Token:
    return token
  
  user = token.owner
  _ctx_dict = {
    "user": {
      "Name": user.name,
      "name": user.name.lower(),
      "email_dots": "•"*len(user.email)
    }
  }

  if subpage == "apitokens":
    tokens_list = await pg.get_tokens_from_user(user)

    def apply_icons(tok: Token):
      get_icon = lambda x: "mdi:check" if x else "ph:x"
      perms = tok.permissions
      d = {
        "name": tok.name,
        "id": tok.ident,
        "perm": {
          "create": get_icon(perms.create_paste),
          "edit": get_icon(perms.edit_paste),
          "delete": get_icon(perms.delete_paste),
          "viewpriv": get_icon(perms.view_private)
        }
      }
      return d

    _ctx_dict["tokens"] = {
      "list": [apply_icons(tk) for tk in tokens_list]
    }

  settings_content = page_template.render(Context(_ctx_dict))

  ctx_dict = {
    "navbar": navbar,
    "footer": sup_templates["footer.html"].source,
    "paste_sidebar": paste_sidebar,
    "settings_menu": sup_templates["settings/menu.html"].render(Context({"subpage":subpage})),
    "settings_content": settings_content,
    "config": {
      "USERNAME_MAX_LENGTH": USERNAME_MAX_LENGTH,
      "USERNAME_MIN_LENGTH": USERNAME_MIN_LENGTH,
      "PASSWORD_MAX_LENGTH": PASSWORD_MAX_LENGTH,
      "PASSWORD_MIN_LENGTH": PASSWORD_MIN_LENGTH,
    }
  }
  rendered = templates["settings/main.html"].render(Context(ctx_dict))
  return web.Response(body=rendered,content_type="text/html")

@routes.get("/dl/{tail:\w+$}")
async def get_dl_paste(request: web.Request) -> web.Response:
  # Check devmode
  if config["devmode"]:
    reload_files()
  pasteID: str = request.path.removeprefix("/dl/")
  app: web.Application = request.app
  pg: PGUtils = app.pg

  paste: Paste = await pg.get_pastes_from_search(id=pasteID)

  if paste:
    paste = paste[0]
    if paste.visibility == Visibility.PRIVATE.value:
      token = await pg.handle_auth(request,no_exist_ok=True)
      if not (token and token.creator == paste.creator and token.permissions.view_private):
        return web.Response(status=404,body="404: not found")
  else:
    return web.Response(status=404,body="404: not found")

  resp: web.StreamResponse = web.StreamResponse()
  resp.headers["Content-Type"] = "text/plain"
  resp.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{pasteID}.txt"
  await resp.prepare(request)
  await resp.write(paste.data)
  return resp

@routes.get("/raw/{tail:\w+$}")
async def get_raw_paste(request: web.Request) -> web.Response:
  # Check devmode
  if config["devmode"]:
    reload_files()
  pasteID: str = request.path.removeprefix("/raw/")
  app: web.Application = request.app
  pg: PGUtils = app.pg

  paste: Paste = await pg.get_pastes_from_search(id=pasteID)

  if paste:
    paste = paste[0]
    if paste.visibility == Visibility.PRIVATE.value:
      token = await pg.handle_auth(request,no_exist_ok=True)
      if token and token.creator == paste.creator and token.permissions.view_private:
        return web.Response(body=paste.text_content,content_type="text/plain")
      else:
        return web.Response(status=404)
    else:
      return web.Response(body=paste.text_content,content_type="text/plain")
  else:
    return web.Response(status=404)

@routes.get("/edit/{tail:\w+$}")
async def get_paste(request: web.Request) -> web.Response:
  # Check devmode
  if config["devmode"]:
    reload_files()
  pasteID: str = request.path.removeprefix("/edit/")
  app: web.Application = request.app
  pg: PGUtils = app.pg

  paste: Paste = await pg.get_pastes_from_search(id=pasteID)

  text_content: Union[str,False] = ""
  authorized:   bool = False
  logged_in:    bool = False
  if paste:
    token = await pg.handle_auth(request,no_exist_ok=True)
    paste = paste[0]
    p_owner: User = await paste.get_creator(pg)
    if p_owner != token.owner:
      text_content = False
    else:
      text_content = paste.text_content

    authorized = type(token) is Token and token.owner == p_owner
    logged_in  = type(token) is Token
  else:
    text_content = False

  paste_sidebar = await prepare_sidebar(request, PASTE_SIDEBAR_NUM_SHOW)
  navbar = await prepare_navbar(request)
  _ctx_dict: dict[str,Any] = {
    "authorized": authorized,
    "logged_in": logged_in,
  }
  if text_content:
    _ctx_dict["paste"] = {
      **grand_context, 
      "text":text_content,
      "title": paste.title,
      "Syntax": paste.syntax.title(),
      "syntax": paste.syntax,
      "tags": paste.tags or False,
      "visibility": paste.visibility,
      "id": paste.id,
    }
    ctx_dict: dict[str,Any] = {**grand_context, "navbar":navbar,"paste_sidebar":paste_sidebar}
    ctx_dict["edit_paste"] = sup_templates["paste/edit.html"].render(Context(_ctx_dict))
  else:
    _ctx_dict["paste"] = {
      **grand_context, 
      "title": "The paste you are looking for either does not exist, or is private."
    }
    ctx_dict: dict[str,Any] = {**grand_context, "navbar":navbar,"footer": sup_templates["footer.html"].source,"paste_sidebar":paste_sidebar}
    ctx_dict["edit_paste"] = sup_templates["paste/main_no_exist.html"].render(Context(_ctx_dict))

  rendered = templates["paste_edit.html"].render(Context(ctx_dict))
  return web.Response(body=rendered,content_type="text/html")

@routes.get("/tos")
async def get_terms_of_service(request: web.Request) -> web.Response:
  # Check devmode
  if config["devmode"]:
    reload_files()
  app: web.Application = request.app

  paste_sidebar = await prepare_sidebar(request, PASTE_SIDEBAR_NUM_SHOW)
  navbar = await prepare_navbar(request)

  ctx_dict = {
    "navbar": navbar,
    "footer": sup_templates["footer.html"].source,
    "paste_sidebar": paste_sidebar
  }

  return web.Response(body=templates["legal/tos.html"].render(Context(ctx_dict)),content_type="text/html")

@routes.get("/privacy")
async def get_terms_of_service(request: web.Request) -> web.Response:
  # Check devmode
  if config["devmode"]:
    reload_files()
  app: web.Application = request.app

  paste_sidebar = await prepare_sidebar(request, PASTE_SIDEBAR_NUM_SHOW)
  navbar = await prepare_navbar(request)

  ctx_dict = {
    "navbar": navbar,
    "footer": sup_templates["footer.html"].source,
    "paste_sidebar": paste_sidebar
  }

  return web.Response(body=templates["legal/privacy.html"].render(Context(ctx_dict)),content_type="text/html")

@routes.get("/{tail:\w+$}")
async def get_paste(request: web.Request) -> web.Response:
  # Check devmode
  if config["devmode"]:
    reload_files()
  pasteID: str = request.path.removeprefix("/")
  app: web.Application = request.app
  pg: PGUtils = app.pg

  paste: Paste = await pg.get_pastes_from_search(id=pasteID)

  text_content: Union[str,False] = ""
  authorized:   bool = False
  logged_in:    bool = False
  if paste:
    token = await pg.handle_auth(request,no_exist_ok=True)
    paste = paste[0]
    p_owner: User = await paste.get_creator(pg)
    if paste.visibility == Visibility.PRIVATE.value:
      if type(token) is Token and token.owner == p_owner and token.permissions.view_private:
        text_content = paste.text_content
      else:
        text_content = False
    else:
      text_content = paste.text_content
    authorized = type(token) is Token and token.owner == p_owner
    logged_in  = type(token) is Token

  else:
    text_content = False

  paste_sidebar = await prepare_sidebar(request, PASTE_SIDEBAR_NUM_SHOW)
  navbar = await prepare_navbar(request)
  _ctx_dict: dict[str,Any] = {
    "authorized": authorized,
    "logged_in": logged_in,
  }

  def suffix(x):
    if len(str(x)) > 1 and str(x)[-2] == "1":
      return f"{x}th"
    elif x % 10 == 1:
      return f"{x}st"
    elif x % 10 == 2:
      return f"{x}nd"
    elif x % 10 == 3:
      return f"{x}rd"
    else:
      return f"{x}th"
    
  def ftime(format, t):
    return t.strftime(format).replace('{S}', suffix(t.day))

  if text_content:
    _ctx_dict["paste"] = {
      **grand_context, 
      "text":text_content,
      "title": paste.title,
      "size": humanize.naturalsize(len(paste.data)),
      "relative_time": humanize.naturaltime(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromtimestamp(paste.created,datetime.timezone.utc)),
      "real_time": ftime("%b {S}, %Y",datetime.datetime.fromtimestamp(paste.created, datetime.timezone.utc)),
      "id": paste.id,
      "Syntax": paste.syntax.title(),
      "syntax": paste.syntax,
      "linerange": range(text_content.count("\n")+1),
      "tags": paste.tags and paste.tags.split(",") or False,
      "folder": paste.folder
    }
    p_owner: User = await paste.get_creator(pg)
    _ctx_dict["user"] = {
      "name": p_owner.name
    }
    ctx_dict: dict[str,Any] = {**grand_context, "navbar":navbar,"paste_sidebar":paste_sidebar}
    ctx_dict["paste"] = sup_templates["paste/main.html"].render(Context(_ctx_dict))
  else:
    _ctx_dict["paste"] = {
      **grand_context, 
      "title": "The paste you are looking for either does not exist, or is private."
    }
    ctx_dict: dict[str,Any] = {**grand_context, "navbar":navbar,"footer": sup_templates["footer.html"].source,"paste_sidebar":paste_sidebar}
    ctx_dict["paste"] = sup_templates["paste/main_no_exist.html"].render(Context(_ctx_dict))

  return web.Response(body=templates["paste.html"].render(Context(ctx_dict)),content_type="text/html")

def setup() -> web.RouteTableDef:
  return routes