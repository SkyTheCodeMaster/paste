from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from typing_extensions import Self
  from asyncpg import Record

class User():
  name: str
  password: str # this is the hashed/salted/whatever password
  email: str
  id: int
  token: str
  avatar_type: int
  avatar_url: str
  joindate: int

  def __init__(self, *, 
               name: str = None, 
               password: str = None, 
               email: str = None, 
               id: int = None, 
               token: str = None, 
               avatar_type: int = None, 
               avatar_url: str = None, 
               joindate: int = None
              ):
    self.name = name
    self.password = password
    self.email = email
    self.id = id
    self.token = token
    self.avatar_type = avatar_type
    self.avatar_url = avatar_url
    self.joindate = joindate

  def clone(self) -> Self:
    "Clones the user object and makes a new one."
    return self.__class__(
      name=self.name,
      password=self.password,
      email=self.email,
      id=self.id,
      token=self.token,
      avatar_type=self.avatar_type,
      avatar_url=self.avatar_url,
      joindate = self.joindate
    )

  def __eq__(self, other: Self) -> bool:
    return \
      self.name == other.name and \
      self.password == other.password and \
      self.email == other.email and \
      self.id == other.id and \
      self.token == other.token

  @classmethod
  def from_record(cls, record: Record) -> User:
    return cls(
      name=record["username"],
      password=record["password"],
      email=record["email"],
      id=record["id"],
      token=record["token"],
      avatar_type=record["avatartype"],
      avatar_url=record["avatarurl"],
      joindate=record["joindate"]
    )