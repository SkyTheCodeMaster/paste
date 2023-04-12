from __future__ import annotations

import os

from aiohttp import web
import django.template
from django.conf import settings as django_settings

django_settings.configure()

routes = web.RouteTableDef()

# Load all of the templates in the static folder.
engine = django.template.Engine()
templates: dict[str,django.template.Template] = {}

for file in os.listdir("templates"):
  with open(os.path.join("templates",file),"r") as f:
    tmpl = engine.from_string(f.read())
    templates[file] = tmpl

print(templates)

@routes.get("/")
async def get_index(request: web.Request) -> web.Response:
  # Load the index.html template
  rendered = templates["index.html"].render(django.template.Context({}))
  return web.Response(body=rendered,content_type="text/html")

def setup() -> web.RouteTableDef:
  return routes