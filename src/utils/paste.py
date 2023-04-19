from __future__ import annotations

import json
import urllib.parse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from typing import Union

  from asyncpg import Record
  from typing_extensions import Self

  from utils.pg import PGUtils
  from utils.user import User
  from utils.utils import Visibility


with open("config.json") as f:
  PUBLIC_URL = json.loads(f.read())["srv.publicurl"]

class Paste:
  def __init__(self,*,id: str, creator: int,data: bytes, visibility: Union[Visibility,int], title: str, created: int = None, modified: int = None) -> None:
    self.id = id
    self.creator = creator
    self.data = data
    self.visibility = visibility
    self.title = title
    self.created = created
    self.modified = modified
  
  @property
  def url(self) -> str:
    return urllib.parse.urljoin(PUBLIC_URL,self.id)

  @property
  def json(self) -> str:
    out = {
      "id": self.id,
      "creator": self.creator,
      "visibility":self.visibility,
      "title":self.title,
      "content": self.text_content,
      "created": self.created,
      "modified": self.modified
    }
    return json.dumps(out)

  async def get_creator(self,pgUtils: PGUtils) -> User:
    "Helper method to get the creator of the paste."
    return await pgUtils.get_user(id=self.creator)

  @property
  def text_content(self) -> str:
    return self.data.decode()

  def edit(self,*,newContent: str = None, newVisibility: Union[Visibility,int] = None, newTitle: str = None) -> None:
    "Edits the paste *in memory*, not in the database."
    if newContent:
      self.data = newContent.encode()

    if newVisibility:
      if type(newVisibility) is Visibility:
        self.visibility = newVisibility.value
      else:
        self.visibility = newVisibility
    
    if newTitle:
      self.title = newTitle

  @classmethod
  def from_record(cls, record: Record) -> Self:
    paste = cls(
      id=record["id"],
      creator=record["creator"],
      data=record["content"],
      visibility=record["visibility"],
      title=record["title"],
      created=record["created"],
      modified=record["modified"]
    )
    return paste

  def clone(self) -> Self:
    newPaste = Paste(
      id=self.id,
      creator=self.creator,
      data=self.data,
      visibility=self.visibility,
      title=self.title,
      created=self.created,
      modified=self.modified
    )
    return newPaste

  async def update(self,pgUtils:PGUtils) -> Self:
    paste = (await pgUtils.get_pastes_from_search(id=self.id))[0]
    self.id = paste.id
    self.creator= paste.creator
    self.data = paste.data
    self.visibility = paste.visibility
    self.title = paste.title
    self.created = paste.created
    self.modified = paste.modified
    return self
