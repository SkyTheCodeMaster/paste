from __future__ import annotations

import json
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

# Get JSON of paste
@routes.get("/api/paste/get/{tail:.*}")
async def apiPasteGet(request: web.Request) -> web.Response:
  pasteID: str = request.path.removeprefix("/api/paste/get/")
  app: web.Application = request.app
  pg: PGUtils = app.pgUtils

  paste: Paste = await pg.getPastesFromSearch(id=pasteID)

  if not paste:
    return web.Response(status=404)
  paste = paste[0]
  if paste.visibility == Visibility.PRIVATE.value:
    headers = request.headers
    auth = headers.get("Authorization","")
    token: Token = await pg.verifyToken(auth)
    if token and token.creator == paste.creator and token.permissions.viewPrivate:
      return web.Response(text=paste.json,content_type="application/json")
    else:
      return web.Response(status=401)
  else:
    user: User = await paste.getCreator(pg)
    paste.creator = user.name
    return web.Response(text=paste.json,content_type="application/json")

# Get raw paste data
@routes.get("/api/paste/raw/get/{tail:.*}")
async def apiPasteRawGet(request: web.Request) -> web.Response:
  pasteID: str = request.path.removeprefix("/api/paste/raw/get/")
  app: web.Application = request.app
  pg: PGUtils = app.pgUtils

  paste: Paste = await pg.getPastesFromSearch(id=pasteID)

  if not paste:
    return web.Response(status=404)
  paste = paste[0]
  if paste.visibility == Visibility.PRIVATE.value:
    headers = request.headers
    auth = headers.get("Authorization","")
    token: Token = await pg.verifyToken(auth)
    if token and token.creator == paste.creator and token.permissions.viewPrivate:
      return web.Response(text=paste.textContent,content_type="text/plain")
    else:
      return web.Response(status=401)
  else:
    return web.Response(text=paste.textContent,content_type="text/plain")

@routes.get("/api/paste/search/")
async def apiPasteSearch(request: web.Request) -> web.Response:
  print("got here 1')")
  query = request.query
  
  app: web.Application = request.app
  pg: PGUtils = app.pgUtils

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

  headers = request.headers
  auth = headers.get("Authorization","")
  token = await pg.verifyToken(auth)
  if title: regex: re.Pattern = re.compile(title.lower())

  async def search(paste: Paste,limit=limit,offset=offset) -> bool:
    user = await pg.getUser(id=paste.creator)
    if not token:
      if title and creator:
        return regex.findall(paste.title.lower()) and user.name.lower() == creator.lower() and paste.visibility == Visibility.PUBLIC.value
      elif title:
        return regex.findall(paste.title.lower()) and paste.visibility == Visibility.PUBLIC.value
      elif creator:
        return user.name.lower() == creator.lower() and paste.visibility == Visibility.PUBLIC.value
    else:
      tokenCreator = token.owner
      if user == tokenCreator and token.permissions.viewPrivate:
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

  pastes = await pg.getPastesFromFunction(search)
  print(pastes)
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
async def apiPasteCreate(request: web.Request) -> web.Response:
  app: web.Application = request.app
  pgUtils: PGUtils = app.pgUtils
  headers = request.headers

  auth = headers.get("Authorization","")
  if not auth:
    return web.Response(status=401)
  
  data: dict = await request.json()
  if not data.get("title") or not data.get("content") or not data.get("visibility"):
    return web.Response(status=400,text="missing body element")

  try:
    int(data.get("visibility"))
  except ValueError:
    return web.Response(status=400,text="invalid visibility")

  token = await pgUtils.verifyToken(token=auth)
  
  paste = Paste(
    id="",
    creator=token.owner.id,
    data=data.get("content"),
    visibility=data.get("visibility"),
    title=data.get("title")
  )

  newPaste,reason = await pgUtils.createNewPaste(paste,token)

  if not newPaste:
    return web.Response(text=reason,status=400)

  return web.Response(status=200,text=newPaste.id)

@routes.post("/api/paste/edit/")
async def apiPasteEdit(request: web.Request) -> web.Response:
  app: web.Application = request.app
  pgUtils: PGUtils = app.pgUtils
  headers = request.headers

  auth = headers.get("Authorization","")
  if not auth:
    return web.Response(status=401)

  token = await pgUtils.verifyToken(headers.get("Authorization"))

  data: dict = await request.json()
  if not data.get("id",""):
    return web.Response(status=400,body="missing paste id")

  paste = await pgUtils.getPastesFromSearch(id=data.get("id"))
  print(paste)
  if not paste:
    return web.Response(status=404,body="paste not found")
  paste = paste[0]
  if paste.creator != token.owner.id:
    return web.Response(status=401,body="invalid token")

  paste.title = data.get("title",paste.title)
  paste.data = data.get("content",paste.data)
  try:
    paste.visibility = int(data.get("visibility",paste.visibility))
  except ValueError:
    pass

  out = await pgUtils.editPaste(paste,token)
  if not out:
    return web.Response(status=400)
  return web.Response(status=200,text=out.id)

@routes.delete("/api/paste/delete/{tail:.*}")
async def apiPasteDelete(request: web.Request) -> web.Response:
  pasteID: str = request.path.removeprefix("/api/paste/delete/")

  app: web.Application = request.app
  pgUtils: PGUtils = app.pgUtils
  headers = request.headers

  auth = headers.get("Authorization","")
  if not auth:
    return web.Response(status=401)

  token = await pgUtils.verifyToken(headers.get("Authorization"))

  paste = (await pgUtils.getPastesFromSearch(id=pasteID))
  if not paste:
    return web.Response(status=404,body="paste not found")
  paste = paste[0]
  
  out = await pgUtils.deletePaste(paste,token)

  if out:
    return web.Response(status=200)
  else:
    return web.Response(status=400)

def setup():
  return routes
