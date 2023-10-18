from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from utils.user import User
  from asyncpg import Record

class TokenPermissions:
  create_paste = False
  edit_paste = False
  delete_paste = False
  view_private = False

  @property
  def json(self) -> str:
    data = {
      "create": self.create_paste,
      "edit": self.edit_paste,
      "delete": self.delete_paste,
      "viewpriv": self.view_private
    }
    return json.dumps(data)

class Token:
  name: str
  owner: User
  perms: TokenPermissions
  id: str
  ident: str
  user_token: bool
  secure: bool
  def __init__(self,*,name: str, owner: User, permissions: int, id: str, ident: str) -> None:
    self.name = name
    self.owner = owner
    self.perms = permissions
    self.id = id
    self.ident = ident
    self.user_token = name in ["INSECUREPASSWORD","SECUREPASSWORD"]
    self.secure = name == "SECUREPASSWORD"

  @property
  def permissions(self) -> TokenPermissions:
    perms = TokenPermissions()
    perms.create_paste = self.perms & 1 == 1
    perms.edit_paste   = self.perms & 2 == 2
    perms.delete_paste = self.perms & 4 == 4
    perms.view_private = self.perms & 8 == 8
    return perms
    
  @property
  def json(self) -> str:
    data = {
      "title":self.name,
      "owner":self.owner.name,
      "permissions":self.perms,
      "id":self.id,
      "ident": self.ident
    }
    return json.dumps(data)
  
  @property
  def front(self) -> dict:
    perms = self.permissions
    return {
      "name": self.name,
      "owner": self.owner.name,
      "permissions": perms.json,
      "ident": self.ident
    }
  
  @classmethod
  def from_record(cls, record: Record, owner: User):
    if owner.id != record["creator"]:
      raise ValueError("Token record.creator does not match passed user object!")
    return cls(
      name=record["title"],
      owner=owner,
      permissions=record["perms"],
      id=record["id"],
      ident=record["ident"]
    )