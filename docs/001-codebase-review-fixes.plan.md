# Codebase review fixes — Plan 001

Status: ready to execute.
Branches: `chore/package-bootstrap` (Phase 0 → PR #1 → merge to `main`),
then `fix/codebase-review` off updated `main` (Phases 1-11 → PR #2).

Conventions for every phase:
- Tests-first where behavior changes (red before impl).
- Verify with `uv run pytest`, `uv run ruff check`, `uv run ty check`.
- One commit per phase; explicit `git add <files>` (never `git add .`).

## Decisions

| Item | Decision |
|------|----------|
| Layout | `src/tornopen/` |
| Python | `>=3.10` (StrEnum shim) |
| Tooling | uv-managed pyproject + lock, ruff + ty |
| Phase 0 branch | `chore/package-bootstrap` → PR #1 → merge to `main` |
| Fixes branch | `fix/codebase-review` off updated `main` → PR #2 |
| Phase 3 | `415 Unsupported Media Type` for non-JSON to `RequestBody` handlers; `UnsupportedMediaTypeError` exported in `__all__` for user override/raising; response body follows `HTTPError.dict()` structure |
| Phase 9 (test fixes #11) | DEFERRED to future error-management-UX pass |
| Skipped findings | #15 pydantic v2 `.schema()` migration, #20 Redoc CDN pin |

## Findings reference (from codebase review)

| # | Severity | Finding |
|---|----------|---------|
| 1 | High | `is_primitive`/`is_collection` use `get_args(type)` instead of `get_args(type_)` — typed-list query params broken |
| 2 | High | `ValidateArgumentsDecoratorFactory(exclude_none=...)` is a no-op |
| 3 | High | `retrieve_request_body` returns dict for form-encoded → `json.loads` crashes |
| 4 | Med | `RequestValidationError.status_code` is the string `"400"` |
| 5 | Med | Validation-error early-return path skips `Content-Type: application/json` header |
| 6 | Med | `cast_enum_to_str` sync wrapper only works as inner decorator of `validate_arguments` |
| 7 | Med | `documenter` mutates handler classes (`_doc_category` leak) |
| 8 | Med | `create_api_spec` leaks `handler.handler_class_params` on exception |
| 9 | Med | `SuccessResponseModelSchema` dead code |
| 10 | Med | `exception_finder.get_exceptions` has dead `results` list, `vars` shadow, undocumented limits |
| 11 | Med | Several tests broken/empty/literal-string-asserting |
| 12 | Med | Custom `HTTPError` without `error_type`/`error_message` blows up at runtime |
| 13 | Hygiene | No project metadata, no commits, no `.gitignore` |
| 14 | Hygiene | No lint/type-check config; mixed typing style |
| 15 | Low | Pydantic v2 deprecation: `BaseModel.schema()` — SKIPPED |
| 16 | Low | `_clear_none_from_dict` lacks comment re `0`/`False` preservation |
| 17 | Low | `Documents.categories` typed wrong (`dict[str, APISpec]` holds `dict`) |
| 18 | Low | Singleton `validate_arguments` + global exception registry — document only |
| 19 | Low | `_doc_*` decorator stacking order fragile — test + document |
| 20 | Low | Redoc CDN unpinned — SKIPPED |
| 21 | Low | Dead/dup files; `TimestampedBaseModel` unused; name-mangled attr access; reused var names; bare except |

---

## Phase 0 — Package bootstrap

Branch: `chore/package-bootstrap` (off unborn `main`).
PR: #1 → merge to `main`. Then `git switch -c fix/codebase-review` off updated `main`.

- [ ] (1) Tests: none new; confirm existing suite passes post-restructure.
- [ ] (2) Impl:
  - [ ] Add `.gitignore`: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `.ty_cache/`, `.venv/`, `dist/`, `build/`.
  - [ ] Add `pyproject.toml` (uv `--lib`): `[project]` name=`tornopen`, requires-python=`>=3.10`, deps `tornado`, `pydantic>=2`, `apispec`, `typing_extensions`, optional `orjson`; `[dependency-groups] dev = ["pytest","pytest-tornado","ruff","ty"]`; `[tool.ruff]`, `[tool.ty]`, `[tool.pytest.ini_options]`.
  - [ ] `git mv` current package → `src/tornopen/`.
  - [ ] Test imports: `from ... import` → `from tornopen import`; tests at repo-root `tests/`.
  - [ ] `model.py`: `try: from enum import StrEnum / except ImportError: class StrEnum(str, Enum)` shim for 3.10.
  - [ ] `README.md`: `private.lib.annotation_helper` → `tornopen` throughout.
  - [ ] Delete `tests/decorator/handler_test_cases.py` (byte-identical to `__init__.py`).
  - [ ] `uv sync` → `uv.lock`.
- [ ] (3) Verify: `uv run pytest` green, `uv run ruff check`, `uv run ty check`.
- [ ] (4) Commit:
  ```
  git add .gitignore pyproject.toml uv.lock src/tornopen tests README.md
  git rm tests/decorator/handler_test_cases.py
  git commit -m "Initial import: tornopen package scaffolding"
  ```
- [ ] Push branch, open PR #1, merge to `main`.

---

## Phase 1 — Fix `is_primitive`/`is_collection` `get_args` typo (#1)

- [ ] (1) Tests: `tests/decorator/test_typed_list_query_params.py`:
  - [ ] `list[int]` handler: `?param=1,2,3` → 200; `?param=1,abc` → 400.
  - [ ] `Optional[list[int]]` handler: omitted → 200.
  - [ ] Red before fix.
- [ ] (2) Impl: `src/tornopen/decorator.py:61` and `:76` — `get_args(type)` → `get_args(type_)`.
- [ ] (3) Verify: new tests green; no regressions.
- [ ] (4) Commit:
  ```
  git add src/tornopen/decorator.py tests/decorator/test_typed_list_query_params.py
  git commit -m "fix(decorator): correct get_args() typo breaking typed-list query params"
  ```

---

## Phase 2 — Fix `exclude_none` factory arg no-op (#2)

- [ ] (1) Tests: `tests/decorator/test_exclude_none.py`:
  - [ ] `factory = ValidateArgumentsDecoratorFactory(exclude_none=True)`.
  - [ ] Handler returns `Response` with `Optional[str] = None` field.
  - [ ] Assert response JSON omits the key. Red now.
- [ ] (2) Impl: `src/tornopen/decorator.py:277` — bind `self.exclude_none` in wrapper (drop `__call__`'s `exclude_none` kwarg or default to `self.exclude_none`).
- [ ] (3) Verify.
- [ ] (4) Commit:
  ```
  git add src/tornopen/decorator.py tests/decorator/test_exclude_none.py
  git commit -m "fix(decorator): honor ValidateArgumentsDecoratorFactory(exclude_none=...)"
  ```

---

## Phase 3 — 415 for non-JSON request bodies (#3)

- [ ] (1) Tests: `tests/decorator/test_request_body_content_type.py`:
  - [ ] Form-encoded POST to `RequestBody` handler → 415 + `error.type == "unsupported_media_type"`.
  - [ ] JSON POST → 200.
  - [ ] No Content-Type + no body → 400 validation_error.
  - [ ] User-registered `@exception_handler(UnsupportedMediaTypeError)` override → custom status/body.
- [ ] (2) Impl:
  - [ ] `src/tornopen/http_error.py`: new `UnsupportedMediaTypeError(HTTPError)` (status 415, `error_type="unsupported_media_type"`); add to `__all__`.
  - [ ] `src/tornopen/decorator.py`: register default handler in `ValidateArgumentsDecoratorFactory.exception_handlers`; in wrapper, when `request_body_name` set and Content-Type present and non-JSON → raise `UnsupportedMediaTypeError`.
  - [ ] `retrieve_request_body` returns `None` for non-JSON (Content-Type-gated).
- [ ] (3) Verify.
- [ ] (4) Commit:
  ```
  git add src/tornopen/http_error.py src/tornopen/decorator.py src/tornopen/__init__.py tests/decorator/test_request_body_content_type.py
  git commit -m "fix(decorator): return 415 for non-JSON bodies to RequestBody handlers"
  ```

---

## Phase 4 — `RequestValidationError` int status + Content-Type on 400 path (#4, #5)

- [ ] (1) Tests: extend `tests/decorator/test_validation_error_handling.py`:
  - [ ] Custom handler reading `e.status_code` asserts `== 400` (int).
  - [ ] 400 response has `Content-Type: application/json`.
  - [ ] Leave existing literal-string assertion as-is (deferred to error-UX pass).
- [ ] (2) Impl:
  - [ ] `src/tornopen/decorator.py:247` `status_code="400"` → `400`.
  - [ ] `src/tornopen/decorator.py:322-334` early-return sets `Content-Type: application/json` before `write`.
- [ ] (3) Verify.
- [ ] (4) Commit:
  ```
  git add src/tornopen/decorator.py tests/decorator/test_validation_error_handling.py
  git commit -m "fix(decorator): int status_code on RequestValidationError; JSON Content-Type on 400 path"
  ```

---

## Phase 5 — Guard `HTTPError.dict` for subclasses skipping base `__init__` (#12)

- [ ] (1) Tests: `tests/decorator/test_custom_http_error.py`:
  - [ ] `CustomErrorWithoutMessage` raised in decorated handler → 420 + custom body, not 500. Red now.
- [ ] (2) Impl: `src/tornopen/http_error.py:14` — `dict()` uses `getattr(self, "error_type", None)` / `getattr(self, "error_message", "")`.
- [ ] (3) Verify.
- [ ] (4) Commit:
  ```
  git add src/tornopen/http_error.py tests/decorator/test_custom_http_error.py
  git commit -m "fix(http_error): guard dict() for subclasses that skip base __init__"
  ```

---

## Phase 6 — `cast_enum_to_str` doc + stacking-order test (#6, #19)

- [ ] (1) Tests: `tests/decorator/test_cast_enum_stacking.py`:
  - [ ] `@validate_arguments` over `@cast_enum_to_str` → 200 (correct).
  - [ ] Reverse order → document as unsupported (xfail or assert 500).
- [ ] (2) Impl: doc comment on `cast_enum_to_str` (`src/tornopen/decorator.py:103`) — must sit below `validate_arguments` (relies on `__wrapped__` unwrap).
- [ ] (3) Verify.
- [ ] (4) Commit:
  ```
  git add src/tornopen/decorator.py tests/decorator/test_cast_enum_stacking.py
  git commit -m "docs(decorator): document cast_enum_to_str stacking requirement"
  ```

---

## Phase 7 — `documenter` mutation leak + `create_api_spec` try/finally (#7, #8)

- [ ] (1) Tests: `tests/api_spec/test_documenter_no_mutation.py`:
  - [ ] Handler without `_doc_category` post-`documenter`: assert `'_doc_category' not in handler_class.__dict__`.
  - [ ] Force `api_spec.path` to raise, post-`documenter`: assert `not hasattr(handler_class, 'handler_class_params')`.
- [ ] (2) Impl:
  - [ ] `src/tornopen/document.py:45` `_categorize_rules` uses `getattr(handler_class, "_doc_category", "undocumented")` without `setattr`.
  - [ ] `src/tornopen/api_spec/create_api_spec.py:126-134` `try/finally` with `del handler.handler_class_params` in `finally`.
- [ ] (3) Verify.
- [ ] (4) Commit:
  ```
  git add src/tornopen/document.py src/tornopen/api_spec/create_api_spec.py tests/api_spec/test_documenter_no_mutation.py
  git commit -m "fix(document): stop mutating handler classes; try/finally around spec build"
  ```

---

## Phase 8 — Dead code + `exception_finder` cleanup (#9, #10, #21.1-21.3)

- [ ] (1) Tests: `tests/api_spec/test_exception_finder_limits.py`:
  - [ ] Bare-name `raise X(...)` found.
  - [ ] `raise` inside nested function not found (documents current behavior).
- [ ] (2) Impl:
  - [ ] Delete `SuccessResponseModelSchema` (`src/tornopen/api_spec/plugin.py:280`).
  - [ ] `src/tornopen/api_spec/exception_finder.py`: remove dead `results=[]` + append (line 48); rename `vars` shadow; docstring listing limits (nested funcs, re-raises, ternary).
  - [ ] `src/tornopen/decorator.py:97` bare `try/except/finally: continue` → log on exception.
  - [ ] `src/tornopen/document.py:38,61` rename reused `rules` in `_add_rules`.
  - [ ] `src/tornopen/api_spec/core.py` add `tags` property; `src/tornopen/api_spec/create_api_spec.py:155` `api_spec._tags` → `api_spec.tags`.
- [ ] (3) Verify.
- [ ] (4) Commit:
  ```
  git add src/tornopen/api_spec/plugin.py src/tornopen/api_spec/exception_finder.py src/tornopen/api_spec/core.py src/tornopen/api_spec/create_api_spec.py src/tornopen/decorator.py src/tornopen/document.py tests/api_spec/test_exception_finder_limits.py
  git commit -m "chore: remove dead code, document exception_finder limits, minor cleanups"
  ```

---

## Phase 9 (DEFERRED) — Test fixes (#11)

DEFERRED to a future error-management-UX design pass. Known-broken tests left in place:
- [ ] `test_query_params_model.py` `return Pagination` (returns class, not instance).
- [ ] `test_nested_models.py` empty body `...`.
- [ ] `test_validation_error_handling.py` literal pydantic error string.
- [ ] `RequestValidationError.errors()` exposure in response body (currently only `str(e)`).
- [ ] User-managed error schema/shape customization exploration.
- [ ] Structural test assertions replacing literal pydantic strings.

Will be addressed together with the broader "how users manage their own errors" exploration.

---

## Phase 10 — Typing modernization via ruff + ty (#14)

- [ ] (1) Tests: none.
- [ ] (2) Impl:
  - [ ] `uv run ruff check --fix && uv run ruff format`.
  - [ ] Manually modernize `typing.Dict`→`dict`, `Optional`→`| None`, `Tuple`→`tuple`, `List`→`list` in `decorator.py`, `http_error.py`, `tests/__init__.py`.
  - [ ] Resolve remaining `ty check` findings.
- [ ] (3) Verify: `uv run ruff check`, `uv run ty check`, `uv run pytest` clean.
- [ ] (4) Commit:
  ```
  git add src/tornopen tests
  git commit -m "style: modernize typing (PEP 585/604); ruff + ty clean"
  ```

---

## Phase 11 — Types, comments, delete unused `TimestampedBaseModel` (#16, #17, #21.4, #21.5)

- [ ] (1) Tests: none.
- [ ] (2) Impl:
  - [ ] `src/tornopen/document.py:24` `Documents.categories: dict[str, APISpec]` → `dict[str, dict]`.
  - [ ] `src/tornopen/api_spec/plugin.py:41` `_clear_none_from_dict` — comment: `0`/`False` preserved (only `None/{}/[]` dropped).
  - [ ] `src/tornopen/model.py` delete `TimestampedBaseModel` + `Timestamp` TypeAlias (unused, unexported).
  - [ ] `src/tornopen/model.py:85` `BaseModel.dict` — comment: delegates to `model_dump`, casts enums (kept for back-compat).
- [ ] (3) Verify.
- [ ] (4) Commit:
  ```
  git add src/tornopen/document.py src/tornopen/api_spec/plugin.py src/tornopen/model.py
  git commit -m "chore: fix Documents.categories type, comment _clear_none, delete unused TimestampedBaseModel"
  ```

---

## Phase 12 — Docs: singleton + exception_finder + stacking (#18, #6, #10)

- [ ] (1) Tests: none.
- [ ] (2) Impl: `README.md` "Limitations" section:
  - [ ] Process-global exception-handler registry (one mapping per process).
  - [ ] `exception_finder` detects only bare-name `raise X(...)`; nested functions, re-raises, ternary raises missed.
  - [ ] `cast_enum_to_str` must stack below `validate_arguments`.
- [ ] (3) Verify: `uv run pytest` green (doc-only).
- [ ] (4) Commit:
  ```
  git add README.md
  git commit -m "docs: document singleton registry, exception_finder limits, decorator stacking"
  ```

---

## Phase 13 — Open PR #2

- [ ] `git push -u origin fix/codebase-review`.
- [ ] `gh pr create --base main --head fix/codebase-review --title "Codebase review fixes" --body <summary>`.
- [ ] PR body lists all fix-phase commits + findings closed.
- [ ] Skipped (per decisions): #15 pydantic v2 `.schema()` migration, #20 Redoc CDN pin.
- [ ] Deferred: #11 test fixes (Phase 9) → future error-UX pass.