# A generic collection of utilities for the paste server.

from __future__ import annotations

import importlib.util
import re
from enum import Enum
from hashlib import sha256

from aiohttp import web

Visibility = Enum("VISIBILITY", ("PUBLIC", "UNLISTED", "PRIVATE"))

SHA256_REGEX = re.compile("^[0-9A-Fa-f]{64}$",re.IGNORECASE)

class aobject(object):
    """Inheriting this class allows you to define an async __init__.

    So you can create objects by doing something like `await MyClass(params)`
    """
    async def __new__(cls, *a, **kw):
        instance = super().__new__(cls)
        await instance.__init__(*a, **kw)
        return instance

    async def __init__(self):
        pass

def hash(passwd: str, username: str) -> str:
  "Returns a SHA256 hash of the password."
  hash = sha256(f"{username}{passwd}".encode()).hexdigest()
  for i in range(9):
    hash = sha256(f"{username}{passwd}{hash}".encode()).hexdigest()
  return hash

def isHash(s: str) -> bool:
  "Checks if a string is a valid SHA256 hash."
  return bool(SHA256_REGEX.match(s))

# Helper function for routes
def getRoutes(name:str,*,package=None) -> web.RouteTableDef:
  "Get the RouteTable for each cog."
  n = importlib.util.resolve_name(name,package)
  spec = importlib.util.find_spec(n)
  lib = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(lib)
  routes = lib.setup()
  return routes

def setBit(v: int, index: int, x: bool) -> int:
  "Sets the index bit of v to the value of x"
  mask = 1 << index
  v &= ~mask
  if x:
    v |= mask
  return v
