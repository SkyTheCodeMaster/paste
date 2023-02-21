from aiohttp import web
from typing import TYPE_CHECKING

from utils.ratelimit import limiter

routes = web.RouteTableDef()

@routes.post("/api/internal/user/create/")
@limiter.limit("1/30minutes")
async def apiInternalUserCreate(request: web.Request) -> web.Response:
  """
  Create a user.

  Required post data:
  `name` - Name of user
  `password` - Password of user, if doesnt match sha256 then it will be hashed
  `email` email of user
  """
  pass

@routes.post("/api/internal/user/edit/")
@limiter.limit("1/15minutes")
async def apiInternalUserEdit(request: web.Request) -> web.Response:
  """
  Edit a user.
  Post data (all optional):
  `name` - New name of the user
  `password` - New password of the user, must be pre hashed. If not hashed, 400 is returned
  `email` - New email of user, must be valid or 400 will be returned.
  
  Required header is the Authorization header of the user's hashed password.

  Returns 400 if no parameters are passed, or if authorization is not passed
  Returns 401 if authorization is incorrect
  Returns 200 on success
  """
  pass

@routes.get("/api/internal/user/datadump")
@limiter.limit("1/day")
async def apiInternalUserDatadump(request: web.Request) -> web.Response:
  """
  Gets all of a user's data and collects it into a single json package.
  Zips it up, and returns the file.

  Authorization required (User's hashed password)
  """
  pass

@routes.delete("/api/internal/user/delete/")
@limiter.limit("1/5minutes")
async def apiInternalUserDelete(request: web.Request) -> web.Response:
  """
  Deletes a user account. This action is irreversible!

  Return 200 if account was deleted, and a data dump.
  """
  pass

@routes.post("/api/internal/token/create/")
@limiter.limit("1/15seconds")
async def apiInternalTokenCreate(request: web.Request) -> web.Response:
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
  pass

@routes.post("/api/internal/token/edit/")
async def apiInternalTokenEdit(request: web.Request) -> web.Response:
  """
  Modify a token
  POST data:
  `name`: str Name of the API token (this can not be changed ever)
  `perms`: New bitarry of the API token.

  Authorization of the user's hashword is required.

  Return 200 if successful
  Returns 401 if bad authorization.
  Returns 400 if bitarray is bad.
  """
  pass

@routes.delete("/api/internal/token/delete/")
@limiter.limit("1/15seconds")
async def apiInternalTokenDelete(request: web.Request) -> web.Response:
  pass

def setup() -> web.RouteTableDef:
  return routes