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

reg_b = re.compile(r"(android|bb\\d+|meego).+mobile|avantgo|bada\\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|mobile.+firefox|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\\.(browser|link)|vodafone|wap|windows ce|xda|xiino", re.I|re.M)
reg_v = re.compile(r"1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\\-(n|u)|c55\\/|capi|ccwa|cdm\\-|cell|chtm|cldc|cmd\\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\\-s|devi|dica|dmob|do(c|p)o|ds(12|\\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\\-|_)|g1 u|g560|gene|gf\\-5|g\\-mo|go(\\.w|od)|gr(ad|un)|haie|hcit|hd\\-(m|p|t)|hei\\-|hi(pt|ta)|hp( i|ip)|hs\\-c|ht(c(\\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\\-(20|go|ma)|i230|iac( |\\-|\\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\\/)|klon|kpt |kwc\\-|kyo(c|k)|le(no|xi)|lg( g|\\/(k|l|u)|50|54|\\-[a-w])|libw|lynx|m1\\-w|m3ga|m50\\/|ma(te|ui|xo)|mc(01|21|ca)|m\\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\\-2|po(ck|rt|se)|prox|psio|pt\\-g|qa\\-a|qc(07|12|21|32|60|\\-[2-7]|i\\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\\-|oo|p\\-)|sdk\\/|se(c(\\-|0|1)|47|mc|nd|ri)|sgh\\-|shar|sie(\\-|m)|sk\\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\\-|v\\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\\-|tdg\\-|tel(i|m)|tim\\-|t\\-mo|to(pl|sh)|ts(70|m\\-|m3|m5)|tx\\-9|up(\\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\\-|your|zeto|zte\\-", re.I|re.M)

def is_mobile(request: web.Request) -> bool:
  user_agent = request.headers["User-Agent"]
  b = reg_b.search(user_agent)
  v = reg_v.search(user_agent[0:4])
  return b or v