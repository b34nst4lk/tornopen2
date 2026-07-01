# Codebase review fixes — Plan 001

Status: executing.
Workflow: **Stacked PRs, one phase at a time.** Each phase = branch →
commit → push → PR → **wait for user to merge before starting the next
phase.** Each phase branches off the previous phase's branch (Phase 1
off `main`). User merges on their end; do not merge PRs.

Branches:
- `chore/package-bootstrap` (Phase 0 → PR #1 → MERGED to `main`).
- `docs/plan-update` off `main` → PR → user merges (this doc update).
- `fix/phase-1-...` off `main` (after plan PR merged) → PR #2 → user merges.
- `fix/phase-2-...` off `fix/phase-1-...` → PR base `fix/phase-1-...` → user merges.
- ... stacking continues through Phase 12.
- Phase 9 DEFERRED. Old "Phase 13" (single PR) REMOVED — replaced by
  per-phase PRs.

Conventions for every phase:
- Tests-first where behavior changes (red before impl).
- Verify with `uv run pytest`, `uv run ruff check`, `uv run ty check`.
- One commit per phase; explicit `git add <files>` (never `git add .`).
- After commit: push branch, `gh pr create`, STOP and wait for user merge.

## Decisions

| Item | Decision |
|------|----------|
| Layout | `src/tornopen/` |
| Python | `>=3.10` (StrEnum shim) |
| Tooling | uv-managed pyproject + lock, ruff + ty |
| Phase 0 | `chore/package-bootstrap` → PR #1 → MERGED to `main` |
| PR model | One PR per phase, stacked, user merges |
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

## Phase 0 — Package bootstrap — DONE

Branch: `chore/package-bootstrap` → PR #1 → MERGED to `main` (squash).

- [x] (1) Tests: existing suite passes post-restructure.
- [x] (2) Impl: `src/tornopen/` layout, `pyproject.toml` (uv, `>=3.10`), `.gitignore`, StrEnum shim, README import rewrite, duplicate test file removed, `documenter` sets `template_path`, `uv.lock`.
- [x] (3) Verify: `uv run pytest` green (2 pre-existing failures deferred), `uv run ruff check`, `uv run ty check`.
- [x] (4) Commit + PR #1 + merged.

---

## Phase 1 — Fix `is_primitive`/`is_collection` `get_args` typo (#1) — DONE

- [x] (1) Tests: `tests/decorator/test_typed_list_query_params.py`:
  - [x] `list[int]` handler: `?param=1,2,3` → 200; `?param=1,abc` → 400.
  - [x] `Optional[list[int]]` handler: omitted → 200; `?param=1,2,3` → 200.
  - [x] Red before fix.
- [x] (2) Impl: `get_args(type)` → `get_args(type_)`; exclude collections from `is_primitive` recursion; recognize parameterized `list`/`set` via `get_origin` in `is_collection`.
- [x] (3) Verify: new tests green; no regressions.
- [x] (4) PR #3 → MERGED.

---

## Phase 2 — Fix `exclude_none` factory arg no-op (#2) — DONE

- [x] (1) Tests: `tests/decorator/test_exclude_none.py`:
  - [x] `factory = ValidateArgumentsDecoratorFactory(exclude_none=True)`.
  - [x] Handler returns `Response` with `Optional[str] = None` field.
  - [x] Assert response JSON omits the key. Red before fix.
- [x] (2) Impl: `__call__`'s `exclude_none` defaults to `None`; wrapper uses `effective_exclude_none` (per-decorator override → factory setting).
- [x] (3) Verify: 272 passed (+1), no regressions.
- [x] (4) PR #4 → MERGED.

---

## Phase 3 — 415 for non-JSON request bodies (#3) — DONE

- [x] (1) Tests: `tests/decorator/test_request_body_content_type.py`:
  - [x] Form-encoded POST to `RequestBody` handler → 415 + `error.type == "unsupported_media_type"`.
  - [x] JSON POST → 200.
  - [x] Missing Content-Type + body → 415.
  - [x] User-registered `@exception_handler(UnsupportedMediaTypeError)` override → custom status/body.
  - [x] Direct raise `UnsupportedMediaTypeError` → 415.
- [x] (2) Impl:
  - [x] `src/tornopen/http_error.py`: new `UnsupportedMediaTypeError(HTTPError)` (415, `error_type="unsupported_media_type"`); exported in `__all__`.
  - [x] `retrieve_request_body` returns `(body, is_json)` tuple; Content-Type-gated.
  - [x] Wrapper raises `UnsupportedMediaTypeError` for non-JSON when body expected; moved inside validation try/except; sets `Content-Type: application/json` on error path.
- [x] (3) Verify: 277 passed (+5), no regressions.
- [x] (4) PR #5 → MERGED.

---

## Phase 4 — `RequestValidationError` int status + Content-Type on 400 path (#4, #5) — DONE

- [x] (1) Tests: extend `tests/decorator/test_validation_error_handling.py`:
  - [x] Custom handler reading `e.status_code` asserts `== 400` (int).
  - [x] 400 response has `Content-Type: application/json`.
  - [x] Leave existing literal-string assertion as-is (deferred to error-UX pass).
- [x] (2) Impl:
  - [x] `decorator.py:265` `status_code="400"` → `400` (int).
  - [x] Content-Type on 400 error path already set in Phase 3.
- [x] (3) Verify: 279 passed (+2), no regressions.
- [x] (4) PR #6 → MERGED.

---

## Phase 5 — Guard `HTTPError.dict` for subclasses skipping base `__init__` (#12) — DONE

- [x] (1) Tests: `tests/decorator/test_custom_http_error.py`:
  - [x] `CustomErrorWithoutMessage` (skips base `__init__`) raised → 420 + `error.type` is None, not 500.
  - [x] `PartiallyInitializedError` (only `error_message`) → 418 + `error.type` is None + message.
  - [x] Red before fix.
- [x] (2) Impl: `http_error.py` `dict()` uses `getattr(self, "error_type", None)` / `getattr(self, "error_message", "")`; `__str__` falls back to `Exception.__str__` when `error_message` unset.
- [x] (3) Verify: 282 passed (+2), no regressions.
- [x] (4) PR #7 → MERGED.

---

## Phase 6 — `cast_enum_to_str` doc + stacking-order test (#6, #19) — DONE

- [x] (1) Tests: `tests/decorator/test_cast_enum_stacking.py`:
  - [x] `@validate_arguments` over `@cast_enum_to_str` → 200 (correct).
  - [x] Reverse order → strict xfail (handler body doesn't run).
- [x] (2) Impl: doc comment on `cast_enum_to_str` — must sit below `validate_arguments` (relies on `__wrapped__` unwrap).
- [x] (3) Verify: 283 passed (+1), 1 xfailed (+1), no regressions.
- [x] (4) PR (this PR).

---

## Phase 7 — `documenter` mutation leak + `create_api_spec` try/finally (#7, #8)

- [ ] (1) Tests: `tests/api_spec/test_documenter_no_mutation.py`:
  - [ ] Handler without `_doc_category` post-`documenter`: assert `'_doc_category' not in handler_class.__dict__`.
  - [ ] Force `api_spec.path` to raise, post-`documenter`: assert `not hasattr(handler_class, 'handler_class_params')`.
- [ ] (2) Impl:
  - [ ] `src/tornopen/document.py:45` `_categorize_rules` uses `getattr(handler_class, "_doc_category", "undocumented")` without `setattr`.
  - [ ] `src/tornopen/api_spec/create_api_spec.py:126-134` `try/finally` with `del handler.handler_class_params` in `finally`.
- [ ] (3) Verify.
- [ ] (4) Branch off `fix/phase-6-...`, commit, push, PR (base phase-6), wait:
  ```
  git switch -c fix/phase-7-documenter-no-mutation  # off phase-6 branch
  git add src/tornopen/document.py src/tornopen/api_spec/create_api_spec.py tests/api_spec/test_documenter_no_mutation.py
  git commit -m "fix(document): stop mutating handler classes; try/finally around spec build"
  git push -u origin fix/phase-7-documenter-no-mutation
  gh pr create --base fix/phase-6-cast-enum-stacking-doc --head fix/phase-7-documenter-no-mutation \
    --title "fix(document): stop mutating handler classes; try/finally around spec build"
  # STOP — wait for user to merge before Phase 8
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
- [ ] (4) Branch off `fix/phase-7-...`, commit, push, PR (base phase-7), wait:
  ```
  git switch -c fix/phase-8-dead-code-exception-finder  # off phase-7 branch
  git add src/tornopen/api_spec/plugin.py src/tornopen/api_spec/exception_finder.py src/tornopen/api_spec/core.py src/tornopen/api_spec/create_api_spec.py src/tornopen/decorator.py src/tornopen/document.py tests/api_spec/test_exception_finder_limits.py
  git commit -m "chore: remove dead code, document exception_finder limits, minor cleanups"
  git push -u origin fix/phase-8-dead-code-exception-finder
  gh pr create --base fix/phase-7-documenter-no-mutation --head fix/phase-8-dead-code-exception-finder \
    --title "chore: remove dead code, document exception_finder limits, minor cleanups"
  # STOP — wait for user to merge before Phase 10
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
- [ ] (4) Branch off `fix/phase-8-...`, commit, push, PR (base phase-8), wait:
  ```
  git switch -c fix/phase-10-typing-modernization  # off phase-8 branch
  git add src/tornopen tests
  git commit -m "style: modernize typing (PEP 585/604); ruff + ty clean"
  git push -u origin fix/phase-10-typing-modernization
  gh pr create --base fix/phase-8-dead-code-exception-finder --head fix/phase-10-typing-modernization \
    --title "style: modernize typing (PEP 585/604); ruff + ty clean"
  # STOP — wait for user to merge before Phase 11
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
- [ ] (4) Branch off `fix/phase-10-...`, commit, push, PR (base phase-10), wait:
  ```
  git switch -c fix/phase-11-types-comments-timestamped  # off phase-10 branch
  git add src/tornopen/document.py src/tornopen/api_spec/plugin.py src/tornopen/model.py
  git commit -m "chore: fix Documents.categories type, comment _clear_none, delete unused TimestampedBaseModel"
  git push -u origin fix/phase-11-types-comments-timestamped
  gh pr create --base fix/phase-10-typing-modernization --head fix/phase-11-types-comments-timestamped \
    --title "chore: fix Documents.categories type, comment _clear_none, delete unused TimestampedBaseModel"
  # STOP — wait for user to merge before Phase 12
  ```

---

## Phase 12 — Docs: singleton + exception_finder + stacking (#18, #6, #10)

- [ ] (1) Tests: none.
- [ ] (2) Impl: `README.md` "Limitations" section:
  - [ ] Process-global exception-handler registry (one mapping per process).
  - [ ] `exception_finder` detects only bare-name `raise X(...)`; nested functions, re-raises, ternary raises missed.
  - [ ] `cast_enum_to_str` must stack below `validate_arguments`.
- [ ] (3) Verify: `uv run pytest` green (doc-only).
- [ ] (4) Branch off `fix/phase-11-...`, commit, push, PR (base phase-11), wait:
  ```
  git switch -c fix/phase-12-docs-limitations  # off phase-11 branch
  git add README.md
  git commit -m "docs: document singleton registry, exception_finder limits, decorator stacking"
  git push -u origin fix/phase-12-docs-limitations
  gh pr create --base fix/phase-11-types-comments-timestamped --head fix/phase-12-docs-limitations \
    --title "docs: document singleton registry, exception_finder limits, decorator stacking"
  # STOP — wait for user to merge. This is the final phase.
  ```

---

## Obsolete — Phase 13 (single PR) REMOVED

Replaced by per-phase stacked PRs (Phases 1-8, 10-12). Each phase is
its own PR; user merges each before the next phase begins.

Skipped (per decisions): #15 pydantic v2 `.schema()` migration, #20
Redoc CDN pin. Deferred: #11 test fixes (Phase 9) → future error-UX pass.