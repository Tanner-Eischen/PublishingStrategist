# KDP Publishing Strategist

[![CI](https://github.com/Tanner-Eischen/PublishingStrategist/actions/workflows/ci.yml/badge.svg)](https://github.com/Tanner-Eischen/PublishingStrategist/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

KDP Publishing Strategist is an experimental research tool for Amazon Kindle Direct Publishing. It combines a Python analysis package, a FastAPI service, and a React client. The current code supports niche discovery, competitor analysis, listing drafts, and scenario-based stress tests.

The application needs a Keepa API key for Amazon product data. Ubersuggest support is optional. Scores and listing suggestions are inputs to further research, not evidence that a book will sell.

## Run the API

Python 3.9 or newer is required.

```bash
git clone https://github.com/Tanner-Eischen/PublishingStrategist.git
cd PublishingStrategist
python -m venv .venv
```

Activate the environment, then install the project:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install mcp
```

Copy `.env.example` to `.env` and set `KEEPA_API_KEY`. Start the FastAPI service from the repository root:

```bash
python -m uvicorn api.main:app --reload
```

The API documentation is available at `http://localhost:8000/docs`. The basic health endpoint is `http://localhost:8000/api/health`.

## Run the React client

Use Node.js 24 in a second terminal:

```bash
cd frontend
npm ci
npm start
```

The development client proxies API calls to `http://localhost:8000`.

## Main API routes

- `POST /api/niches/discover` analyzes candidate niches.
- `POST /api/competitors/analyze` compares products for a niche.
- `POST /api/listings/generate` creates a listing draft.
- `POST /api/stress/run` runs the configured market scenarios.
- `GET /api/dashboard/stats` returns dashboard totals.

See the interactive FastAPI documentation for request and response schemas.

## Repository layout

```text
api/                     FastAPI application and routers
config/                  Environment-backed settings
frontend/                React client
scripts/                 Database, deployment, and monitoring utilities
src/kdp_strategist/      Analysis package and data clients
```

## Checks

Run the Python checks with:

```bash
python -m ruff check src api scripts --select E9,F63,F7,F82
python -m compileall -q src api scripts
python -m pytest tests
python -m build
python -m twine check dist/*
```

The frontend job runs:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

The Python tests currently cover the importable package metadata. The older frontend component tests need further repair and are not part of CI.

## License

This project is available under the [MIT License](LICENSE).
