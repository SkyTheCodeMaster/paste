from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from utils.user import User

class TokenPermissions:
  createPaste = False
  editPaste = False
  deletePaste = False
  viewPrivate = False

class Token:
  def __init__(self,*,name: str, owner: User, permissions: int, id: str) -> None:
    self.name = name
    self.owner = owner
    self.perms = permissions
    self.id = id

  @property
  def permissions(self) -> TokenPermissions:
    perms = TokenPermissions()
    perms.createPaste = self.perms & 1 == 1
    perms.editPaste   = self.perms & 2 == 2
    perms.deletePaste = self.perms & 4 == 4
    perms.viewPrivate = self.perms & 8 == 8
    return perms
    
  @property
  def json(self) -> str:
    data = {
      "title":self.name,
      "owner":self.owner.name,
      "permissions":self.perms,
      "id":self.id,
    }
    return json.dumps(data)