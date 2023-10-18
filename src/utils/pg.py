# Postgresql utils

from __future__ import annotations

import datetime
import tomllib
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
from utils.user import User, DeletedUser
from utils.utils import ahash
from aiohttp import web

if TYPE_CHECKING:
  from typing import Union, Any, Coroutine

LOG = logging.getLogger(__name__)

with open("config.toml") as f:
  contents = f.read()
  config = tomllib.loads(contents)
  PASTE_ID_LENGTH   = config["paste"]["id_length"]
  TOKEN_ID_LENGTH   = config["token"]["id_length"]
  USER_TOKEN_LENGTH=config["user"]["token_length"]
  USERNAME_MIN_LENGTH = config["user"]["name_min"]
  USERNAME_MAX_LENGTH = config["user"]["name_max"]

class PGUtils:
  def __init__(self, pool: asyncpg.Pool = None):
    self.pool = pool

  def _time(self) -> int:
    return int(datetime.datetime.now(datetime.timezone.utc).timestamp())

  async def handle_auth(self, request: web.Request, *, strict_password: bool = False, no_exist_ok: bool = False, secure: bool = False) -> Union[web.Response,Token,False]:
    if "Authorization" in request.headers:
      token = await self.verify_token(request.headers["Authorization"])
      if strict_password and type(token) is Token and token.name in ["INSECUREPASSWORD","SECUREPASSWORD"]:
        if secure and token.name == "SECUREPASSWORD":
          return token
        elif secure: 
          return web.Response(status=401)
        else:
          return token
      elif strict_password:
        return web.Response(status=401)
      else:
        return token
    if "securetoken" in request.cookies:
      token = await self.verify_token(request.cookies["securetoken"])
      if strict_password and type(token) is Token and token.secure:
        return token
    if "token" in request.cookies:
      token = await self.verify_token(request.cookies["token"])
      if strict_password and type(token) is Token and token.name in ["INSECUREPASSWORD","SECUREPASSWORD"]:
        if secure and token.name == "SECUREPASSWORD":
          return token
        elif secure: 
          return web.Response(status=401)
        else:
          return token
      elif strict_password:
        return web.Response(status=401)
      else:
        return token
    if not no_exist_ok:
      return web.Response(status=401)
    else:
      return False

  async def get_user(self,*,name: str = None, email: str = None, id: int = None) -> User|None:
    "Get a user from either username, email, or the ID, and return a User object."
    async with self.pool.acquire() as conn:
      if name:
        record = await conn.fetchrow("SELECT * FROM Users WHERE Username ILIKE $1", name)
      elif email:
        record = await conn.fetchrow("SELECT * FROM Users WHERE Email ILIKE $1", email)
      elif id:
        record = await conn.fetchrow("SELECT * FROM Users WHERE Id = $1", id)
      if record:
        return User.from_record(record)
      else:
        return type(id) is int and DeletedUser() or None

  async def create_new_user(self,user: User) -> int:
    "Create a new user, and return the ID of the user."
    if not USERNAME_MIN_LENGTH <= len(user.name) <= USERNAME_MAX_LENGTH:
      return False
    async with self.pool.acquire() as conn:
      exists = await conn.fetchrow("SELECT EXISTS ( SELECT 1 FROM Users WHERE Username ILIKE $1);",user.name)
      if not exists["exists"]:
        await conn.execute("INSERT INTO Users (Username, Password, Email, AvatarType, JoinDate, RememberMe) VALUES ($1, $2, $3, 0, $4, $5);", user.name, user.password, user.email, self._time(), user.remember_me)
        user = await self.get_user(name=user.name)
        return user.id
      else:
        return False
  
  async def update_user(self,user: User) -> bool:
    "Update attributes of a user."
    async with self.pool.acquire() as conn:
      original_user = await self.get_user(id = user.id)
      if original_user.password != user.password:
        await self.generate_new_user_token(original_user, True)
      record = await conn.execute("UPDATE Users SET username=$2, email = $3, password=$4 WHERE id=$1",user.id,user.name,user.email,user.password)
      return record == "UPDATE 1" # If we've updated more than one, yikes bro

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
      pastes = [Paste.from_record(record) for record in records]

      # Now loop over it and check it against the lambda
      out = []
      for paste in pastes:
        if isawaitable(lambd):
          if await lambd(paste):
            out.append(paste)
        else:
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
          ident=record["ident"]
        )
        return token
      record = await conn.fetchrow("SELECT * FROM Users WHERE Password = $1 OR SecureToken = $1 OR InsecureToken = $1;",token)
      if record:
        if record["password"] == token or record["securetoken"] == token:
          user = User.from_record(record)
          token = Token(
            name="SECUREPASSWORD",
            owner=user,
            permissions=255,
            id=token,
            ident="NONE"
          )
          return token
        if record["insecuretoken"] == token:
          user = User.from_record(record)
          token = Token(
            name="INSECUREPASSWORD",
            owner=user,
            permissions=255,
            id=token,
            ident="NONE"
          )
          return token
    return False

  async def _generate_paste_id(self, *, conn: asyncpg.Connection = None) -> str:
    "Generate an ID, while making sure it does not exist in the database already."
    pool: str = string.ascii_letters+string.digits
    pasteID = "".join(random.choices(pool,k=PASTE_ID_LENGTH))
    if conn is None:
      conn = await self.pool.acquire()
    record = await conn.fetchrow("SELECT EXISTS (SELECT 1 FROM Pastes WHERE Id = $1);",pasteID)
    if record["exists"]:
      return await self._generate_paste_id()
    else:
      await self.pool.release(conn)
      return pasteID

  async def _generate_token_id(self, *, conn: asyncpg.Connection = None) -> str:
    "Generate an ID, while making sure it does not exist in the database already."
    pool: str = string.ascii_letters+string.digits
    tokenID = "".join(random.choices(pool,k=TOKEN_ID_LENGTH))
    if conn is None:
      conn = await self.pool.acquire()
    record = await conn.fetchrow("SELECT EXISTS (SELECT 1 FROM APITokens WHERE Id = $1 OR Ident = $1);",tokenID)
    if record["exists"]:
      return await self._generate_token_id(conn=conn)
    else:
      await self.pool.release(conn)
      return tokenID

  async def _generate_user_token_id(self, secure: bool, *, conn: asyncpg.Connection = None) -> str:
    "Generate an ID, while making sure it does not exist in the database already."
    pool: str = string.ascii_letters+string.digits
    tokenID = "".join(random.choices(pool,k=TOKEN_ID_LENGTH))
    if conn is None:
      conn = await self.pool.acquire()
    if secure:
      record = await conn.fetchrow("SELECT EXISTS (SELECT 1 FROM Users WHERE SecureToken = $1);",tokenID)
    else:
      record = await conn.fetchrow("SELECT EXISTS (SELECT 1 FROM Users WHERE InsecureToken = $1);",tokenID)
    if record["exists"]:
      return await self._generate_user_token_id(conn=conn)
    else:
      await self.pool.release(conn)
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
            (id,creator,content,visibility,title,created,modified,syntax,tags) 
        VALUES
          ($1, $2, $3, $4, $5, $6, $7, $8, $9);
        """,
        pasteID,
        token.owner.id,
        paste.data,
        paste.visibility,
        paste.title,
        self._time(),
        self._time(),
        paste.syntax,
        paste.tags
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
      await conn.execute("""UPDATE 
                              Pastes 
                            SET 
                              Content = $1, 
                              Title = $2, 
                              Visibility = $3, 
                              Modified=$5, 
                              Syntax = $6,
                              tags = $7
                            WHERE 
                              id = $4""",
                         paste.data,
                         paste.title,
                         paste.visibility,
                         nPaste.id,
                         self._time(),
                         paste.syntax,
                         paste.tags
      )
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
      await aioshutil.rmtree(f"/tmp/paste_server/{user.id}/")
    except: pass
    await aos.makedirs(f"/tmp/paste_server/{user.id}/",exist_ok=True)
    for paste in pastes:
      async with aiofiles.open(f"/tmp/paste_server/{user.id}/{paste.title} ({paste.id}).txt","w") as f:
        await f.write(paste.text_content)
    await aioshutil.make_archive(f"/tmp/paste_server/{user.id}","zip",f"/tmp/paste_server/{user.id}/")
    return f"/tmp/paste_server/{user.id}.zip"
  
  async def get_token(self, user: User, token_name: str) -> Token:
    user_id = user.id
    async with self.pool.acquire() as conn:
      record = await conn.fetchrow("SELECT * FROM APITokens WHERE Creator = $1 AND (Title = $2 OR Ident = $2);", user_id, token_name)
      if not record: return False
      return Token.from_record(record,user)

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
        ident = await self._generate_token_id()
        await conn.execute("INSERT INTO APITokens (Creator, Title, Perms, Id, Ident) VALUES ($1,$2,$3,$4,$5);",token.owner.id,token.name,token.perms,id,ident)
        token.id = id
        token.ident = ident
        return token
      except:
        LOG.exception("Error in create_token")
        return False

  async def edit_token(self, token: Token, *, name: str = None, perms: int = None) -> Union[Token,False]:
    async with self.pool.acquire() as conn:
      try:
        await conn.execute("UPDATE APITokens SET title=$3, perms=$4 WHERE id=$1 AND Creator=$2;",
        token.id,token.owner.id,
        name if name is not None else token.name,
        perms if perms is not None else token.perms
        )
        return await self.verify_token(token.id)
      except:
        LOG.exception("Error in edit_token")
        return False

  async def delete_token(self, token: Token) -> bool:
    async with self.pool.acquire() as conn:
      try:
        await conn.execute("DELETE FROM APITokens WHERE Creator=$1 AND id=$2;",token.owner.id,token.id)
        return True
      except:
        return False
      
  async def get_tokens_from_user(self, user: int|User) -> Coroutine[Any, Any, list[Token]]:
    if type(user) is User:
      user_id = user.id
    else:
      user = await self.get_user(id=user)
      user_id = user.id
    async with self.pool.acquire() as conn:
      records = await conn.fetch("SELECT * FROM APITokens WHERE Creator=$1;", user_id)
      tokens = [Token.from_record(record, user) for record in records]
      return tokens

  async def generate_new_user_token(self, user: Union[int,User], regen_secure: bool = False) -> str:
    if type(user) is User:
      user = user.id
    async with self.pool.acquire() as conn:
      new_token: str = await self._generate_user_token_id(False)
      await conn.execute("UPDATE Users SET InsecureToken = $2 WHERE Id = $1",user,new_token)
      if regen_secure:
        new_secure_token: str = await self._generate_user_token_id(True)
        await conn.execute("UPDATE Users SET SecureToken = $2 WHERE Id = $1",user,new_secure_token)
      return new_token
    
  async def get_user_pastes_count(self, user: Union[int,User], all_pastes: bool) -> int:
    if type(user) is User:
      user = user.id
    async with self.pool.acquire() as conn:
      if all_pastes:
        count = (await conn.fetchrow("SELECT COUNT(*) FROM Pastes WHERE Creator=$1;", user))["count"]
      else:
        count = (await conn.fetchrow("SELECT COUNT(*) FROM Pastes WHERE Creator=$1 AND Visibility=1;", user))["count"]
      return count