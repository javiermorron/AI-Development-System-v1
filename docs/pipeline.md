# Pipeline

This document walks through the full pipeline execution — from feature description to running FastAPI backend.

## Overview

```
Feature text  ->  ArchitectureAgent  ->  BackendAgent  ->  ReviewerAgent  ->  generated/<slug>/
```

All stages run inside a `PipelineEngine` that manages ordering, dependencies, and fail-fast behavior. Inter-stage data flows exclusively through `PipelineContext.stage_outputs`.

---

## Stage 1 — ArchitectureAgent

### Input

A plain-text feature description:

```
"User authentication system with JWT tokens and role-based permissions"
```

### What it does

1. **Keyword extraction** — scans the feature text against a 27-entry keyword map. Recognized entities: `user`, `token`, `order`, `product`, `payment`, `invoice`, `blog`, `post`, `comment`, `tag`, `category`, `cart`, `item`, `address`, `review`, `rating`, `notification`, `message`, `report`, `file`, `image`, `role`, `permission`, `session`, `log`, `audit`, `setting`.

2. **Component derivation** — maps entities to their infrastructure components (e.g., `token` -> `jwt`, `auth`; `payment` -> `stripe`, `billing`).

3. **Route derivation** — generates 5 CRUD routes per entity (POST create, GET list, GET by ID, PUT update, DELETE). Security level per route: read=L1, write=L2, delete=L3.

4. **Security concern identification** — flags entity-specific risks (JWT secret exposure, PII handling, payment card data, etc.)

### Output stored in `stage_outputs["architecture"]`

```python
{
    "entities": ["User", "Token"],
    "components": ["authentication", "jwt", "authorization"],
    "routes": [
        {"method": "POST", "path": "/users",       "handler": "create_user",  "security_level": 2},
        {"method": "GET",  "path": "/users",       "handler": "list_users",   "security_level": 1},
        {"method": "GET",  "path": "/users/{id}",  "handler": "get_user",     "security_level": 1},
        {"method": "PUT",  "path": "/users/{id}",  "handler": "update_user",  "security_level": 2},
        {"method": "DELETE","path":"/users/{id}",  "handler": "delete_user",  "security_level": 3},
        # ... 5 more for Token
    ],
    "security_concerns": [
        "JWT secret must not be hardcoded — use environment variables",
        "Passwords must be hashed — never store plaintext"
    ]
}
```

---

## Stage 2 — BackendAgent

### Input

Reads `stage_outputs["architecture"]` plus `context.workspace` (the output directory path).

### What it does

Generates 9+ Python files using string templates. No LLM is involved — the code structure is derived purely from the entity/route data produced by Stage 1.

**models.py** — one Pydantic `BaseModel` per entity with typed fields:

```python
class User(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    created_at: Optional[str] = None
```

**schemas.py** — three schema variants per entity:

```python
class UserCreate(BaseModel):   # only writable fields
class UserUpdate(BaseModel):   # all fields Optional for PATCH semantics
class UserResponse(BaseModel): # full model for API responses
```

**routers/user.py** — an APIRouter with all 5 CRUD endpoints:

```python
router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate) -> UserResponse: ...

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int) -> UserResponse: ...
```

**main.py** — imports and mounts all routers:

```python
app = FastAPI(title="User Authentication System With Jwt Tokens And Role-Based Permissions")
from routers import router as api_router
app.include_router(api_router, prefix="/api/v1")
```

Files are written to `context.workspace` (e.g., `generated/user-authentication-system-with-jwt-toke/`).

### Output stored in `stage_outputs["backend"]`

```python
{
    "files": {
        "main.py": "...",
        "models.py": "...",
        "schemas.py": "...",
        "services.py": "...",
        "repositories.py": "...",
        "routers/__init__.py": "...",
        "routers/user.py": "...",
        "routers/token.py": "...",
        "requirements.txt": "fastapi\nuvicorn[standard]\npydantic>=2.0",
        "README.md": "..."
    },
    "entities_implemented": ["User", "Token"],
    "route_count": 10,
    "lines_of_code": 420
}
```

---

## Stage 3 — ReviewerAgent

### Input

Reads `stage_outputs["backend"]["files"]` — the dict of filename -> source code strings. Non-`.py` files are skipped.

### What it does

Runs `ast.parse()` on every Python file and walks the AST to collect metrics and findings:

| Check | Severity | Score penalty |
|-------|----------|---------------|
| Class missing docstring | WARNING | -0.5 |
| Function missing docstring | WARNING | -0.5 |
| Function missing return annotation | WARNING | -0.5 |
| Parameter missing annotation | WARNING | -0.5 |
| `raise NotImplementedError` stub | ERROR | -2.0 |
| Hardcoded credential pattern | ERROR | -2.0 |
| Debug `print()` call | WARNING | -0.5 |
| TODO/FIXME comment | INFO | no penalty |

Final score: `max(0, 10.0 - errors*2.0 - warnings*0.5)`

Approved if score >= 7.0.

### Output stored in `stage_outputs["reviewer"]`

```python
{
    "approved": True,
    "score": 9.5,
    "summary": "Good code quality. Minor documentation gaps.",
    "findings": [
        {"severity": "WARNING", "file": "services.py", "line": 24, "message": "Missing return annotation"},
    ],
    "metrics": {
        "files_reviewed": 7,
        "classes_found": 9,
        "functions_found": 42,
        "docstring_coverage": "78%",
        "not_implemented_count": 0,
        "todo_count": 2
    }
}
```

---

## Pipeline context lifecycle

```
PipelineContext created
    stage_outputs = {}

After Stage 1:
    stage_outputs["architecture"] = { entities, routes, ... }

After Stage 2:
    stage_outputs["backend"] = { files, route_count, ... }
    (files written to disk at context.workspace)

After Stage 3:
    stage_outputs["reviewer"] = { approved, score, findings, ... }

Pipeline returns list[StageResult]
```

---

## Fail-fast behavior

If any stage returns `StageStatus.FAILED`, the engine stops immediately and returns all results up to and including the failed stage. The runner (`run_pipeline.py`) exits with code 1 and prints the error.

---

## Running the pipeline

```bash
# Default feature
python -m examples.run_pipeline

# Custom feature
python -m examples.run_pipeline --feature "Blog with posts, comments and tags"

# Show all generated source files inline
python -m examples.run_pipeline --feature "E-commerce catalog" --show-code

# Use a different config file
python -m examples.run_pipeline --config my_config.yaml
```

### Example terminal output

```
╭─────────────────────────────────────────────────────────╮
│ AI Development System v2 - Example Pipeline             │
│                                                         │
│ Feature:    User authentication system with JWT tokens  │
│ Output dir: generated/user-authentication-system-wi...  │
╰─────────────────────────────────────────────────────────╯

>> ARCHITECTURE
  Entities   : User, Token
  Components : authentication, jwt, authorization
  Routes     : 10 endpoints across 2 resource(s)
  Security   : 2 concern(s) identified

>> BACKEND
  Entities : User, Token
  Routes   : 10 FastAPI handler stubs
  Lines    : ~420 lines of Python

>> REVIEWER
  APPROVED  Score: 10/10
  Excellent generated code quality. ...
  Files reviewed     : 7
  Docstring coverage : 85%

╭─────────────────────────────────────────────────────────╮
│ OK PIPELINE PASSED                                      │
│ Score: 10/10   All stages completed successfully.       │
│                                                         │
│ Output: generated/user-authentication-system-wi.../     │
│                                                         │
│ To run:                                                 │
│   cd generated/user-authentication-system-wi...        │
│   pip install -r requirements.txt                       │
│   uvicorn main:app --reload                             │
│                                                         │
│ Then open http://localhost:8000/docs                    │
╰─────────────────────────────────────────────────────────╯
```
