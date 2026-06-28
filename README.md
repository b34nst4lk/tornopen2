# tornopen

`tornopen` (Tornado + OpenAPI) is a small library that brings type-annotated
request validation, error handling, and automatic OpenAPI/Redoc documentation
to [Tornado][tornado] `RequestHandler`s.

It lets you write handler methods like this:

```python
class HelloHandler(RequestHandler):
    @validate_arguments
    async def get(self, name: str, age: int) -> HelloResponse:
        ...
```

…instead of manually calling `get_query_argument`, hand-rolling JSON parsing,
`try/except`ing validation, and writing a separate OpenAPI spec by hand. The
decorator inspects the signature, validates the incoming request against the
annotations, runs the handler, serializes the `ResponseBody` return value, and
records the route so it can be emitted as an OpenAPI spec.

## What this repo is trying to do

Goal: make type annotation, request validation, and auto-generated API docs
**gradually adoptable** on an existing Tornado codebase, with no rewrite.

Design principles:

1. **Annotation-driven.** Path params, query params, JSON request bodies, and
   responses are all declared as type hints (`str`, `int`, `pydantic` models,
   `Enum`, `Annotated[..., Field(...)]`). The decorator does the wiring.
2. **Gradual adoption.** Undecorated handlers keep working. `validate_arguments`
   bypasses Tornado's own error-handling path only for the exceptions it owns
   (`HTTPError`, `RequestValidationError`, `pydantic.ValidationError`), so it
   can be rolled out per-handler without breaking neighbours.
3. **One source of truth.** The same annotations that validate the request also
   generate the OpenAPI spec — no separate spec file to keep in sync.
4. **Served docs.** Wrapping the app in `documenter(app, path="_docs")` mounts
   Redoc pages and per-category `.json` specs at the chosen path.
5. **Pluggable errors.** Custom exception classes map to status codes and
   response bodies; `@validate_arguments.exception_handler(SomeError)` registers
   handlers for arbitrary exception types.

Under the hood it leans on [pydantic][pydantic] for validation/modeling and
[apispec][apispec] for spec assembly, and renders via [Redoc][Redoc].

Out of the box only `application/json` request and response bodies are
supported.

## Status

Experimental. Tag/category documentation helpers (`doc_category`, `doc_tag`,
`doc_summary`) are explicitly flagged as clunky and subject to change. The
`validate_arguments` decorator is adapted from pydantic's experimental
decorator of the same name (pre-2.0).

## Install

```
uv add tornopen
```

or, with pip:

```
pip install tornopen
```

Imports are `from tornopen import ...`.

Dependencies: `tornado`, `pydantic` (v2), `apispec`, `typing_extensions`;
`orjson` optional (falls back to stdlib `json`). Redoc is loaded from CDN at
view time, no asset install needed.

## Layout

```
tornopen/
├── __init__.py        # public API surface
├── decorator.py       # validate_arguments, doc_category/doc_tag/doc_summary
├── model.py           # BaseModel, RequestBody, ResponseBody, QueryParams, Enum
├── http_error.py     # HTTPError, RequestValidationError
├── handlers.py        # Redoc/spec-serving RequestHandlers mounted by documenter
├── document.py        # documenter(): categorize rules, build APISpecs, mount docs
├── pages/             # Redoc HTML templates
├── api_spec/
│   ├── core.py            # TornOpenAPISpec (tag tracking)
│   ├── plugin.py          # TornOpenPlugin: builds operations from handlers
│   ├── create_api_spec.py # regex->url, param parsing, spec assembly + tag groups
│   └── exception_finder.py# AST-walks handler source to discover raised HTTPErrors
└── tests/
    ├── decorator/     # validation, error handling, enum casting, query/path params
    └── api_spec/       # paths, model collisions, nested models, http error docs
```

Key pieces:

- `ValidateHTTPCallWrapper` (`decorator.py:169`) — inspects a handler method's
  signature once at import time and builds a pydantic model for the path/query
  params and a reference to the `RequestBody` subclass, if any.
- `ValidateArgumentsDecoratorFactory` (`decorator.py:257`) — produces the
  `validate_arguments` decorator; owns the exception-handler registry; runs
  validation, executes the handler (sync or async), and writes the
  `ResponseBody` JSON.
- `documenter` (`document.py:37`) — groups `URLSpec`s by `_doc_category`,
  builds an `APISpec` per category via `create_api_spec`, attaches them to the
  app as `_documentation`, and mounts the Redoc/spec handlers from
  `handlers.BINDINGS`.
- `TornOpenPlugin` (`api_spec/plugin.py:57`) — apispec plugin that drives
  path/operation generation from the handler class and its
  `handler_class_params`.
- `exception_finder.get_exceptions` (`api_spec/exception_finder.py:23`) —
  AST-walks the handler source to find `raise HTTPError(...)` call sites so
  failure responses can be documented without manual annotation.

## Usage

### Hello world

```python
import asyncio
from tornado.web import RequestHandler, Application, url
from tornopen import validate_arguments

class HelloWorldRequestHandler(RequestHandler):
    @validate_arguments
    async def get(self, name: str):
        self.write(f"hello {name}")

def make_app():
    return Application([
        url(r"/hello/(?P<name>.*?)", HelloWorldRequestHandler),
    ])

async def main():
    app = make_app()
    app.listen(8888)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

```bash
curl "http://localhost:8888/hello/world"
```

### Query parameters

Params not in the URL path are treated as query params.

```python
class HelloWorldRequestHandler(RequestHandler):
    @validate_arguments
    async def get(self, name: str, age: int):
        self.write(f"My name is {name}. I am {age} years old.")
```

```bash
curl "http://localhost:8888/hello/John?age=10"        # ok
curl "http://localhost:8888/hello/John?age=invalid"   # 400 validation_error
curl "http://localhost:8888/hello/John"               # 400 validation_error
```

### JSON request body

Subclass `RequestBody` and annotate a parameter with it.

```python
from tornopen import validate_arguments, RequestBody

class HelloWorldRequest(RequestBody):
    name: str
    age: int

class HelloWorldRequestHandler(RequestHandler):
    @validate_arguments
    async def post(self, body: HelloWorldRequest):
        self.write(f"My name is {body.name}. I am {body.age} years old.")
```

```bash
curl -X POST "http://localhost:8888/hello" \
    -H 'Content-Type: application/json' \
    -d '{"name": "John", "age": 20}'
```

### Typed responses

Annotate the return type with a `ResponseBody` subclass and `return` an
instance; `validate_arguments` serializes it.

```python
from tornopen import validate_arguments, RequestBody, ResponseBody

class HelloWorldRequest(RequestBody):
    name: str
    age: int

class HelloWorldResponse(ResponseBody):
    name: str
    age_in_seconds: int

class HelloWorldRequestHandler(RequestHandler):
    @validate_arguments
    async def post(self, body: HelloWorldRequest) -> HelloWorldResponse:
        return HelloWorldResponse(
            name=body.name,
            age_in_seconds=body.age * 365 * 86400,
        )
```

### Pydantic fields and custom validation

`Annotated` and `Field` are re-exported for annotated advanced validation.

```python
from typing import Optional
from tornopen import validate_arguments, Annotated, Field

class HelloWorldRequestHandler(RequestHandler):
    @validate_arguments
    async def get(
        self,
        name: Annotated[Optional[str], Field(description="Optional name")] = None,
    ) -> SmartVideoDashboardResponse:
        ...
```

## How it works

### At import

For each decorated method, a `ValidatedFunction` (`ValidateHTTPCallWrapper`) is
built from the signature: a pydantic model validates path/query params, and
the `RequestBody` subclass (if any) is captured for body parsing.

### On request

1. **Validate** — path args, query args, and JSON body are parsed and passed
   through the validators. On failure, `RequestValidationError` (a subclass of
   `pydantic.ValidationError`) is raised and turned into a `400` by the
   default handler.
2. **Execute** — the handler runs with validated, typed arguments.
3. **Finish** — if the handler returns a `ResponseBody`, it is serialized with
   `model_dump_json` and written with `Content-Type: application/json`.

## Error handling

Tornado's normal error path (`write_error` + `tornado.web.HTTPError`) is
bypassed for the three exception types `validate_arguments` owns:
`annotation_helper.HTTPError`, `annotation_helper.RequestValidationError`, and
`pydantic.ValidationError`. Everything else falls through to Tornado as usual.

> **Warning:** `HTTPError` must only be raised inside methods decorated with
> `validate_arguments`. Raising it from an undecorated handler returns a
> server error.

### `HTTPError`

Default response shape:

```json
{ "error": { "type": "str", "message": "str" } }
```

### `RequestValidationError`

Raised only at the request-validation step. A bare `pydantic.ValidationError`
raised elsewhere (e.g. inside your handler) is treated as a `500` and logged,
since it shouldn't be surfaced to the client.

### Custom errors

Tie an error to a status code / `error_type`:

```python
from tornopen import HTTPError

class NotFoundError(HTTPError):
    def __init__(self, error_message: str):
        super().__init__(404, error_type="not_found", error_message=error_message)
```

Or fully customize the body — override `dict()` and set `status_code`:

```python
from typing import Dict, List
from tornopen import HTTPError

class ListOfErrors(HTTPError):
    def __init__(self, code: int, errors: List[Dict[str, str]]):
        self.status_code = code
        self.errors = errors

    def dict(self) -> dict:
        return {"errors": self.errors}
```

### Registering exception handlers

`@validate_arguments.exception_handler(SomeError)` registers a handler with
signature `Callable[[Exception], Tuple[int, str]]` returning
`(status_code, response_body)`.

```python
import json, logging
from tornopen import validate_arguments, HTTPError

@validate_arguments.exception_handler(ValueError)
def handle_value_error(e: ValueError):
    logging.error(e)
    return 400, json.dumps({"error_type": "unexpected value"})

class ErrorHandler(RequestHandler):
    @validate_arguments
    async def get(self, error: str):
        match error:
            case "http_error":
                raise HTTPError(444, error_type="my error", error_message="msg")
            case "value_error":
                raise ValueError
```

## Documentation

Wrap the app in `documenter` to mount Redoc + per-category OpenAPI JSON at the
given path.

```python
from tornopen import validate_arguments, documenter

async def main():
    app = make_app()
    app.listen(8888)
    app = documenter(app, path="_docs")
    await asyncio.Event().wait()
```

- `http://localhost:8888/_docs/home` — Redoc landing page listing categories.
- `http://localhost:8888/_docs/<category>.json` — OpenAPI spec for a category.
- `http://localhost:8888/_docs/home.json` — root OpenAPI doc with category index.

By default everything lands in the `undocumented` category and is `untagged`.

### Categorizing endpoints

> **Warning:** experimental, subject to change.

```python
from tornopen import validate_arguments, documenter, doc_category

@doc_category("hello")
class HelloWorldRequestHandler(RequestHandler):
    @validate_arguments
    async def get(self, name: str):
        self.write(f"hello {name}")
```

`curl localhost:8888/_docs/hello.json` returns the OpenAPI spec for the
`hello` category.

### Tagging endpoints within a category

> **Warning:** experimental, subject to change.

```python
from tornopen import (
    validate_arguments, documenter, doc_category, doc_tag,
)

@doc_category("hello")
class HelloWorldRequestHandler(RequestHandler):
    @validate_arguments
    @doc_tag("world")
    async def get(self, name: str):
        self.write(f"hello {name}")
```

The operation is now tagged `"world"` and grouped under that tag in Redoc.

### Operation summaries

```python
from tornopen import doc_summary

class HelloWorldRequestHandler(RequestHandler):
    @validate_arguments
    @doc_summary("Say hello to someone by name")
    async def get(self, name: str):
        ...
```

Without `doc_summary`, the default is `"<METHOD>: <path>"`.

## Running the tests

```bash
pytest tests/
```

`tornado`, `pydantic`, `apispec`, and `typing_extensions` must be installed.

[tornado]: https://www.tornadoweb.org/
[apispec]: https://apispec.readthedocs.io/en/latest/
[pydantic]: https://pydantic-docs.helpmanual.io/
[pydantic-field-types]: https://pydantic-docs.netlify.app/usage/types/
[pydantic-field-customization]: https://pydantic-docs.helpmanual.io/usage/schema/#field-customization
[Redoc]: https://github.com/Redocly/redoc