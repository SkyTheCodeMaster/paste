# A generic collection of utilities for the paste server.

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import io
import os
import re
import urllib.parse
import tomllib
from enum import Enum
from typing import TYPE_CHECKING

from aiohttp import web
from PIL import Image

if TYPE_CHECKING:
  from typing import Any, Coroutine

with open("config.toml") as f:
  contents = f.read()
  config = tomllib.loads(contents)
  HASH_ITERS = config["user"]["hash_iterations"]

Visibility = Enum("VISIBILITY", ("PUBLIC", "UNLISTED", "PRIVATE"))

SHA512_REGEX = re.compile("^[0-9A-Fa-f]{128}$",re.IGNORECASE)

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
  "Returns a SHA512 hash of the password."
  salt = hashlib.sha512(username.encode()).digest()
  output_hash = hashlib.pbkdf2_hmac("sha512", passwd.encode(), salt, HASH_ITERS).hex()
  return output_hash

async def ahash(passwd: str, username: str) -> Coroutine[Any, Any, str]:
  loop = asyncio.get_running_loop()
  result = await loop.run_in_executor(None, hash, passwd, username)
  return result

async def gravatar(user_email: str) -> Coroutine[Any, Any, str]:
  "Return a gravatar URL for the email"
  loop = asyncio.get_running_loop()
  def process():
    email = user_email.strip().lower()
    hash = hashlib.sha256(email.encode()).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash}.png?d=retro"
  
  return await loop.run_in_executor(None, process)

async def resize_image_bytes(image_data: bytes, size: tuple[int,int] = (80,80)) -> bytes:
  loop = asyncio.get_running_loop()
  image = await loop.run_in_executor(None, lambda: Image.open(io.BytesIO(image_data)))
  image = await loop.run_in_executor(None, image.resize, size)
  output_bytes = io.BytesIO()
  await loop.run_in_executor(None, lambda: image.save(output_bytes, format="png"))
  output_bytes.seek(0)
  return output_bytes.read()


def is_hash(s: str) -> bool:
  "Checks if a string is a valid SHA256 hash."
  return bool(SHA512_REGEX.match(s))

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

def join_url_path(a: str, b: str) -> str:
  return urllib.parse.urljoin(a, b)

def _bytestring_to_bytes(data: str) -> bytes:
  "Converts '21,37,223,255' into bytes because javascript files just suck"
  byte_list: list[int] = [int(byte) for byte in data.split(",")]
  return bytes(byte_list)

async def bytestring_to_bytes(data: str) -> Coroutine[Any, Any, bytes]:
  loop = asyncio.get_running_loop()
  result = await loop.run_in_executor(None, _bytestring_to_bytes, data)
  return result