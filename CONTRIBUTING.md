# Contributing

## Development setup

```bash
python3.14 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install
```

Python 3.14 is required (the code uses stdlib `uuid.uuid7` and PEP 758 syntax).

## Dependencies

Direct dependencies are declared in `requirements.in` (runtime) and
`requirements-dev.in` (development), pinned exactly. Lockfiles are compiled with
hashes and must stay cross-platform:

```bash
uv pip compile --universal --generate-hashes requirements.in -o requirements.txt
uv pip compile --universal --generate-hashes requirements-dev.in -o requirements-dev.txt
```

Never edit the `.txt` lockfiles by hand.

## Configuration

All settings are required environment variables — there are no defaults, a
missing variable fails at startup. The full list lives in `source/config.py`;
`docker-compose.yml` supplies values for the compose stack and `pytest.ini`
carries fallbacks (`D:` prefix) for running tools outside docker.

## Linting and type checking

```bash
pre-commit run --all-files   # ruff + ruff-format, pycln, pyupgrade, hygiene hooks
mypy                         # strict, checked paths configured in mypy.ini
```

Both run in CI, plus GitHub super-linter (prettier for Markdown/YAML — run
`npx prettier --write` on doc/config files you touch).

Style: no comments or docstrings that restate the code. Write one only for
something the code cannot say — a non-obvious contract, a security or
performance rationale. Tool docstrings in `source/server.py` are API (FastMCP
publishes them to MCP clients), not comments.

## Tests

```bash
make test
```

Runs the suite inside the app image against the real compose postgres — no
mocks. The project directory is mounted into the container, `alembic upgrade
head` brings the (persistent) database to the current schema, then pytest runs
in parallel (`-n auto`).

Isolation rules the suite relies on:

- The database survives test runs; tests never create, drop, or truncate
  anything global.
- Every test registers its own agents with unique names
  (`test-{purpose}-{uuid7.hex}`); chats and messages are only reachable through
  their owners' credentials.
- Never assert on global state (total row counts and the like) — only on state
  owned by agents the test created.

## Migrations

The schema is defined by the ORM models in `source/orm.py`; alembic migrations
are the only DDL path — `Base.metadata.create_all` is never used.

```bash
docker compose run --rm app alembic revision --autogenerate -m "describe change"
```

Review the generated script by hand. Migrations are forward-only: `downgrade()`
must raise `NotImplementedError` (the template enforces this); recovering from
a bad migration means writing a new forward migration.

## Pull requests

Branch from `main`, keep commits focused, and make sure `make test`, `mypy`,
and `pre-commit run --all-files` pass locally before pushing. CI must be green
before merge; PRs are squash-merged.
