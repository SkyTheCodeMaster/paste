# A generic collection of utilities for the paste server.

from __future__ import annotations

import asyncio
import importlib.util
import os
import re
import tomllib
from enum import Enum
from hashlib import sha256
from typing import TYPE_CHECKING

from aiohttp import web

if TYPE_CHECKING:
  from typing import Any, Coroutine

with open("config.toml") as f:
  contents = f.read()
  config = tomllib.loads(contents)
  HASH_ITERS = config["user"]["hash_iterations"] - 1

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
  for i in range(HASH_ITERS):
    hash = sha256(f"{username}{passwd}{hash}".encode()).hexdigest()
  return hash

async def ahash(passwd: str, username: str) -> Coroutine[Any, Any, str]:
  loop = asyncio.get_running_loop()
  result = await loop.run_in_executor(None, hash, passwd, username)
  return result

def is_hash(s: str) -> bool:
  "Checks if a string is a valid SHA256 hash."
  return bool(SHA256_REGEX.match(s))

# Helper function for routes
def get_routes(name:str,*,package=None) -> web.RouteTableDef:
  "Get the RouteTable for each cog."
  n = importlib.util.resolve_name(name,package)
  spec = importlib.util.find_spec(n)
  lib = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(lib)
  routes = lib.setup()
  return routes

def set_bit(v: int, index: int, x: bool) -> int:
  "Sets the index bit of v to the value of x"
  mask = 1 << index
  v &= ~mask
  if x:
    v |= mask
  return v