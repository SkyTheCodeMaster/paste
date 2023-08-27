# Postgresql utils

from __future__ import annotations

import datetime
import json
import random
import logging
import string
from inspect import isawaitable
from typing import TYPE_CHECKING

import aiofiles
from aiofiles import os as aos
import aioshutil
import asyncpg

from utils.paste import Paste
from utils.token import Token
from utils.user import User
from utils.utils import hash
from aiohttp import web

if TYPE_CHECKING:
  from typing import Union

LOG = logging.getLogger(__name__)

with open("config.json") as f:
  contents = f.read()
  config = json.loads(contents)
  PASTE_ID_LENGTH   = config["paste.id_length"]
  TOKEN_ID_LENGTH   = config["token.id_length"]
  USER_TOKEN_LENGTH = config["user.token_length"]
  USERNAME_MIN_LENGTH = config["user.name_min"]
  USERNAME_MAX_LENGTH = config["user.name_max"]

class PGUtils:
  def __init__(self, pool: asyncpg.Pool = None):
    self.pool = pool

  def _time(self) -> int:
    return int(datetime.datetime.now(datetime.timezone.utc).timestamp())

  async def handle_auth(self, request: web.Request, *, strict_password: bool = False, no_exist_ok: bool = False) -> Union[web.Response,Token,False]:
    if "Authorization" in request.headers:
      token = await self.verify_token(request.headers["Authorization"])
      if strict_password and type(token) is Token and token.name == "PASSWORD":
        return token
      elif strict_password:
        return web.Response(status=401)
      else:
        return token
    if "token" in request.cookies:
      token = await self.verify_token(request.cookies["token"])
      if strict_password and type(token) is Token and token.name == "PASSWORD":
        return token
      elif strict_password:
        return web.Response(status=401)
      else:
        return token
    if not no_exist_ok:
      return web.Response(status=401)
    else:
      return False

  async def get_user(self,*,name: str = None, email: str = None, id: int = None) -> User:
    "Get a user from either username, email, or the ID, and return a User object."
    async with self.pool.acquire() as conn:
      if name:
        record = await conn.fetchrow("SELECT * FROM Users WHERE Username LIKE $1", name)
      elif email:
        record = await conn.fetchrow("SELECT * FROM Users WHERE Email LIKE $1", email)
      elif id:
        record = await conn.fetchrow("SELECT * FROM Users WHERE Id = $1", id)

      return User.from_record(record)

  async def create_new_user(self,user: User) -> int:
    "Create a new user, and return the ID of the user."
    if not USERNAME_MIN_LENGTH <= len(user.name) <= USERNAME_MAX_LENGTH:
      return False
    async with self.pool.acquire() as conn:
      exists = await conn.fetchrow("SELECT EXISTS ( SELECT 1 FROM Users WHERE Username ILIKE $1);",user.name)
      if not exists["exists"]:
        await conn.execute("INSERT INTO Users (Username, Password, Email) VALUES ($1, $2, $3)", user.name, user.password, user.email)
        user = await self.get_user(name=user.name)
        return user.id
      else:
        return False
  
  async def update_user(self,user: User) -> bool:
    "Update attributes of a user."
    async with self.pool.acquire() as conn:
      record = await conn.execute("UPDATE Users SET name=$2, email = $3, password=$4 WHERE id=$1",user.id,user.name,user.email,user.password)
      return bool(record["update"])

  async def get_pastes_from_creator(self,*,creator: int) -> list[Paste]:
    "Get all of the pastes registered to a user"
    async with self.pool.acquire() as conn:
      records = await conn.fetch("SELECT * FROM Pastes WHERE Creator = $1", creator)
      out: list[Paste] = []
      for record in records:
        out.append(Paste.from_record(record))
      return out

  async def get_pastes_from_search(self,*,creator: Union[int,str,User] = None, title: str = None, id: str = None) -> list[Paste]:
    "Get a paste from either the creator id, or title, or the id, and return a Paste object."
    async with self.pool.acquire() as conn:
      if creator:
        if type(creator) is int:
          creator = creator
        elif type(creator) is str:
          creator = (await self.get_user(name=creator)).id
        elif type(creator) is User:
          creator = creator.id

        records = await conn.fetch("SELECT * FROM Pastes WHERE Creator ", creator)
      elif title:
        records = await conn.fetch("SELECT * FROM Pastes WHERE Email LIKE %$1%", title)
      elif id:
        records = await conn.fetch("SELECT * FROM Pastes WHERE Id = $1", id)

      out = [Paste.from_record(record) for record in records]
      return out

  async def get_pastes_from_lambda(self,lambd: function,*,limit:int=50,offset:int=0) -> list[Paste]:
    """Use the lambda to return a list of pastes. Lambda's argument is a Paste object. Pastes `creator` attribute is a User object
    The limit function returns only a max of the limit, and offset is pagination"""
    # Get all of the pastes
    async with self.pool.acquire() as conn:
      records = await conn.fetch("SELECT * FROM Pastes LIMIT $1 OFFSET $2",limit,offset*limit)
      # Now turn it into a list of pastes
      print(records)
      pastes = [Paste.from_record(record) for record in records]

      # Now loop over it and check it against the lambda
      out = []
      for paste in pastes:
        if isawaitable(lambd):
          print(await lambd())
          if await lambd(paste):
            out.append(paste)
        else:
          print(lambd())
          if lambd(paste):
            out.append(paste)
      return out

  async def verify_token(self, token: Union[Token,str]) -> Union[Token,bool]:
    "Verifies a token and returns the Token object, or False if the token does not exist."
    if type(token) is Token:
      return token
    async with self.pool.acquire() as conn:
      record = await conn.fetchrow("SELECT * FROM APITokens WHERE id = $1",token)
      if record:
        user: User = await self.get_user(id=record["creator"])
        token = Token(
          name=record["title"],
          owner=user,
          permissions=record["perms"],
          id=record["id"],
        )
        return token
      record = await conn.fetchrow("SELECT * FROM Users WHERE Password = $1 OR Token = $1;",token)
      if record:
        user = User.from_record(record)
        token = Token(
          name="PASSWORD",
          owner=user,
          permissions=255,
          id=token
        )
        return token

  async def _generate_paste_id(self) -> str:
    "Generate an ID, while making sure it does not exist in the database already."
    pool: str = string.ascii_letters+string.digits
    pasteID = "".join(random.choices(pool,k=PASTE_ID_LENGTH))
    async with self.pool.acquire() as conn:
      record = await conn.fetchrow("SELECT EXISTS (SELECT 1 FROM Pastes WHERE Id = $1);",pasteID)
      if record["exists"]:
        return await self._generate_paste_id()
      else:
        return pasteID

  async def _generate_token_id(self) -> str:
    "Generate an ID, while making sure it does not exist in the database already."
    pool: str = string.ascii_letters+string.digits
    tokenID = "".join(random.choices(pool,k=TOKEN_ID_LENGTH))
    async with self.pool.acquire() as conn:
      record = await conn.fetchrow("SELECT EXISTS (SELECT 1 FROM APITokens WHERE Id = $1);",tokenID)
      if record["exists"]:
        return await self._generate_token_id()
      else:
        return tokenID

  async def _generate_user_token_id(self) -> str:
    "Generate an ID, while making sure it does not exist in the database already."
    pool: str = string.ascii_letters+string.digits
    tokenID = "".join(random.choices(pool,k=TOKEN_ID_LENGTH))
    async with self.pool.acquire() as conn:
      record = await conn.fetchrow("SELECT EXISTS (SELECT 1 FROM Users WHERE Token = $1);",tokenID)
      if record["exists"]:
        return await self._generate_user_token_id()
      else:
        return tokenID

  async def create_new_paste(self, paste: Paste, token: Union[Token,str]) -> Union[Paste,bool]:
    "Create a new paste, returning the paste object with the ID field set. The ID field will be overwritten with the new one. Token is used for determining who owns the paste, and if this token can create pastes."
    if type(token) is str:
      token = await self.verify_token(token)
      if not token: return False,"verify token failed/not passed"
    if not token.permissions.create_paste:
      return False,"missing create intent"
    
    pasteID = await self._generate_paste_id()
    if type(paste.data) is not bytes:
      paste.data = paste.data.encode()
    async with self.pool.acquire() as conn:
      await conn.execute("""
        INSERT INTO 
          Pastes
            (id,creator,content,visibility,title,created,modified,syntax) 
        VALUES
          ($1, $2, $3, $4, $5, $6, $7, $8);
        """,
        pasteID,
        token.owner.id,
        paste.data,
        paste.visibility,
        paste.title,
        self._time(),
        self._time(),
        paste.syntax
      )
      return (await self.get_pastes_from_search(id=pasteID))[0],""

  async def edit_paste(self, paste:Paste, token: Union[Token,str]) -> Union[Paste,bool]:
    "Edit a paste, returns the new paste object."
    if type(token) is str:
      token = await self.verify_token(token)
      if not token: return False
    if not token.permissions.edit_paste:
      return False

    nPaste = await self.get_pastes_from_search(id=paste.id)
    if not nPaste: return False
    nPaste = nPaste[0]

    if token.owner.id != nPaste.creator:
      return False
    async with self.pool.acquire() as conn:
      await conn.execute("UPDATE Pastes SET Content = $1, Title = $2, Visibility = $3, Modified=$5, Syntax = $6 WHERE id = $4",paste.data,paste.title,paste.visibility,nPaste.id,self._time(),paste.syntax)
      return (await self.get_pastes_from_search(id=nPaste.id))[0]

  async def delete_paste(self,paste: Paste, token: Token) -> bool:
    "Delete a paste, returning a boolean"
    if type(token) is str:
      token = await self.verify_token(token)
      if not token: return False
    if not token.permissions.delete_paste:
      return False

    nPaste = await self.get_pastes_from_search(id=paste.id)
    if not nPaste: return False
    nPaste = nPaste[0]

    if token.owner.id != nPaste.creator:
      return False

    async with self.pool.acquire() as conn:
      await conn.execute("DELETE FROM Pastes WHERE id = $1",nPaste.id)
      return True
    
  async def create_datadump(self, user: User) -> str:
    "Create a datadump in `/tmp/` and return the filepath of the zip."
    # Get the pastes
    pastes = await self.get_pastes_from_creator(creator=user.id)
    # Create a tmp directory
    try:
      await aioshutil.rmtree(f"/tmp/{user.id}/")
    except: pass
    await aos.makedirs(f"/tmp/{user.id}/",exist_ok=True)
    for paste in pastes:
      async with aiofiles.open(f"/tmp/{user.id}/{paste.id} ({paste.title}).txt","w") as f:
        await f.write(paste.text_content)
    await aioshutil.make_archive(f"/tmp/{user.id}","zip",f"/tmp/{user.id}/")
    return f"/tmp/{user.id}.zip"

  async def delete_user(self, user: User, *, delete_pastes: bool = True) -> bool:
    user_id = user.id
    async with self.pool.acquire() as conn:
      try:
        if delete_pastes:
          await conn.execute("DELETE FROM Pastes WHERE Creator = $1;",user_id)
        await conn.execute("DELETE FROM APITokens WHERE Creator = $1;",user_id)
        await conn.execute("DELETE FROM Users WHERE id = $1;",user_id)
      except:
        return False
    return True

  async def create_token(self, token: Token) -> Union[Token,False]:
    "This takens a token object with no ID and inserts it into the database, generating an ID as necessary."
    async with self.pool.acquire() as conn:
      try:
        id = await self._generate_token_id()
        await conn.execute("INSERT INTO APITokens (Creator, Title, Perms, Id) VALUES ($1,$2,$3,$4);",token.owner.id,token.name,token.perms,id)
        token.id = id
        return Token
      except:
        return False

  async def edit_token(self, token: Token, *, name: str = None, perms: int = None) -> Union[Token,False]:
    async with self.pool.acquire() as conn:
      try:
        await conn.execute("UPDATE APITokens SET name=$3, perms=$4 WHERE id=$1 AND Creator=$2;",
        token.id,token.owner.id,
        name if name is not None else token.name,
        perms if perms is not None else token.perms
        )
        return await self.verify_token(token.id)
      except:
        return False

  async def delete_token(self, token: Token) -> bool:
    async with self.pool.acquire() as conn:
      try:
        await conn.execute("DELETE FROM APITokens WHERE Creator=$1 AND id=$2;",token.owner.id,token.id)
        return True
      except:
        return False

  async def generate_new_user_token(self, user: Union[int,User]) -> str:
    if type(user) is User:
      user = user.id
    async with self.pool.acquire() as conn:
      new_token: str = await self._generate_user_token_id()
      await conn.execute("UPDATE Users SET Token = $2 WHERE Id = $1",user,new_token)
      return new_token