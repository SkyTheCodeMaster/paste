# Postgresql utils

from __future__ import annotations

import random
import string
import json
from inspect import isawaitable
from typing import List, Union

import asyncpg

from utils.paste import Paste
from utils.token import Token
from utils.user import User
from utils.utils import hash

with open("config.json") as f:
  contents = f.read()
  PASTE_ID_LENGTH = json.loads(contents)["paste.id_length"]
  TOKEN_ID_LENGTH = json.loads(contents)["token.id_length"]

class PGUtils:
  def __init__(self, conn: asyncpg.Connection = None):
    self.conn = conn

  async def getUser(self,*,name: str = None, email: str = None, id: int = None) -> User:
    "Get a user from either username, email, or the ID, and return a User object."
    if name:
      row = await self.conn.fetchrow("SELECT * FROM Users WHERE Username LIKE $1", name)
    elif email:
      row = await self.conn.fetchrow("SELECT * FROM Users WHERE Email LIKE $1", email)
    elif id:
      row = await self.conn.fetchrow("SELECT * FROM Users WHERE Id = $1", id)
    
    return User(
      name=row["username"],
      password=row["password"],
      email=row["email"],
      id=row["id"]
    )

  async def createNewUser(self,*,name: str, passwd: str, email: str = None) -> int:
    "Create a new user, and return the ID of the user."
    h = hash(passwd,name)
    record = await self.conn.fetchrow("INSERT INTO Users VALUES ($1, $2, $3)", name, h, email)
    return record["id"]

  async def getPastesFromCreator(self,*,creator: int) -> List[Paste]:
    "Get all of the pastes registered to a user"
    records = await self.conn.fetch("SELECT * FROM Pastes WHERE Creator = $1", creator)
    out: List[Paste] = []
    for record in records:
      paste = Paste(
        id=record["id"],
        creator=record["creator"],
        data=record["content"],
        filepath=record["filepath"],
        visibility=record["visibility"],
      )
      out.append(paste)
    return out

  async def getPastesFromSearch(self,*,creator: Union[int,str,User] = None, title: str = None, id: str = None) -> List[Paste]:
    "Get a paste from either the creator id, or title, or the id, and return a Paste object."
    if creator:
      if type(creator) is int:
        creator = creator
      elif type(creator) is str:
        creator = (await self.getUser(name=creator)).id
      elif type(creator) is User:
        creator = creator.id
        
      records = await self.conn.fetch("SELECT * FROM Pastes WHERE Creator ", creator)
    elif title:
      records = await self.conn.fetch("SELECT * FROM Pastes WHERE Email LIKE %$1%", title)
    elif id:
      records = await self.conn.fetch("SELECT * FROM Pastes WHERE Id = $1", id)
    
    out = []
    for record in records:
      paste = Paste(
        id=record["id"],
        creator=record["creator"],
        data=record["content"],
        visibility=record["visibility"],
        title=record["title"]
      )
      out.append(paste)
    return out

  async def getPastesFromFunction(self,lambd: function,*,limit:int=50,offset:int=0) -> List[Paste]:
    """Use the lambda to return a list of pastes. Lambda's argument is a Paste object. Pastes `creator` attribute is a User object
    The limit function returns only a max of the limit, and offset is pagination"""
    # Get all of the pastes
    records = await self.conn.fetch("SELECT * FROM Pastes LIMIT $1 OFFSET $2",limit,offset*limit)
    # Now turn it into a list of pastes
    print(records)
    pastes = []
    for record in records:
      paste: Paste = Paste.fromRecord(record)
      pastes.append(paste)
    
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

  async def verifyToken(self, token: Union[Token,str]) -> Union[Token,bool]:
    "Verifies a token and returns the Token object, or False if the token does not exist."
    if type(token) is Token:
      return token
    record = await self.conn.fetchrow("SELECT * FROM APITokens WHERE id = $1",token)
    if record:
      user: User = await self.getUser(id=record["creator"])
      token = Token(
        name=record["title"],
        owner=user,
        permissions=record["perms"],
        id=record["id"],
      )
      return token
    else:
      record = await self.conn.fetchrow("SELECT * FROM Users WHERE Password = $1",token)
      if record:
        user = User(
          name=record["username"],
          password=record["password"],
          email=record["email"],
          id=record["id"]
        )
        token = Token(
          name="PASSWORD",
          owner=user,
          permissions=255,
          id=token
        )
        return token
      else:
        return False

  async def _generatePasteID(self) -> str:
    "Generate an ID, while making sure it does not exist in the database already."
    pool: str = string.ascii_letters+string.digits
    pasteID = "".join(random.choices(pool,k=PASTE_ID_LENGTH))
    record = await self.conn.fetchrow("SELECT * FROM Pastes WHERE Id = $1;",pasteID)
    if record:
      return await self._generatePasteID()
    else:
      return pasteID

  async def _generateTokenID(self) -> str:
    "Generate an ID, while making sure it does not exist in the database already."
    pool: str = string.ascii_letters+string.digits
    pasteID = "".join(random.choices(pool,k=TOKEN_ID_LENGTH))
    record = await self.conn.fetchrow("SELECT * FROM APITokens WHERE Id = $1;",pasteID)
    if record:
      return await self._generateTokenID()
    else:
      return pasteID

  async def createNewPaste(self, paste: Paste, token: Union[Token,str]) -> Union[Paste,bool]:
    "Create a new paste, returning the paste object with the ID field set. The ID field will be overwritten with the new one. Token is used for determining who owns the paste, and if this token can create pastes."
    if type(token) is str:
      token = await self.verifyToken(token)
      if not token: return False,"verify token failed/not passed"
    if not token.permissions.createPaste:
      return False,"missing create intent"
    
    pasteID = await self._generatePasteID()
    if type(paste.data) is not bytes:
      paste.data = paste.data.encode()
    await self.conn.execute("INSERT INTO Pastes VALUES ($1, $2, $3, $4, $5);",pasteID,token.owner.id,paste.data,paste.visibility,paste.title)

    return (await self.getPastesFromSearch(id=pasteID))[0],""

  async def editPaste(self, paste:Paste, token: Union[Token,str]) -> Union[Paste,bool]:
    "Edit a paste, returns the new paste object."
    if type(token) is str:
      token = await self.verifyToken(token)
      if not token: return False
    if not token.permissions.editPaste:
      return False

    nPaste = await self.getPastesFromSearch(id=paste.id)
    if not nPaste: return False
    nPaste = nPaste[0]

    if token.owner.id != nPaste.creator:
      return False

    await self.conn.execute("UPDATE Pastes SET Content = $1, Title = $2, Visibility = $3 WHERE id = $4",paste.data,paste.title,paste.visibility,nPaste.id)

    return (await self.getPastesFromSearch(id=nPaste.id))[0]

  async def deletePaste(self,paste: Paste, token: Token) -> bool:
    "Delete a paste, returning a boolean"
    if type(token) is str:
      token = await self.verifyToken(token)
      if not token: return False
    if not token.permissions.deletePaste:
      return False

    nPaste = await self.getPastesFromSearch(id=paste.id)
    if not nPaste: return False
    nPaste = nPaste[0]

    if token.owner.id != nPaste.creator:
      return False

    await self.conn.execute("DELETE FROM Pastes WHERE id = $1",nPaste.id)

    return True