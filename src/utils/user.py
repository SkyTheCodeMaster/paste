from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from typing_extensions import Self

class User():
  def __init__(self, *, name: str = None, password: str = None, email: str = None, id: int = None):
    self.name = name
    self.password = password
    self.email = email
    self.id = id

  def clone(self) -> Self:
    "Clones the user object and makes a new one."
    return self.__class__(
      name=self.name,
      password=self.password,
      email=self.email,
      id=self.id,
    )

  def __eq__(self, other: Self) -> bool:
    return \
      self.name == other.name and \
      self.password == other.password and \
      self.email == other.email and \
      self.id == other.id