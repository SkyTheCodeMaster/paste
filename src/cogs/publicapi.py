from __future__ import annotations

import json
import logging
import math
import re
from typing import TYPE_CHECKING

import aiohttp
from aiohttp import web

from utils.paste import Paste
from utils.utils import Visibility

if TYPE_CHECKING:
  from utils.pg import PGUtils
  from utils.token import Token
  from utils.user import User

routes = web.RouteTableDef()
LOG = logging.getLogger(__name__)

VALID_SYNTAX_LANGUAGES = ["abap","actionscript-3","ada","apache","apex","apl","applescript","ara","asm","astro","awk","ballerina","bash","bat","batch","be","berry","bibtex","bicep","blade","c","c#","cadence","cdc","clarity","clj","clojure","cmake","cmd","cobol","codeql","coffee","console","cpp","crystal","cs","csharp","css","cue","d","dart","dax","diff","docker","dream-maker","elixir","elm","erb","erl","erlang","f#","fish","fs","fsharp","fsl","gherkin","git-commit","git-rebase","glsl","gnuplot","go","graphql","groovy","hack","haml","handlebars","haskell","hbs","hcl","hlsl","hs","html","http","imba","ini","jade","java","javascript","jinja-html","jison","js","json","json5","jsonc","jsonnet","jssm","jsx","julia","kotlin","latex","less","liquid","lisp","logo","lua","make","makefile","markdown","marko","matlab","md","mdx","mermaid","nginx","nim","nix","objc","objective-c","objective-cpp","ocaml","pascal","perl","perl6","php","plsql","postcss","powerquery","powershell","prisma","prolog","properties","proto","ps","ps1","pug","puppet","purescript","py","python","ql","r","raku","razor","rb","rel","riscv","rs","rst","ruby","rust","sas","sass","scala","scheme","scss","sh","shader","shaderlab","shell","shellscript","smalltalk","solidity","sparql","sql","ssh-config","stata","styl","stylus","svelte","swift","system-verilog","tasl","tcl","tex","toml","ts","tsx","turtle","twig","typescript","v","vb","verilog","vhdl","vim","viml","vimscript","vue","vue-html","wasm","wenyan","wgsl","xml","xsl","yaml","yml","zenscript","zsh","文言"]

# Get JSON of paste
@routes.get("/api/paste/get/{tail:.*}")
async def apiPasteGet(request: web.Request) -> web.Response:
  pasteID: str = request.path.removeprefix("/api/paste/get/")
  app: web.Application = request.app
  pg: PGUtils = app.pg

  paste: Paste = await pg.get_pastes_from_search(id=pasteID)

  if not paste:
    return web.Response(status=404)
  paste = paste[0]
  if paste.visibility == Visibility.PRIVATE.value:
    headers = request.headers
    auth = headers.get("Authorization","")
    if not auth:
      if "token" in request.cookies:
        auth = request.cookies["token"]
      else:
        return web.Response(status=401)
    token: Token = await pg.verify_token(auth)
    if token and token.creator == paste.creator and token.permissions.view_private:
      return web.Response(text=paste.json,content_type="application/json")
    else:
      return web.Response(status=401)
  else:
    user: User = await paste.get_creator(pg)
    paste.creator = user.name
    return web.Response(text=paste.json,content_type="application/json")

# Get raw paste data
@routes.get("/api/paste/raw/get/{tail:.*}")
async def api_paste_raw_get(request: web.Request) -> web.Response:
  pasteID: str = request.path.removeprefix("/api/paste/raw/get/")
  app: web.Application = request.app
  pg: PGUtils = app.pg

  paste: Paste = await pg.get_pastes_from_search(id=pasteID)

  if not paste:
    return web.Response(status=404)
  paste = paste[0]
  if paste.visibility == Visibility.PRIVATE.value:
    token = await pg.handle_auth(request,no_exist_ok=True)
    if token and token.creator == paste.creator and token.permissions.view_private:
      return web.Response(text=paste.text_content,content_type="text/plain")
    else:
      return web.Response(status=401)
  else:
    return web.Response(text=paste.text_content,content_type="text/plain")

@routes.get("/api/paste/search/")
async def api_paste_search(request: web.Request) -> web.Response:
  query = request.query
  
  app: web.Application = request.app
  pg: PGUtils = app.pg

  title=""
  creator=""

  try:
    limit=min(
      int(query.get("limit","50")),
      250
    )
    offset=int(query.get("offset","0"))
  except ValueError:
    return web.Response(status=400)

  if query.get("title"):title=query.get("title")
  if query.get("creator"):creator=query.get("creator")

  token = await pg.handle_auth(request,no_exist_ok=True)
  if type(token) is web.Response:
    return token

  if title: regex: re.Pattern = re.compile(title.lower())

  async def search(paste: Paste,limit=limit,offset=offset) -> bool:
    user = await pg.get_user(id=paste.creator)
    if not token:
      if title and creator:
        return regex.findall(paste.title.lower()) and user.name.lower() == creator.lower() and paste.visibility == Visibility.PUBLIC.value
      elif title:
        return regex.findall(paste.title.lower()) and paste.visibility == Visibility.PUBLIC.value
      elif creator:
        return user.name.lower() == creator.lower() and paste.visibility == Visibility.PUBLIC.value
    else:
      tokenCreator = token.owner
      if user == tokenCreator and token.permissions.view_private:
        if title and creator:
          return regex.findall(paste.title.lower()) and user.name.lower() == creator.lower()
        elif title:
          return regex.findall(paste.title.lower())
        elif creator:
          return user.name.lower() == creator.lower()
      else:
        if title and creator:
          return regex.findall(paste.title.lower()) and user.name.lower() == creator.lower() and paste.visibility == Visibility.PUBLIC.value
        elif title:
          return regex.findall(paste.title.lower()) and paste.visibility == Visibility.PUBLIC.value
        elif creator:
          return user.name.lower() == creator.lower() and paste.visibility == Visibility.PUBLIC.value
    return False

  pastes = await pg.get_pastes_from_function(search)
  # Convert list to json document
  j = []
  for paste in pastes:
    j.append({
      "id":paste.id,
      "creator":paste.creator,
      "visibility":paste.visibility,
      "title":paste.title,
    })
  return web.Response(text=json.dumps(j),content_type="application/json")

@routes.post("/api/paste/create/")
async def api_paste_create(request: web.Request) -> web.Response:
  app: web.Application = request.app
  pg: PGUtils = app.pg

  token = await pg.handle_auth(request)
  if type(token) is web.Response:
    return token
  
  data: dict = await request.json()
  if (not data.get("title")) or (not data.get("content")):
    return web.Response(status=400,text="missing body element")

  try:
    int(data.get("visibility"))
  except (TypeError, ValueError) as e:
    LOG.exception(e)
    return web.Response(status=400,text="invalid visibility")

  syntax: str = data.get("syntax","plaintext")
  if syntax not in VALID_SYNTAX_LANGUAGES:
    syntax = "plaintext"
  
  paste = Paste(
    id="",
    creator=token.owner.id,
    data=data.get("content"),
    visibility=data.get("visibility"),
    title=data.get("title"),
    syntax=syntax,
    tags=data.get("tags",""),
    folder=data.get("folder","")
  )

  new_paste,reason = await pg.create_new_paste(paste,token)

  if not new_paste:
    return web.Response(text=reason,status=400)

  return web.Response(status=200,text=new_paste.id)

@routes.post("/api/paste/create_query/")
async def api_paste_create(request: web.Request) -> web.Response:
  app: web.Application = request.app
  pg: PGUtils = app.pg

  # In this endpoint, instead of the post data being a json of the data,
  # the query is the "header" of the paste, and the post data is the contents.

  query = request.query


  int(query.get("visibility"))
  token = await pg.handle_auth(request)
  if type(token) is web.Response:
    return token
  
  data: dict = await request.text()
  if not query.get("title"):
    return web.Response(status=400,text="missing title")

  try:
    int(query.get("visibility"))
  except (TypeError, ValueError):
    return web.Response(status=400,text="invalid visibility")
  
  syntax = query.get("syntax", "plaintext")
  if syntax not in VALID_SYNTAX_LANGUAGES:
    syntax = "plaintext"
  paste = Paste(
    id="",
    creator=token.owner.id,
    data=data,
    visibility=int(query.get("visibility")),
    title=query.get("title"),
    syntax=syntax,
    tags=query.get("tags",""),
    folder=query.get("folder","")
  )

  new_paste,reason = await pg.create_new_paste(paste,token)

  if not new_paste:
    return web.Response(text=reason,status=400)

  return web.Response(status=200,text=new_paste.id)

@routes.post("/api/paste/edit/")
async def api_paste_edit(request: web.Request) -> web.Response:
  app: web.Application = request.app
  pg: PGUtils = app.pg

  token = await pg.handle_auth(request)
  if type(token) is web.Response:
    return token

  data: dict = await request.json()
  if not data.get("id",""):
    return web.Response(status=400,body="missing paste id")

  paste = await pg.get_pastes_from_search(id=data.get("id"))
  if not paste:
    return web.Response(status=404,body="paste not found")
  paste: Paste = paste[0]
  if paste.creator != token.owner.id or not token.permissions.edit_paste:
    return web.Response(status=401,body="invalid token")

  paste.title = data.get("title",paste.title)
  paste.data = (data.get("content",paste.data)).encode()
  paste.tags = data.get("tags",paste.tags)
  paste.syntax = data.get("syntax",paste.syntax)
  paste.folder = data.get("folder",paste.folder)

  try:
    paste.visibility = int(data.get("visibility",paste.visibility))
  except ValueError:
    pass

  out = await pg.edit_paste(paste,token)
  if not out:
    return web.Response(status=400)
  return web.Response(status=200,text=out.id)

@routes.post("/api/paste/delete/")
async def api_paste_delete(request: web.Request) -> web.Response:

  app: web.Application = request.app
  pg: PGUtils = app.pg

  token = await pg.handle_auth(request)
  if type(token) is web.Response:
    return token

  if not token.permissions.delete_paste:
    return web.Response(status=403)

  data = await request.json()
  if "id" not in data:
    return web.Response(status=400)

  pasteID = data["id"]

  paste = (await pg.get_pastes_from_search(id=pasteID))
  if not paste:
    return web.Response(status=404,body="paste not found")
  paste = paste[0]
  
  out = await pg.delete_paste(paste,token)

  if out:
    return web.Response(status=200)
  else:
    return web.Response(status=400)

def setup():
  return routes
