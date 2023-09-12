import datetime
import re
from typing import TYPE_CHECKING

from aiohttp import web

from utils.pg import PGUtils
from utils.ratelimit import limiter
from utils.token import Token
from utils.user import User
from utils.utils import ahash, gravatar, is_hash, resize_image_bytes

if TYPE_CHECKING:
  import aiohttp

routes = web.RouteTableDef()

DEFAULT_AVATAR_BYTES: bytes

with open("static/images/default_avatar.png","rb") as f:
  DEFAULT_AVATAR_BYTES = f.read()

email_regex = re.compile(r"(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])")

@routes.post("/api/login/")
async def api_login(request: web.Request) -> web.Response:
  """
  Login and return an existing session token or create a new one.

  `name` - username
  `password` - password, if doesnt match sha256 then it will be hashed
  `remember-me` - if true, expiry on the token will be set to 30 days

  returns 200 OK and token cookie, or 401.
  """
  app: web.Application = request.app
  pg: PGUtils = app.pg

  data: dict[str,str] = await request.json()
  if "name" not in data or "password" not in data:
    return web.Response(status=400)
  name = data["name"]
  passwd = data["password"]
  remember_me = data.get("rememberme",False)
  if not is_hash(passwd):
    passwd = await ahash(passwd,name)
  user_token = await pg.verify_token(passwd)
  if not user_token:
    return web.Response(status=401)
  async with app.pool.acquire() as conn:
    record = await conn.fetchrow("SELECT Token FROM Users WHERE Id=$1;",user_token.owner.id)
    token = record["token"]
    response = web.Response(status=200)
    max_age = 2592000 if remember_me else -1
    response.set_cookie("token",token,max_age=max_age,samesite="Lax")
    return response

@routes.post("/api/internal/user/create/")
async def api_internal_user_create(request: web.Request) -> web.Response:
  """
  Create a user.

  Required post data:
  `name` - Name of user
  `password` - Password of user, if doesnt match sha256 then it will be hashed
  `email` email of user
  """
  app: web.Application = request.app
  pg: PGUtils = app.pg
  data = await request.json()
  if "name" not in data:
    return web.Response(status=400,body="name parameter is missing")
  if "email" not in data:
    return web.Response(status=400,body="email parameter is missing")
  if "password" not in data:
    return web.Response(status=400,body="password parameter is missing")
  name = data["name"]
  email = data["email"]
  passwd = data["password"]
  remember_me = data.get("rememberme",False)
  if not email_regex.match(email):
    return web.Response(status=400,body="email invalid")

  if not is_hash(passwd):
    passwd = await ahash(passwd,name)
  user = User(name=name,password=passwd,email=email)
  new_id = await pg.create_new_user(user)
  user.id = new_id
  if type(new_id) is int:
    new_token = await pg.generate_new_user_token(user)
    response = web.Response(status=200,body=str(new_id))
    max_age = 2592000 if remember_me else -1
    response.set_cookie("token",new_token,max_age=max_age,samesite="Lax")
    return response
  else:
    return web.Response(status=400,body="username already registered")

@routes.post("/api/internal/user/exists/")
async def api_internal_user_exists(request: web.Request) -> web.Response:
  "Checks if a user exists. Only required post data is `name`."
  app: web.Application = request.app
  data = await request.json()
  if "name" not in data:
    return web.Response(status=400,body="name parameter is missing")
  async with app.pool.acquire() as conn:
    exists = (await conn.fetchrow("SELECT EXISTS ( SELECT 1 FROM Users WHERE Username ILIKE $1 );",data["name"]))["exists"]
    if exists:
      return web.Response(status=200,body="true")
    else:
      return web.Response(status=200,body="false")
    
@routes.get("/api/internal/user/avatar/")
async def api_internal_user_avatar(request: web.Request) -> web.Response:
  app: web.Application = request.app
  pg: PGUtils = app.pg
  session: aiohttp.ClientSession = app.cs

  target_user = None
  token = await pg.handle_auth(request)
  if "user" in request.query:
    target_user = await pg.get_user(name=request.query["user"])
  elif type(token) is Token:
    target_user = token.owner
  else:
    return web.Response(status=400,body="either pass user in query or pass auth token")
  
  time = lambda: int(datetime.datetime.now(datetime.timezone.utc).timestamp())
  
  async with app.pool.acquire() as conn:
    exists = (await conn.fetchrow("SELECT EXISTS ( SELECT 1 FROM AvatarCache WHERE UserID=$1 );",target_user.id))["exists"]
    if exists:
      record = await conn.fetchrow("SELECT * FROM AvatarCache WHERE UserID=$1;",target_user.id)
      if record["refresh"] > time():
        # cache valid
        return web.Response(body=record["avatar"], content_type="image/png")
  
    image_bytes: bytes = None

    match (target_user.avatar_type):
      case 0:
        # Default user avatar.
        image_bytes = DEFAULT_AVATAR_BYTES
      case 1:
        # Gravatar
        url = await gravatar(target_user.email)
        async with session.get(url) as resp:
          image_bytes = await resp.read()
      case 2:
        # URL
        url = target_user.avatar_url
        if url == "INTERNAL_AVATAR":
          record = await conn.fetchrow("SELECT Avatar FROM Avatars WHERE ID=$1;", target_user.id)
          image_bytes = record["avatar"]
        else:
          async with session.get(url) as resp:
            image_bytes = await resp.read()
  
    await conn.execute("""
      INSERT INTO AvatarCache
        (UserID, Avatar, Refresh)
      VALUES
        ($1, $2, $3)
      ON CONFLICT (UserID)
      DO
        UPDATE SET 
          Avatar = $2,
          Refresh = $3;
    """, target_user.id, image_bytes, time()+60*60*24*7) # Add a week to the cache refresh time.

  return web.Response(body=image_bytes, content_type="image/png")

@routes.post("/api/internal/user/setavatar/")
async def api_internal_user_setavatar(request: web.Request) -> web.Response:
  app: web.Application = request.app
  pg: PGUtils = app.pg

  token = await pg.handle_auth(request, strict_password=True)
  if type(token) is web.Response:
    return token
  
  data = await request.json()
  if not "type" in data:
    return web.Response(body="missing type in post data",status=400)
  
  if data["type"] == 2 and (not "url" in data or not "bytes" in data):
    return web.Response(body="missing url/bytes in post data",status=400)
  
  if data["type"] == 2 and (not "url" in data and not "bytes" in data):
    return web.Response(body="url/bytes both in post data",status=400)

  async with app.pool.acquire() as conn:
    if data["type"] in [0,1]:
      await conn.execute("UPDATE Users SET AvatarType = $2 WHERE ID = $1;", token.owner.id, data["type"])
    elif data["type"] == 2:
      if "url" in data:
        await conn.execute("UPDATE Users SET AvatarType = 2, AvatarURL = $2 WHERE ID = $1;", token.owner.id, data["url"])
      elif "bytes" in data:
        resized_bytes = await resize_image_bytes(data["bytes"], (80,80))
        await conn.execute("UPDATE Users SET AvatarType = 2, AvatarURL = 'INTERNAL_AVATAR' WHERE ID = $1;", token.owner.id)
        await conn.execute("""
          INSERT INTO Avatars
            (ID, Avatar)
          VALUES
            ($1, $2)
          ON CONFLICT (ID)
          DO
            UPDATE SET 
              Avatar = $2;
    """, token.owner.id, resized_bytes)
    await conn.execute("""
      INSERT INTO AvatarCache
        (UserID, Refresh)
      VALUES
        ($1, 0)
      ON CONFLICT (UserID)
      DO
        UPDATE SET 
          Refresh = 0;
    """)
    return web.Response(status=200)

@routes.post("/api/internal/user/edit/")
async def api_internal_user_edit(request: web.Request) -> web.Response:
  """
  Edit a user.
  Post data (all optional):
  `name` - New name of the user
  `newpassword` - New password of the user, must be pre hashed. If not hashed, 400 is returned
  `email` - New email of user, must be valid or 400 will be returned.
  
  Required header is the Authorization header of the user's hashed password.

  Returns 400 if no parameters are passed, or if authorization is not passed
  Returns 401 if authorization is incorrect
  Returns 200 on success
  """
  app: web.Application = request.app
  pg: PGUtils = app.pg

  token = await pg.handle_auth(request, strict_password=True)
  if type(token) is web.Response:
    return token

  data = await request.json()
  old_user = token.owner.clone()
  new_user = User(
    name="name" in data and data["name"] or old_user.name,
    email="email" in data and data["email"] or old_user.email,
    password="newpassword" in data and data["newpassword"] or old_user.password,
    id=old_user.id,
    token=old_user.token
  )

  await pg.update_user(new_user)

  new_token = await pg.generate_new_user_token(new_user)
  response = web.Response(status=200)
  response.set_cookie("token",new_token)
  return response

@routes.get("/api/internal/user/data/")
async def api_internal_user_data(request: web.Request) -> web.Response:
  """
  Gets all of a user's data and collects it into a single json package.
  Zips it up, and returns the file.

  Authorization required (User's hashed password)
  """
  app: web.Application = request.app
  pg: PGUtils = app.pg

  token = await pg.handle_auth(request,strict_password=True)
  if type(token) is web.Response:
    return token

  path = await pg.create_datadump(token.owner)
  return web.FileResponse(path)

@routes.delete("/api/internal/user/delete")
async def api_internal_user_delete(request: web.Request) -> web.Response:
  """
  Deletes a user account. This action is irreversible!

  Requires Authentication header.
  `delete-pastes` header determines if all pastes should be deleted. Default to `true`.

  Return 200 if account was deleted, and a data dump.
  """
  app: web.Application = request.app
  pg: PGUtils = app.pg
  headers = request.headers

  token = await pg.handle_auth(request,strict_password=True)
  if type(token) is web.Response:
    return token

  path = await pg.create_datadump(token.owner)
  await pg.delete_user(token.owner, delete_pastes=headers.get("delete-pastes",True))
  return web.FileResponse(path)

@routes.post("/api/internal/token/create/")
async def api_internal_token_create(request: web.Request) -> web.Response:
  """
  Create an API token
  POST data:
  `name`: str Name of the API token
  `perms`: int Bitarray of the API token

  Authorization of user's hashword is required.

  Returns 200 and token ID.
  Returns 401 if no authorization.
  Returns 400 if bitarray is bad (extra bits, invalid bits, etc)
  """
  app: web.Application = request.app
  pg: PGUtils = app.pg

  user_token = await pg.handle_auth(request,strict_password=True)
  if type(user_token) is web.Response:
    return user_token

  data = await request.json()
  if not "name" in data or not "perms" in data or data["perms"] > 255:
    return web.Response(status=400)

  # Build the token object
  token = Token(name=data["name"],owner=user_token.owner,permissions=data["perms"],id="")
  # Add it to the database
  new_id = await pg.create_token(token)
  return web.Response(body=new_id)

@routes.post("/api/internal/token/edit/")
async def api_internal_token_edit(request: web.Request) -> web.Response:
  """
  Modify a token
  POST data:
  `id`: str ID of the api token.
  `name`: str New name of the API token
  `perms`: int New bitarry of the API token.

  Authorization of the user's hashword is required.

  Return 200 if successful
  Returns 401 if bad authorization.
  Returns 400 if bitarray is bad.
  """
  app: web.Application = request.app
  pg: PGUtils = app.pg

  user_token = await pg.handle_auth(request,strict_password=True)
  if type(user_token) is web.Response:
    return user_token

  data = await request.json()
  if not "id" in data:
    return web.Response(status=400)
  if "perms" in data and data["perms"] > 255:
    return web.Response(status=400)

  token = await pg.verify_token(data["id"])
  await pg.edit_token(token,
    perms="perms" in data and data["perms"] or None,
    name ="name"  in data and data["name"]  or None,
  )
  return web.Response(status=200)

@routes.delete("/api/internal/token/delete/")
async def api_internal_token_delete(request: web.Request) -> web.Response:
  """
  Delete a token.

  Authorization header required.

  Body only requires `id` of the token to be deleted.
  """
  app: web.Application = request.app
  pg: PGUtils = app.pg

  user_token = await pg.handle_auth(request,strict_password=True)
  if type(user_token) is web.Response:
    return user_token

  data = await request.json()
  if not "id" in data:
    return web.Response(status=400)
  token = await pg.verify_token(data["id"])

  if token.owner != user_token.owner:
    return web.Response(status=400)

  if await pg.delete_token(token):
    return web.Response(status=200)
  else:
    return web.Response(status=500)

def setup() -> web.RouteTableDef:
  return routes