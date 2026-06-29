"""
TESTING

# Categories

{categories}
"""

import json

from tornado.web import RequestHandler


class BaseDocHandler(RequestHandler):
    def initialize(self, doc_path: str = "", **kwargs):
        super().initialize(**kwargs)
        self.doc_path = doc_path
        self.documentation = getattr(self.application, "_documentation", None)


class DocRootHandler(BaseDocHandler):
    async def get(self):
        self.render("pages/home.html", route=f"{self.doc_path}/home.json")


class SpecRootHandler(BaseDocHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    async def get(self):
        markdown = __doc__
        categories = ""
        for category in self.documentation.categories:
            categories += f"\n- [{category}]({self.doc_path}/{category})"
        doc = {
            "openapi": "3.0.2",
            "info": {"description": markdown.format(categories=categories)},
        }
        self.write(json.dumps(doc))


class SpecRoutesHandler(BaseDocHandler):
    async def get(self):
        response = {}
        for category in self.documentation.categories:
            response[category] = f"{self.doc_path}/{category}.json"
        self.write(json.dumps(response))


class DocHandler(BaseDocHandler):
    async def get(self, category):
        self.render(
            "pages/redoc.html",
            route=f"{self.doc_path}/{category}.json",
            category=category,
        )


class SpecHandler(BaseDocHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", "application/json")

    async def get(self, category):
        doc = self.documentation.categories[category]
        self.write(json.dumps(doc))


BINDINGS = [
    ("/routes", SpecRoutesHandler),
    ("/home.json", SpecRootHandler),
    ("/home", DocRootHandler),
    ("/(?P<category>[^/]+).json", SpecHandler),
    ("/(?P<category>[^/]+)", DocHandler),
]
