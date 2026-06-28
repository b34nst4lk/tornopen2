"""
This module provides the documenter class, which processes RequestHandlers and
their corresponding routes, and prepares Openapi compliant specs
"""

from pathlib import Path
from typing import Optional

from apispec import APISpec
from tornado.routing import URLSpec
from tornado.web import Application, url

from .api_spec import create_api_spec
from .handlers import BINDINGS

_TEMPLATES_DIR = str(Path(__file__).parent)


class Documents:
    def __init__(
        self,
        version="1.0.0",
        openapi_version="3.0.2",
        categorized_rules: dict[str, Optional[list[URLSpec]]] = None,
    ):
        self.categorized_rules = categorized_rules
        self.categories: dict[str, APISpec] = {}
        self.version = version
        self.openapi_version = openapi_version
        self.create_docs()

    def create_docs(self):
        for category, rules in self.categorized_rules.items():
            self.create_doc(category, rules)

    def create_doc(self, category: str, rules: list[URLSpec]):
        self.categories[category] = create_api_spec(category, rules)


def documenter(application: Application, path: str = "") -> Application:
    rules = application.wildcard_router.rules  # type: ignore
    categories = _categorize_rules(rules)
    application._documentation = Documents(categorized_rules=categories)  # type: ignore
    application.settings.setdefault("template_path", _TEMPLATES_DIR)
    application = _add_rules(application, rules, path)
    return application


def _categorize_rules(rules: list[URLSpec]) -> dict[str, list[URLSpec]]:
    categories = {}
    for rule in rules:
        if not isinstance(rule, URLSpec):
            continue

        handler_class = rule.handler_class
        if not hasattr(handler_class, "_doc_category"):
            handler_class._doc_category = "undocumented"
        if handler_class._doc_category not in categories:
            categories[handler_class._doc_category] = []

        categories[handler_class._doc_category].append(rule)
    return categories


def _add_rules(application: Application, rules: list[URLSpec], path: str = ""):
    rules = [
        url(f"{path}{route}", handler, kwargs={"doc_path": path})
        for route, handler in BINDINGS
    ]
    application.wildcard_router.add_rules(rules)  # type: ignore
    return application
